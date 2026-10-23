package ai.nuqta.ocr

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.core.content.res.ResourcesCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import com.google.android.material.progressindicator.LinearProgressIndicator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

class MainActivity : AppCompatActivity() {
    private lateinit var store: ModelStore
    private var page: Bitmap? = null
    private var running = false
    @Volatile private var stop = false
    private var ticker: Job? = null
    private var shotUri: Uri? = null

    private val v by lazy { Views(this) }

    private val pick = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> uri?.let { setPage(decode(it)) } }
    private val shoot = registerForActivityResult(ActivityResultContracts.TakePicture()) { ok -> if (ok) shotUri?.let { setPage(decode(it)) } }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        store = ModelStore(this)
        styleType()
        buildSamples()
        buildModes()

        v.gallery.setOnClickListener { pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }
        v.camera.setOnClickListener {
            val f = File(cacheDir, "shots").apply { mkdirs() }.let { File(it, "shot.jpg") }
            shotUri = FileProvider.getUriForFile(this, "ai.nuqta.ocr.files", f)
            shoot.launch(shotUri!!)
        }
        v.go.setOnClickListener { if (running) stop = true else read() }
        v.copy.setOnClickListener {
            (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Nuqta", v.out.text))
            Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
        }
        v.dlButton.setOnClickListener { download() }

        @Suppress("DEPRECATION") (intent?.getParcelableExtra<Uri>(Intent.EXTRA_STREAM))?.let { setPage(decode(it)) }
        if (store.ready()) loadModel() else showSetup()
    }

    // ------------------------------------------------------------------ setup
    private fun showSetup() { v.setup.visibility = View.VISIBLE; v.main.visibility = View.GONE }

    private fun download() {
        v.dlButton.isEnabled = false; v.dlButton.text = "Downloading…"
        v.dlBar.visibility = View.VISIBLE; v.dlText.visibility = View.VISIBLE
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        lifecycleScope.launch {
            val err = withContext(Dispatchers.IO) {
                runCatching {
                    store.download { done ->
                        runOnUiThread {
                            v.dlBar.setProgressCompat((done * 1000 / store.totalBytes).toInt(), true)
                            v.dlText.text = String.format(Locale.US, "%d of %d MB", done shr 20, store.totalBytes shr 20)
                        }
                    }
                }.exceptionOrNull()
            }
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            if (err != null) {
                v.dlButton.isEnabled = true; v.dlButton.text = "Resume download"
                v.dlText.text = err.message ?: "Download failed"
            } else loadModel()
        }
    }

    private fun loadModel() {
        v.setup.visibility = View.VISIBLE
        v.setupTitle.text = "Getting ready…"
        v.setupBody.text = "Loading Nuqta-OCR 0.8B into memory. This takes a few seconds."
        v.dlButton.visibility = View.GONE; v.dlBar.visibility = View.VISIBLE; v.dlBar.isIndeterminate = true
        v.dlText.visibility = View.GONE
        lifecycleScope.launch {
            val err = withContext(Dispatchers.Default) {
                Engine.load(store.model.absolutePath, store.mmproj.absolutePath, applicationInfo.nativeLibraryDir)
            }
            if (err != null) {
                v.setupTitle.text = "Could not load the model"
                v.setupBody.text = err
                return@launch
            }
            v.setup.visibility = View.GONE
            v.main.visibility = View.VISIBLE
            if (page == null) selectSample(0)
        }
    }

    // ------------------------------------------------------------------ input
    private val sampleNames = listOf("book" to "Vowelled book", "table" to "Table", "passport" to "Passport", "old_book" to "Old scan")
    private val sampleModes = listOf(0, 1, 0, 1)

    private fun buildSamples() {
        val d = resources.displayMetrics.density
        sampleNames.forEachIndexed { i, (file, label) ->
            val col = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
                setPadding((6 * d).toInt(), (6 * d).toInt(), (6 * d).toInt(), (8 * d).toInt())
                setBackgroundResource(R.drawable.thumb_bg)
                layoutParams = LinearLayout.LayoutParams((96 * d).toInt(), LinearLayout.LayoutParams.WRAP_CONTENT).apply { marginEnd = (10 * d).toInt() }
                tag = i
                setOnClickListener { selectSample(i) }
            }
            col.addView(ImageView(this).apply {
                scaleType = ImageView.ScaleType.CENTER_CROP
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, (96 * d).toInt())
                setImageBitmap(assets.open("samples/$file.jpg").use { BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = 8 }) })
            })
            col.addView(TextView(this).apply {
                text = label; textSize = 12f; setTextColor(getColor(R.color.ink)); gravity = Gravity.CENTER
                setPadding(0, (6 * d).toInt(), 0, 0)
            })
            v.samples.addView(col)
        }
    }

    private fun selectSample(i: Int) {
        for (k in 0 until v.samples.childCount) v.samples.getChildAt(k).isSelected = k == i
        setPage(assets.open("samples/${sampleNames[i].first}.jpg").use { BitmapFactory.decodeStream(it) }, keepSelection = true)
        (v.modes.getChildAt(sampleModes[i]) as Chip).isChecked = true
    }

    private fun setPage(bmp: Bitmap?, keepSelection: Boolean = false) {
        bmp ?: return
        if (!keepSelection) for (k in 0 until v.samples.childCount) v.samples.getChildAt(k).isSelected = false
        page = bmp
        v.preview.setImageBitmap(bmp)
        v.outWrap.visibility = View.GONE; v.status.text = ""
    }

    private fun decode(uri: Uri): Bitmap? = runCatching {
        ImageDecoder.decodeBitmap(ImageDecoder.createSource(contentResolver, uri)) { dec, info, _ ->
            dec.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val mp = info.size.width.toLong() * info.size.height
            if (mp > 12_000_000) { val k = Math.sqrt(12e6 / mp); dec.setTargetSize((info.size.width * k).toInt(), (info.size.height * k).toInt()) }
        }.copy(Bitmap.Config.ARGB_8888, false)
    }.getOrNull()

    private fun buildModes() {
        Engine.PROMPTS.keys.forEachIndexed { i, label ->
            v.modes.addView(Chip(this).apply {
                text = label; id = View.generateViewId(); isCheckable = true; isChecked = i == 0
                setTextColor(getColorStateList(R.color.ink))
            })
        }
    }

    // ------------------------------------------------------------------ read
    private fun read() {
        val src = page ?: return
        val mode = (0 until v.modes.childCount).first { (v.modes.getChildAt(it) as Chip).isChecked }
        val prompt = Engine.PROMPTS.values.elementAt(mode)
        val mp = if (v.quality.checkedButtonId == R.id.fast) 1.0 else 2.4
        running = true; stop = false
        v.go.text = "Stop"
        v.outWrap.visibility = View.VISIBLE; v.out.text = ""; v.stats.text = ""
        v.out.textSize = if (mode == 1) 16f else 19f
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val t0 = SystemClock.elapsedRealtime()
        var stage = 0
        var tokens = 0
        var genStart = 0L
        var firstAt = 0L
        ticker = lifecycleScope.launch {
            while (isActive) {
                val s = (SystemClock.elapsedRealtime() - t0) / 1000
                v.status.text = if (stage == 0) "Looking at the page… ${s}s" else {
                    val g = (SystemClock.elapsedRealtime() - genStart) / 1000.0
                    String.format(Locale.US, "Writing… %ds · %.0f tokens/s", s, if (g > 0) tokens / g else 0.0)
                }
                delay(250)
            }
        }
        val sb = StringBuilder()
        // Paced display: the model writes in bursts (a short image read between strips), so show the text at its
        // average rate, pauses included. Text written ahead covers each read and the page flows without stopping.
        var genDone = false
        val pacer = lifecycleScope.launch {
            var shown = 0.0
            var last = SystemClock.elapsedRealtime()
            while (isActive) {
                val now = SystemClock.elapsedRealtime()
                val dt = (now - last) / 1000.0; last = now
                val total = synchronized(sb) { sb.length }
                if (total > 0) {
                    var rate = total / maxOf((now - t0) / 1000.0, 0.5) * 0.95
                    val backlog = total - shown
                    if (genDone) rate = maxOf(rate, backlog / 0.4)
                    else if (backlog > rate * 5) rate *= 1.6
                    shown = minOf(total.toDouble(), shown + rate * dt)
                    val n = shown.toInt()
                    v.out.text = clean(synchronized(sb) { sb.substring(0, n) })
                    if (genDone && n >= total) break
                } else if (genDone) break
                delay(33)
            }
        }
        lifecycleScope.launch {
            val err = withContext(Dispatchers.Default) {
                val input = Engine.prepare(src, mp)
                Engine.read(input, prompt, object : Engine.Listener {
                    override fun onStage(s: Int) { stage = s; if (s == 1) genStart = SystemClock.elapsedRealtime() }
                    override fun onText(piece: String): Boolean {
                        if (tokens == 0) firstAt = SystemClock.elapsedRealtime()
                        tokens++
                        synchronized(sb) { sb.append(piece) }
                        return !stop
                    }
                    override fun onDone(imageTokens: Int, outTokens: Int, encodeS: Double, genS: Double) {
                        runOnUiThread {
                            v.stats.text = String.format(Locale.US, "First words after %.1f s · %d tokens at %.0f/s · on this phone, offline",
                                (firstAt - t0) / 1000.0, outTokens, if (genS > 0) outTokens / genS else 0.0)
                        }
                    }
                })
            }
            genDone = true
            pacer.join()
            ticker?.cancel()
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            running = false
            v.go.text = "Read the page"
            v.out.text = clean(sb.toString())
            val total = (SystemClock.elapsedRealtime() - t0) / 1000.0
            v.status.text = when {
                err != null -> "Something went wrong: $err"
                stop -> String.format(Locale.US, "Stopped after %.0f s", total)
                else -> String.format(Locale.US, "Done in %.0f s", total)
            }
        }
    }

    private fun clean(s: String) = s.replace("<img>image here</img>", "").replace(Regex("<think>.*?</think>", RegexOption.DOT_MATCHES_ALL), "").trim()

    // ------------------------------------------------------------------ type
    private fun styleType() {
        val naskh = ResourcesCompat.getFont(this, R.font.noto_naskh)
        val serif = ResourcesCompat.getFont(this, R.font.source_serif)
        v.brand.typeface = Typeface.create(naskh, 700, false)
        v.headline.typeface = Typeface.create(serif, 600, false)
        v.setupTitle.typeface = Typeface.create(serif, 600, false)
        v.out.typeface = naskh
    }

    private class Views(a: AppCompatActivity) {
        val setup: LinearLayout = a.findViewById(R.id.setup)
        val setupTitle: TextView = a.findViewById(R.id.setupTitle)
        val setupBody: TextView = a.findViewById(R.id.setupBody)
        val dlBar: LinearProgressIndicator = a.findViewById(R.id.dlBar)
        val dlText: TextView = a.findViewById(R.id.dlText)
        val dlButton: MaterialButton = a.findViewById(R.id.dlButton)
        val main: LinearLayout = a.findViewById(R.id.main)
        val samples: LinearLayout = a.findViewById(R.id.samples)
        val camera: MaterialButton = a.findViewById(R.id.camera)
        val gallery: MaterialButton = a.findViewById(R.id.gallery)
        val preview: ImageView = a.findViewById(R.id.preview)
        val modes: ChipGroup = a.findViewById(R.id.modes)
        val quality: MaterialButtonToggleGroup = a.findViewById(R.id.quality)
        val go: MaterialButton = a.findViewById(R.id.go)
        val status: TextView = a.findViewById(R.id.status)
        val outWrap: LinearLayout = a.findViewById(R.id.outWrap)
        val out: TextView = a.findViewById(R.id.out)
        val copy: TextView = a.findViewById(R.id.copy)
        val stats: TextView = a.findViewById(R.id.stats)
        val brand: TextView = a.findViewById(R.id.brand)
        val headline: TextView = a.findViewById(R.id.headline)
    }
}
