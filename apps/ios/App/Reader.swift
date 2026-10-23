import SwiftUI
import UIKit

/// App state: model setup, the chosen page, and one read at a time with a paced display.
@MainActor
final class Reader: ObservableObject {
    enum Phase: Equatable { case needsDownload, downloading(Double), loading, ready, failed(String) }

    static let prompts: [(String, String)] = [
        ("As written", "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image."),
        ("Markdown", "Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include only the diacritics visible in the image."),
        ("No tashkeel", "Transcribe the Arabic text in this image without any diacritics."),
    ]
    static let samples: [(file: String, label: String, mode: Int)] = [
        ("book", "Vowelled book", 0), ("table", "Table", 1), ("passport", "Passport", 0), ("old_book", "Old scan", 1)]

    @Published var phase: Phase = ModelStore.ready ? .loading : .needsDownload
    @Published var page: UIImage?
    @Published var sample: Int? = 0
    @Published var mode = 0
    @Published var accurate = true
    @Published var running = false
    @Published var shown = ""
    @Published var status = ""
    @Published var stats = ""

    private let store = ModelStore()
    private var stop = false
    private var current: Buffer?

    init() {
        page = Self.sampleImage(0)
        if ModelStore.ready { load() }
    }

    static func sampleImage(_ i: Int) -> UIImage? {
        guard let u = Bundle.main.url(forResource: samples[i].file, withExtension: "jpg") else { return nil }
        return UIImage(contentsOfFile: u.path)
    }

    func pickSample(_ i: Int) { sample = i; page = Self.sampleImage(i); mode = Self.samples[i].mode; shown = ""; status = ""; stats = "" }
    func pickPhoto(_ img: UIImage) { sample = nil; page = img; shown = ""; status = ""; stats = "" }

    func download() {
        phase = .downloading(0)
        UIApplication.shared.isIdleTimerDisabled = true
        Task {
            do {
                try await store.download { done in
                    Task { @MainActor in self.phase = .downloading(Double(done) / Double(ModelStore.totalBytes)) }
                }
                UIApplication.shared.isIdleTimerDisabled = false
                load()
            } catch {
                UIApplication.shared.isIdleTimerDisabled = false
                phase = .failed(error.localizedDescription)
            }
        }
    }

    func load() {
        phase = .loading
        Task.detached {
            let err = NuqtaEngine.loadModel(ModelStore.modelURL.path, mmproj: ModelStore.mmprojURL.path, threads: 4)
            await MainActor.run { self.phase = err == nil ? .ready : .failed(err!) }
        }
    }

    // MARK: reading

    /// Text shared between the reading thread and the display; all access is locked.
    final class Buffer: @unchecked Sendable {
        private let lock = NSLock()
        private var text = ""
        private var _finished = false, _stopped = false
        func append(_ s: String) { lock.lock(); text += s; lock.unlock() }
        func snapshot() -> String { lock.lock(); defer { lock.unlock() }; return text }
        var finished: Bool { get { lock.lock(); defer { lock.unlock() }; return _finished } set { lock.lock(); _finished = newValue; lock.unlock() } }
        var stopped: Bool { get { lock.lock(); defer { lock.unlock() }; return _stopped } set { lock.lock(); _stopped = newValue; lock.unlock() } }
    }

    func toggleRead() {
        if running { stop = true; current?.stopped = true; return }
        guard let page else { return }
        let prompt = Self.prompts[mode].1
        let mp = accurate ? 2.4 : 1.0
        running = true; stop = false
        shown = ""; stats = ""; status = "Looking at the page…"
        UIApplication.shared.isIdleTimerDisabled = true
        let buf = Buffer()
        current = buf
        let t0 = Date()

        // Paced display: the model writes in bursts (a short image read between strips), so show the text at its
        // average rate, pauses included; text written ahead covers each read and the page flows without stopping.
        let pacer = Task { @MainActor in
            var shownCount = 0.0
            var last = Date()
            while !Task.isCancelled {
                let now = Date()
                let dt = now.timeIntervalSince(last); last = now
                let all = buf.snapshot()
                let total = Double(all.count)
                if total > 0 {
                    var rate = total / max(now.timeIntervalSince(t0), 0.5) * 0.95
                    let backlog = total - shownCount
                    if buf.finished { rate = max(rate, backlog / 0.4) } else if backlog > rate * 5 { rate *= 1.6 }
                    shownCount = min(total, shownCount + rate * dt)
                    self.shown = Self.clean(String(all.prefix(Int(shownCount))))
                    if buf.finished && shownCount >= total { break }
                } else if buf.finished { break }
                try? await Task.sleep(nanoseconds: 33_000_000)
            }
        }

        Task.detached { [weak self] in
            var err: String?
            if let img = ImageUtil.rgb(page, megapixels: mp) {
            err = NuqtaEngine.readRGB(img.0, width: Int32(img.1), height: Int32(img.2), prompt: prompt,
                onStage: { s in Task { @MainActor in self?.status = s == 0 ? "Looking at the page…" : "Writing…" } },
                onText: { piece in
                    buf.append(piece)
                    return !buf.stopped
                },
                onDone: { outTokens, first, gen in
                    let line = String(format: "First words after %.1f s · %d tokens at %.0f/s · on this iPhone, offline",
                                      first, outTokens, gen > 0 ? Double(outTokens) / gen : 0)
                    Task { @MainActor in self?.stats = line }
                })
            } else { err = "could not read this image" }
            buf.finished = true
            await pacer.value
            let finalErr = err
            await MainActor.run {
                guard let self else { return }
                self.running = false
                UIApplication.shared.isIdleTimerDisabled = false
                let total = Date().timeIntervalSince(t0)
                self.shown = Self.clean(buf.snapshot())
                self.status = finalErr != nil ? "Something went wrong: \(finalErr!)" : self.stop ? String(format: "Stopped after %.0f s", total) : String(format: "Done in %.0f s", total)
            }
        }
    }

    static func clean(_ s: String) -> String {
        s.replacingOccurrences(of: "<img>image here</img>", with: "")
         .replacingOccurrences(of: "<think>[\\s\\S]*?</think>", with: "", options: .regularExpression)
         .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
