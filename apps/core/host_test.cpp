// Laptop test of nuqta_core (same code as the app): host_test model mmproj image.rgb w h threads
// env: STRIPS=1 strip reading, MD=1 markdown prompt, NUQTA_BG=n background threads
#include "nuqta_core.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <vector>
int main(int c, char ** v) {
    std::ifstream f(v[3], std::ios::binary); std::vector<uint8_t> rgb((std::istreambuf_iterator<char>(f)), {});
    std::string err; nuqta::Stats st;
    if (!nuqta::load(v[1], v[2], atoi(v[6]), 4096, "", err)) { fprintf(stderr, "load: %s\n", err.c_str()); return 1; }
    auto clk = [] { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); };
    std::string out; double last = 0, maxgap = 0;
    const char * prompt = getenv("MD") ? "Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include only the diacritics visible in the image."
                                       : "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image.";
    double t0 = clk();
    bool ok = nuqta::read(rgb.data(), atoi(v[4]), atoi(v[5]), prompt, 4096, getenv("STRIPS") != nullptr, nullptr,
        [&](const std::string & t) {
            double n = clk();
            if (last > 0 && n - last > 0.8) fprintf(stderr, "GAP %.2fs at char %zu\n", n - last, out.size());
            if (last > 0 && n - last > maxgap) maxgap = n - last;
            last = n; out += t; if (getenv("TRACE")) fprintf(stderr, "T %.3f %zu\n", n - t0, out.size()); return true; }, st, err);
    printf("%s\n", out.c_str()); fflush(stdout);
    fprintf(stderr, "RESULT ok=%d total=%.1fs first=%.1fs maxgap=%.2fs strips=%d img_tok=%d out_tok=%d tok/s=%.1f\n", ok, clk() - t0,
            st.first_s, maxgap, st.strips, st.image_tokens, st.out_tokens, st.out_tokens / st.gen_s);
    std::_Exit(0);
}
