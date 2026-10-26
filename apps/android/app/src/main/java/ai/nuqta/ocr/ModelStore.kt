package ai.nuqta.ocr

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

/** Downloads the 0.8B GGUF and its vision file from Hugging Face once, then keeps them on the device. */
class ModelStore(ctx: Context) {
    private val dir = File(ctx.getExternalFilesDir(null) ?: ctx.filesDir, "models").apply { mkdirs() }
    private val base = "https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B-GGUF/resolve/main/"

    // bytes = the current files on Hugging Face (reading settings baked in, 2026-10-22); `old` = the first upload,
    // still accepted so phones that already have it do not download again
    data class Part(val name: String, val bytes: Long, val old: Long)
    val parts = listOf(Part("nuqta-ocr-0.8b-Q4_K_M.gguf", 559_595_520L, 559_595_392L),
                       Part("nuqta-ocr-0.8b-mmproj-f16.gguf", 204_986_688L, 204_986_656L))
    val totalBytes = parts.sumOf { it.bytes }

    val model get() = File(dir, parts[0].name)
    val mmproj get() = File(dir, parts[1].name)
    // within a few KB of the expected size: metadata-only updates of the GGUFs change it by a few bytes
    private fun ok(n: Long, p: Part) = kotlin.math.abs(n - p.bytes) < 65_536
    fun ready() = parts.all { ok(File(dir, it.name).length(), it) }

    /** Resumable download; onProgress gets bytes done so far across both files. */
    fun download(onProgress: (Long) -> Unit) {
        var done = 0L
        for (p in parts) {
            val out = File(dir, p.name)
            if (ok(out.length(), p)) { done += p.bytes; onProgress(done); continue }
            val tmp = File(dir, p.name + ".part")
            var have = tmp.length()
            val conn = URL(base + p.name).openConnection() as HttpURLConnection
            conn.instanceFollowRedirects = true
            conn.connectTimeout = 20_000; conn.readTimeout = 60_000
            if (have > 0) conn.setRequestProperty("Range", "bytes=$have-")
            val code = conn.responseCode
            if (code == 200) have = 0 else if (code != 206) throw RuntimeException("Download failed (HTTP $code)")
            conn.inputStream.use { inp ->
                FileOutputStream(tmp, have > 0).use { os ->
                    val buf = ByteArray(1 shl 16)
                    var last = 0L
                    while (true) {
                        val n = inp.read(buf); if (n < 0) break
                        os.write(buf, 0, n); have += n
                        if (have - last > (1 shl 20)) { last = have; onProgress(done + have) }
                    }
                }
            }
            if (!ok(have, p)) throw RuntimeException("Download incomplete, tap to resume")
            tmp.renameTo(out)
            done += p.bytes; onProgress(done)
        }
    }
}
