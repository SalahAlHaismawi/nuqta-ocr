#!/bin/bash
# Fetches llama.cpp at the version the apps and the GGUFs were tested with, into apps/vendor/llama.cpp.
set -euo pipefail
cd "$(dirname "$0")"
LLAMA_COMMIT=5aeac37a35b44fde4bdffaec9159f2fcb253b622
if [ -d vendor/llama.cpp/.git ]; then exit 0; fi
mkdir -p vendor/llama.cpp && cd vendor/llama.cpp
git init -q && git remote add origin https://github.com/ggml-org/llama.cpp.git
git fetch -q --depth 1 origin "$LLAMA_COMMIT" && git checkout -q FETCH_HEAD
echo "llama.cpp $LLAMA_COMMIT -> apps/vendor/llama.cpp"
