package ai.nuqta.ocr

import android.graphics.Bitmap
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** Nuqta-Arabic-OCR 0.8B on the device (llama.cpp). One read at a time. */
object Engine {
    init { System.loadLibrary("nuqta") }

    interface Listener {
        fun onStage(stage: Int)            // 0 reading the image, 1 writing
        fun onText(piece: String): Boolean // false stops
        fun onDone(imageTokens: Int, outTokens: Int, encodeS: Double, genS: Double)
    }

    private external fun nativeLoad(model: String, mmproj: String, threads: Int, maxImageTokens: Int, libDir: String): String?
    private external fun nativeRead(rgb: ByteArray, w: Int, h: Int, prompt: String, maxTokens: Int, l: Listener): String?

    var isLoaded = false; private set

    fun load(model: String, mmproj: String, libDir: String): String? {
        val threads = performanceCores()
        val err = nativeLoad(model, mmproj, threads, 4096, libDir)
        isLoaded = err == null
        return err
    }

    fun read(bmp: Bitmap, prompt: String, l: Listener): String? {
        val w = bmp.width; val h = bmp.height
        val px = IntArray(w * h); bmp.getPixels(px, 0, w, 0, 0, w, h)
        val rgb = ByteArray(w * h * 3)
        for (i in px.indices) {
            val c = px[i]
            rgb[3 * i] = (c shr 16).toByte(); rgb[3 * i + 1] = (c shr 8).toByte(); rgb[3 * i + 2] = c.toByte()
        }
        return nativeRead(rgb, w, h, prompt, 4096, l)
    }

    /** The library's input rule: page-shaped images go to the target size, crops stay as they are, all capped. */
    fun prepare(src: Bitmap, targetMp: Double): Bitmap {
        val w = src.width.toDouble(); val h = src.height.toDouble()
        val target = targetMp * 1e6
        val pageShaped = max(w, h) / min(w, h) <= 2.0 && min(w, h) >= 450
        val k = when {
            w * h > target -> sqrt(target / (w * h))
            pageShaped -> sqrt(target / (w * h))
            else -> 1.0
        }
        if (k == 1.0) return src
        return Bitmap.createScaledBitmap(src, (w * k).toInt(), (h * k).toInt(), true)
    }

    /** Threads = the fast cores only: on big.LITTLE phones the small cores slow every step down. */
    fun performanceCores(): Int {
        val freqs = (0 until Runtime.getRuntime().availableProcessors()).mapNotNull { i ->
            runCatching { java.io.File("/sys/devices/system/cpu/cpu$i/cpufreq/cpuinfo_max_freq").readText().trim().toLong() }.getOrNull()
        }
        if (freqs.isEmpty()) return 4
        val top = freqs.max()
        return freqs.count { it >= top * 0.75 }.coerceIn(2, 6)
    }

    val PROMPTS = linkedMapOf(
        "As written" to "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image.",
        "Markdown" to "Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include only the diacritics visible in the image.",
        "No tashkeel" to "Transcribe the Arabic text in this image without any diacritics.",
    )
}
