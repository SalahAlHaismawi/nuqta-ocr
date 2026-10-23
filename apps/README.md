# Nuqta OCR on phones

Two small apps that run **Nuqta-OCR 0.8B fully on the phone**, with no server and no internet after the first
download. They share one reading engine (`core/`), built on [llama.cpp](https://github.com/ggml-org/llama.cpp):

| | Android | iPhone |
|---|---|---|
| Runs on | the phone's fast CPU cores | the GPU (Metal) |
| Needs | Android 9+, 64-bit, ~2 GB free RAM | iOS 16+, an iPhone 13 or newer recommended |
| Build on | Linux, macOS or Windows (Android SDK + NDK) | a Mac with Xcode |

On first launch the app downloads the 0.8B GGUF and its vision file (765 MB) from
[Nuqta-OCR-0.8B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-OCR-0.8B-GGUF) and keeps them on the phone.
Then: pick a sample, take a photo or choose one, and read it as written, as Markdown or without tashkeel.

## What the engine does

`core/nuqta_core.cpp` is the same on both phones:

- **The recommended input size:** pages are enlarged to the model's 2.4 MP training size ("Most accurate"), or 1 MP
  ("Faster"). Crops are read as they are.
- **Reading in strips:** the page is cut at blank rows between text lines, never through ink, so tables stay whole.
  The first strip is short, so the first words appear in about 2 seconds instead of after the whole page has been read.
  Blank side margins are trimmed, so there is less to read. Accuracy matches reading the whole page (99.8% on a fully
  vowelled book page in our test).
- **The model's settings:** greedy decoding, thinking switched off, a loop guard.
- **Steady text on screen:** text is shown at its average rate, so the short pause while the next strip is read does
  not show.

`core/host_test.cpp` runs the same engine on a desktop against a llama.cpp build, which is how it was tuned.

## Android

```bash
cd apps
./fetch_llama.sh                      # llama.cpp at the tested version, into apps/vendor/
cd android
echo "sdk.dir=$HOME/Android/Sdk" > local.properties
./gradlew assembleRelease             # app/build/outputs/apk/release/app-release.apk
```

It needs the Android SDK with NDK 28.2 and CMake 3.31 (install them from Android Studio's SDK Manager or with
`sdkmanager "ndk;28.2.13676358" "cmake;3.31.6"`). The APK is signed with the debug key so it installs directly;
use your own key to publish it. Copy the APK to the phone and open it, allowing "install unknown apps".

## iPhone

On a Mac with Xcode (open it once and install the iOS platform: Xcode > Settings > Components) and
[Homebrew](https://brew.sh):

```bash
cd apps/ios
./setup.sh                            # builds llama.cpp for iOS once (5-15 min), generates the project, opens Xcode
```

In Xcode: target **NuqtaOCR** > **Signing & Capabilities** > **Team**: your Apple ID (a free one works). Plug in the
iPhone, select it at the top, press **Run**. The first time, turn on Developer Mode on the iPhone
(Settings > Privacy & Security) and trust your Apple ID (Settings > General > VPN & Device Management). With a free
Apple ID the app has to be reinstalled every 7 days.

If `setup.sh` says the iPhone SDK is missing, point the command-line tools at Xcode:
`sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`.

## License

Apache-2.0, like the models. llama.cpp is MIT. The fonts (Noto Naskh Arabic, Source Serif 4, IBM Plex Sans) are OFL.
The sample pages: a Hindawi book page (CC BY 4.0), a Misraj-DocOCR page (Apache-2.0), a synthetic passport, and an
old scanned book page.
