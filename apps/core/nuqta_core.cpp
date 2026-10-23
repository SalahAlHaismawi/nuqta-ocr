#include "nuqta_core.h"

#ifdef __ANDROID__
#include <android/log.h>
#define __android_log_like(...) __android_log_print(ANDROID_LOG_INFO, "nuqta", __VA_ARGS__)
#else
#include <cstdio>
#define __android_log_like(...) (getenv("NUQTA_LOG") ? fprintf(stderr, __VA_ARGS__), fputc('\n', stderr) : 0)
#endif

#include <chrono>
#include <cstdlib>
#include <mutex>
#include <algorithm>
#include <cstring>
#include <atomic>
#include <condition_variable>
#include <thread>
#include <fstream>
#include <pthread.h>
#include <sched.h>
#include <sys/resource.h>
#include <unistd.h>
#include <vector>

#include "ggml-backend.h"
#include "llama.h"
#include "mtmd.h"
#include "mtmd-helper.h"

namespace nuqta {

static llama_model * g_model = nullptr;
static mtmd_context * g_mtmd = nullptr;
static int g_bg_threads = 2;
static int g_threads = 4;
static std::mutex g_mu;

static constexpr int N_CTX = 8192;
static constexpr int N_BATCH = 2048;

static double now_s() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}


// fast and slow cores from cpufreq (big.LITTLE phones); on equal cores, split them in half
static void core_sets(std::vector<int> & big, std::vector<int> & little) {
    const int n = (int) std::thread::hardware_concurrency();
    std::vector<long> f(n, 0);
    long top = 0;
    for (int i = 0; i < n; i++) {
        std::ifstream in("/sys/devices/system/cpu/cpu" + std::to_string(i) + "/cpufreq/cpuinfo_max_freq");
        if (in) in >> f[i];
        top = std::max(top, f[i]);
    }
    for (int i = 0; i < n; i++) (top > 0 && f[i] >= top * 3 / 4 ? big : little).push_back(i);
    if (little.empty() || big.empty()) {
        big.clear(); little.clear();
        for (int i = 0; i < n; i++) (i < n / 2 ? big : little).push_back(i);
    }
}


bool loaded() { return g_model && g_mtmd; }

void unload() {
    std::lock_guard<std::mutex> lk(g_mu);
    if (g_mtmd) { mtmd_free(g_mtmd); g_mtmd = nullptr; }
    if (g_model) { llama_model_free(g_model); g_model = nullptr; }
}

bool load(const std::string & model_path, const std::string & mmproj_path, int n_threads, int image_max_tokens,
          const std::string & backend_dir, std::string & err) {
    std::lock_guard<std::mutex> lk(g_mu);
    static bool backends = false;
    if (!backends) {
        if (!backend_dir.empty()) ggml_backend_load_all_from_path(backend_dir.c_str());
        else ggml_backend_load_all();
        llama_backend_init();
        backends = true;
    }
    if (g_mtmd) { mtmd_free(g_mtmd); g_mtmd = nullptr; }
    if (g_model) { llama_model_free(g_model); g_model = nullptr; }
    g_threads = n_threads;
    {   // background strips run at idle priority, one thread per slow core (they are idle while the fast cores write)
        std::vector<int> big, little;
        core_sets(big, little);
        g_bg_threads = getenv("NUQTA_BG") ? atoi(getenv("NUQTA_BG")) : std::clamp((int) little.size(), 1, 2);
    }

    llama_model_params mp = llama_model_default_params();
#ifdef __APPLE__
    mp.n_gpu_layers = 999;   // iPhone: the whole model on the GPU (Metal)
#else
    mp.n_gpu_layers = 0;     // Android: CPU (the fast cores)
#endif
    g_model = llama_model_load_from_file(model_path.c_str(), mp);
    if (!g_model) { err = "could not load the model file"; return false; }

    mtmd_context_params cp = mtmd_context_params_default();
#ifdef __APPLE__
    cp.use_gpu = true;       // vision encoder on the GPU: the slow step on a phone CPU
#else
    cp.use_gpu = false;
#endif
    cp.n_threads = n_threads;
    cp.print_timings = getenv("NUQTA_TIMINGS") != nullptr;
    cp.warmup = true;
    cp.flash_attn_type = getenv("NUQTA_NOFA") ? LLAMA_FLASH_ATTN_TYPE_DISABLED : LLAMA_FLASH_ATTN_TYPE_ENABLED;
    if (image_max_tokens > 0) cp.image_max_tokens = image_max_tokens;
    g_mtmd = mtmd_init_from_file(mmproj_path.c_str(), g_model, cp);
    if (!g_mtmd) { err = "could not load the vision file"; llama_model_free(g_model); g_model = nullptr; return false; }
    return true;
}

// emit only complete UTF-8 sequences; keep a trailing partial one for the next piece
static std::string take_valid_utf8(std::string & buf) {
    size_t i = 0, ok = 0;
    while (i < buf.size()) {
        unsigned char c = buf[i];
        size_t n = c < 0x80 ? 1 : (c >> 5) == 0x6 ? 2 : (c >> 4) == 0xE ? 3 : (c >> 3) == 0x1E ? 4 : 1;
        if (i + n > buf.size()) break;
        i += n; ok = i;
    }
    std::string out = buf.substr(0, ok);
    buf.erase(0, ok);
    return out;
}

// stop when the tail is one chunk repeated many times (the library's loop guard, simplified)
static bool looping(const std::string & s) {
    for (size_t len = 8; len <= 200 && len * 6 <= s.size(); len++) {
        const size_t reps = len < 20 ? 12 : 6;
        if (len * reps > s.size()) continue;
        const std::string unit = s.substr(s.size() - len);
        bool all = true;
        for (size_t r = 2; r <= reps && all; r++) all = s.compare(s.size() - r * len, len, unit) == 0;
        if (all) return true;
    }
    return false;
}

// Cut a page into horizontal strips at blank rows between text lines, so the model can start writing after the
// first strip instead of after the whole page. The first strip is short for a fast start; later ones are bigger.
static std::vector<std::pair<int, int>> strip_cuts(const uint8_t * rgb, int w, int h, int first_px, int rest_px) {
    std::vector<int> ink(h, 0);
    for (int y = 0; y < h; y++) {
        const uint8_t * row = rgb + (size_t) y * w * 3;
        int n = 0;
        for (int x = 0; x < w; x += 2) n += (row[3 * x] + row[3 * x + 1] + row[3 * x + 2]) < 3 * 150;
        ink[y] = n;
    }
    std::vector<int> sorted(ink); std::sort(sorted.begin(), sorted.end());
    const int blank = std::max(1, sorted[h / 20] + w / 400);   // rows near the emptiest ones count as gaps
    std::vector<std::pair<int, int>> cuts;
    int start = 0;
    while (start < h) {
        // grow the strips: each one must take longer to write than the next takes to read
        int want = cuts.size() == 0 ? first_px : cuts.size() == 1 ? (first_px * 3 + rest_px) / 4 : cuts.size() == 2 ? (first_px + rest_px) / 2 : rest_px;
        if (start + want + rest_px / 3 >= h) { cuts.push_back({start, h}); break; }
        // find the gap (run of blank rows) whose centre is closest to start + want, searching +-40%
        int best = -1, bestd = 1 << 30;
        int lo = start + want * 6 / 10, hi = std::min(h - 1, start + want * 14 / 10);
        for (int y = lo; y <= hi; y++) {
            if (ink[y] > blank) continue;
            int y2 = y; while (y2 + 1 <= hi && ink[y2 + 1] <= blank) y2++;
            int c = (y + y2) / 2, d = std::abs(c - (start + want));
            if (y2 - y >= 2 && d < bestd) { bestd = d; best = c; }
            y = y2;
        }
        if (best < 0) {  // no gap near the target (a ruled table, say): cut at the next real gap, never through ink
            for (int y = hi + 1; y < h; y++) {
                if (ink[y] > blank) continue;
                int y2 = y; while (y2 + 1 < h && ink[y2 + 1] <= blank) y2++;
                if (y2 - y >= 2) { best = (y + y2) / 2; break; }
                y = y2;
            }
            if (best < 0 || h - best < rest_px / 3) best = h;
        }
        cuts.push_back({start, best});
        start = best;
    }
    return cuts;
}

bool read(const uint8_t * rgb, int w, int h, const std::string & prompt, int max_new_tokens, bool strips,
          const StageFn & on_stage, const TextFn & on_text, Stats & st, std::string & err) {
    std::lock_guard<std::mutex> lk(g_mu);
    if (!g_model || !g_mtmd) { err = "model not loaded"; return false; }

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = N_CTX;
    cp.n_batch = N_BATCH;
    cp.n_ubatch = 512;
    cp.n_threads = g_threads;
    cp.n_threads_batch = g_threads;
    cp.no_perf = true;
    cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
    const llama_vocab * vocab = llama_model_get_vocab(g_model);
    const std::string text = std::string("<|im_start|>user\n") + mtmd_default_marker() + prompt +
                             "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";

    std::vector<std::pair<int, int>> cuts;
    if (strips && h > w * 6 / 10) cuts = strip_cuts(rgb, w, h, std::max(140, h / 9), std::max(260, h / 4));
    else cuts.push_back({0, h});
    // One context, one thread, all on the fast cores: read a strip, write it, read the next. Running a second job in
    // parallel on a phone only slows the writing down; the app paces the text on screen to hide the short reads.
    const size_t N = cuts.size();
    const int n_ctx = N > 1 ? 4096 : N_CTX;
    cp.n_ctx = n_ctx;
    llama_context * ctx = llama_init_from_model(g_model, cp);
    if (!ctx) { err = "could not create a context"; return false; }
    std::vector<llama_context *> cx{ctx};

    llama_sampler * smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(smpl, llama_sampler_init_greedy());
    llama_batch batch = llama_batch_init(1, 0, 1);
    st = Stats{};
    st.strips = (int) N;
    bool ok = true, stopped = false;
    std::string all;
    const double t_start = now_s();
    int img_tok = 0;
    double enc_s = 0;

    // horizontal crop of a strip to its ink (+ padding): less to encode on pages with wide margins
    auto strip_rgb = [&](size_t si, std::vector<uint8_t> & buf, int & ow) {
        const int y0 = cuts[si].first, sh = std::max(8, cuts[si].second - cuts[si].first);
        int x0 = w, x1 = -1;
        for (int y = y0; y < y0 + sh; y += 2) {
            const uint8_t * row = rgb + (size_t) y * w * 3;
            for (int x = 0; x < w; x++)
                if (row[3 * x] + row[3 * x + 1] + row[3 * x + 2] < 3 * 150) { x0 = std::min(x0, x); x1 = std::max(x1, x); }
        }
        const int pad = std::max(24, w / 20);
        x0 = std::max(0, x0 - pad); x1 = std::min(w - 1, x1 + pad);
        if (x1 < 0 || (x1 - x0 + 1) > w * 9 / 10 || getenv("NUQTA_NOTRIM")) { x0 = 0; x1 = w - 1; }
        ow = x1 - x0 + 1;
        buf.resize((size_t) ow * sh * 3);
        for (int y = 0; y < sh; y++) memcpy(&buf[(size_t) y * ow * 3], rgb + ((size_t) (y0 + y) * w + x0) * 3, (size_t) ow * 3);
        return sh;
    };

    if (on_stage) on_stage(0);
    for (size_t si = 0; si < N && ok && !stopped; si++) {
        double t0 = now_s();
        std::vector<uint8_t> buf; int ow = 0;
        const int sh = strip_rgb(si, buf, ow);
        mtmd::bitmap bmp(mtmd_bitmap_init((uint32_t) ow, (uint32_t) sh, buf.data()));
        mtmd_input_text in{text.c_str(), text.size(), true, true};
        mtmd::input_chunks chunks(mtmd_input_chunks_init());
        const mtmd_bitmap * bitmaps[] = {bmp.ptr.get()};
        if (mtmd_tokenize(g_mtmd, chunks.ptr.get(), &in, bitmaps, 1) != 0) { err = "could not prepare the image"; ok = false; break; }
        for (size_t i = 0; i < chunks.size(); i++)
            if (mtmd_input_chunk_get_type(chunks[i]) == MTMD_INPUT_CHUNK_TYPE_IMAGE) img_tok += (int) mtmd_input_chunk_get_n_tokens(chunks[i]);
        llama_memory_clear(llama_get_memory(ctx), true);
        llama_sampler_reset(smpl);
        llama_pos n_past = 0;
        if (mtmd_helper_eval_chunks(g_mtmd, ctx, chunks.ptr.get(), 0, 0, N_BATCH, true, &n_past) != 0) { err = "could not read the image"; ok = false; break; }
        enc_s += now_s() - t0;
        if (si == 0) { st.first_s = now_s() - t_start; if (on_stage) on_stage(1); }

        t0 = now_s();
        std::string pending, part;
        if (si > 0 && !all.empty()) { all += "\n"; if (on_text && !on_text("\n")) { stopped = true; break; } }
        for (int i = 0; i < max_new_tokens && n_past < n_ctx - 1; i++) {
            llama_token tok = llama_sampler_sample(smpl, ctx, -1);
            if (llama_vocab_is_eog(vocab, tok)) break;
            char piece[256];
            int n = llama_token_to_piece(vocab, tok, piece, sizeof(piece), 0, false);
            if (n > 0) pending.append(piece, n);
            st.out_tokens++;
            std::string rd = take_valid_utf8(pending);
            if (!rd.empty()) {
                part += rd; all += rd;
                if (on_text && !on_text(rd)) { stopped = true; break; }
                if (looping(part)) break;
            }
            batch.n_tokens = 1;
            batch.token[0] = tok;
            batch.pos[0] = n_past++;
            batch.n_seq_id[0] = 1;
            batch.seq_id[0][0] = 0;
            batch.logits[0] = 1;
            if (llama_decode(ctx, batch) != 0) { err = "decode failed"; ok = false; break; }
        }
        st.gen_s += now_s() - t0;
        __android_log_like("strip %zu/%zu: read %.2fs, wrote %d tokens", si + 1, N, enc_s, st.out_tokens);
    }
    st.image_tokens = img_tok;
    st.encode_s = enc_s;
    llama_batch_free(batch);
    llama_sampler_free(smpl);
    for (auto * c : cx) if (c) llama_free(c);
    return ok;

}

}  // namespace nuqta
