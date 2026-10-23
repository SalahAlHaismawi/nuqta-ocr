#!/bin/bash
# One-time setup on a Mac: builds llama.cpp for iOS, generates the Xcode project, opens it.
#   ./setup.sh                      (then pick your Team in Xcode > Signing, plug in the iPhone, press Run)
#   DEVELOPMENT_TEAM=ABCDE12345 ./setup.sh   (skips picking the team by hand)
set -euo pipefail
cd "$(dirname "$0")"

xcode-select -p >/dev/null 2>&1 || { echo "Install Xcode from the App Store first, open it once, then run this again."; exit 1; }
if ! xcrun --sdk iphoneos --show-sdk-path >/dev/null 2>&1; then
  cat <<MSG
The iPhone SDK was not found. Usually the Mac is using the small Command Line Tools instead of Xcode:
  1. Install Xcode from the App Store, open it once, and download the iOS platform (Xcode > Settings > Components).
  2. Run:  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer && sudo xcodebuild -license accept
  3. Run ./setup.sh again.
MSG
  exit 1
fi
rm -rf ../vendor/llama.cpp/build-ios-device ../vendor/llama.cpp/build-ios-sim 2>/dev/null || true   # clear a failed earlier attempt
if ! command -v brew >/dev/null; then echo "Install Homebrew first: https://brew.sh"; exit 1; fi
command -v cmake >/dev/null || brew install cmake
command -v xcodegen >/dev/null || brew install xcodegen

../fetch_llama.sh
if [ ! -d ../vendor/llama.cpp/build-apple/llama.xcframework ]; then
  echo "== Building llama.cpp for iPhone (Metal). About 5-15 minutes, once."
  (cd ../vendor/llama.cpp && ./build-xcframework.sh ios-device ios-sim)
fi

export BUNDLE_ID=${BUNDLE_ID:-ai.nuqta.ocr.$(whoami | tr -cd 'a-zA-Z0-9')}
export DEVELOPMENT_TEAM=${DEVELOPMENT_TEAM:-}
echo "== Generating NuqtaOCR.xcodeproj (bundle id $BUNDLE_ID)"
xcodegen generate -q
open NuqtaOCR.xcodeproj
cat <<MSG

Done. In Xcode:
  1. Click NuqtaOCR (blue icon, top left) > target NuqtaOCR > Signing & Capabilities > Team: pick your Apple ID.
  2. Plug in your iPhone, unlock it, pick it at the top of the window, press Run (the play button).
  3. First time only, on the iPhone: Settings > General > VPN & Device Management > trust your Apple ID,
     and Settings > Privacy & Security > Developer Mode > On (the phone restarts).
MSG
