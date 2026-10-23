import Foundation

/// Downloads the 0.8B GGUF and its vision file from Hugging Face once, then keeps them on the phone.
final class ModelStore: NSObject, URLSessionDownloadDelegate {
    // bytes = the current files on Hugging Face (reading settings baked in, 2026-10-22); old = the first upload, still accepted
    struct Part { let name: String; let bytes: Int64; let old: Int64 }
    static let parts = [Part(name: "nuqta-ocr-0.8b-Q4_K_M.gguf", bytes: 559_595_520, old: 559_595_392),
                        Part(name: "nuqta-ocr-0.8b-mmproj-f16.gguf", bytes: 204_986_688, old: 204_986_656)]
    static let totalBytes = parts.reduce(0) { $0 + $1.bytes }
    private static let base = "https://huggingface.co/SalahALHaismawi/Nuqta-OCR-0.8B-GGUF/resolve/main/"

    static var dir: URL {
        let d = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("models")
        try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        return d
    }
    static var modelURL: URL { dir.appendingPathComponent(parts[0].name) }
    static var mmprojURL: URL { dir.appendingPathComponent(parts[1].name) }

    static func size(_ u: URL) -> Int64 { ((try? FileManager.default.attributesOfItem(atPath: u.path)[.size]) as? NSNumber)?.int64Value ?? 0 }
    /// within a few KB of the expected size: metadata-only updates of the GGUFs change it by a few bytes
    static func ok(_ n: Int64, _ p: Part) -> Bool { abs(n - p.bytes) < 65_536 }
    static var ready: Bool { parts.allSatisfy { ok(size(dir.appendingPathComponent($0.name)), $0) } }

    private var onProgress: ((Int64) -> Void)?
    private var done: Int64 = 0
    private var cont: CheckedContinuation<URL, Error>?
    private lazy var session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)

    /// Downloads whatever is missing; onProgress gets bytes done across both files.
    func download(onProgress: @escaping (Int64) -> Void) async throws {
        self.onProgress = onProgress
        done = 0
        for p in Self.parts {
            let dest = Self.dir.appendingPathComponent(p.name)
            if Self.ok(Self.size(dest), p) { done += p.bytes; onProgress(done); continue }
            let tmp: URL = try await withCheckedThrowingContinuation { c in
                cont = c
                session.downloadTask(with: URL(string: Self.base + p.name)!).resume()
            }
            try? FileManager.default.removeItem(at: dest)
            try FileManager.default.moveItem(at: tmp, to: dest)
            var v = URLResourceValues(); v.isExcludedFromBackup = true
            var d = dest; try? d.setResourceValues(v)
            guard Self.ok(Self.size(dest), p) else { throw NSError(domain: "Nuqta", code: 1, userInfo: [NSLocalizedDescriptionKey: "Download incomplete, try again"]) }
            done += p.bytes
            onProgress(done)
        }
    }

    func urlSession(_ s: URLSession, downloadTask t: URLSessionDownloadTask, didWriteData _: Int64, totalBytesWritten w: Int64, totalBytesExpectedToWrite _: Int64) {
        onProgress?(done + w)
    }

    func urlSession(_ s: URLSession, downloadTask t: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {
        // the file at `location` disappears when this returns: move it somewhere we own first
        let keep = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        do { try FileManager.default.moveItem(at: location, to: keep); cont?.resume(returning: keep) }
        catch { cont?.resume(throwing: error) }
        cont = nil
    }

    func urlSession(_ s: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error { cont?.resume(throwing: error); cont = nil }
    }
}
