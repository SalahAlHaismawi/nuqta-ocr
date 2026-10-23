// Nuqta on-device OCR core: llama.cpp + mtmd, one image and one prompt in, streamed text out.
#pragma once
#include <cstdint>
#include <functional>
#include <string>

namespace nuqta {

struct Stats {
    int image_tokens = 0;
    int out_tokens = 0;
    double encode_s = 0;   // image encode + prompt decode
    double gen_s = 0;      // token generation
    double first_s = 0;    // time to the first written token
    int strips = 1;
};

// stage: 0 = reading the image, 1 = writing. Return false from on_text to stop early.
using StageFn = std::function<void(int)>;
using TextFn = std::function<bool(const std::string &)>;

bool load(const std::string & model_path, const std::string & mmproj_path, int n_threads, int image_max_tokens,
          const std::string & backend_dir, std::string & err);
bool loaded();
void unload();

// rgb: w*h*3 bytes. Returns false on error (message in err).
bool read(const uint8_t * rgb, int w, int h, const std::string & prompt, int max_new_tokens, bool strips,
          const StageFn & on_stage, const TextFn & on_text, Stats & stats, std::string & err);

}  // namespace nuqta
