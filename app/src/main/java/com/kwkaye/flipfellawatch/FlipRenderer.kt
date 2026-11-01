package com.kwkaye.flipfellawatch

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.os.BatteryManager
import android.os.SystemClock
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasType
import androidx.wear.watchface.ComplicationSlotsManager
import androidx.wear.watchface.DrawMode
import androidx.wear.watchface.Renderer
import androidx.wear.watchface.WatchState
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.LongTextComplicationData
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.style.CurrentUserStyleRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.ZonedDateTime
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin

// Design units: the face is drawn on a 480 x 480 grid and scaled to the screen.
private const val SIZE = 480f
private const val C = 240f

private const val BG = 0xFF070708.toInt()
private const val DISC = 0xFF0F0F11.toInt()
private const val CARD = 0xFF1B1B1B.toInt()
private const val INK = 0xFFF3F0E8.toInt()
private const val MUTED = 0xFFA0A0A6.toInt()
private const val ACCENT = 0xFFFF6A1A.toInt()
private const val PEBBLE = 0xFF4B57FF.toInt()
private const val PEBBLE_SHADE = 0xFF2329A8.toInt()

private const val FLIP_MS = 460L
private const val FLIP_STAGGER_MS = 70L
private const val STEP_GOAL = 10_000f

class FlipRenderer(
    private val context: Context,
    surfaceHolder: SurfaceHolder,
    watchState: WatchState,
    private val complicationSlotsManager: ComplicationSlotsManager,
    currentUserStyleRepository: CurrentUserStyleRepository,
) : Renderer.CanvasRenderer2<FlipRenderer.Assets>(
    surfaceHolder,
    currentUserStyleRepository,
    watchState,
    CanvasType.HARDWARE,
    16L,
    false
) {

    class Assets : SharedAssets {
        override fun onDestroy() = Unit
    }

    override suspend fun createSharedAssets() = Assets()

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val compass = Compass(context)
    private var shownHeading = 0f

    // Fonts
    private val cardFont = loadFont("fonts/robotocondensed.ttf", 800, Typeface.BOLD)
    private val labelFont = loadFont("fonts/robotocondensed.ttf", 700, Typeface.BOLD)
    private val compassFont = loadFont("fonts/sairacondensed_medium.ttf", null, Typeface.NORMAL)

    // Paints
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }
    private val dashed = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(3f, 3f), 0f)
    }

    private val pebbleBody = Path().apply {
        moveTo(100f, 22f)
        cubicTo(146f, 20f, 176f, 54f, 174f, 100f)
        cubicTo(172f, 146f, 140f, 176f, 98f, 174f)
        cubicTo(54f, 172f, 24f, 142f, 26f, 98f)
        cubicTo(28f, 56f, 58f, 24f, 100f, 22f)
        close()
    }
    private val heartPath = Path().apply {
        moveTo(12f, 21f)
        cubicTo(4f, 14f, 1f, 9.5f, 3.5f, 6f)
        cubicTo(6f, 2.5f, 10.5f, 3.5f, 12f, 7f)
        cubicTo(13.5f, 3.5f, 18f, 2.5f, 20.5f, 6f)
        cubicTo(23f, 9.5f, 20f, 14f, 12f, 21f)
        close()
    }
    private val lubber = Path().apply {
        moveTo(240f, 30f); lineTo(248f, 16f); lineTo(232f, 16f); close()
    }

    // Flip state
    private var shownDigits: String? = null
    private var previousDigits: String? = null
    private var flipStartedAt = 0L

    // Battery, refreshed every 30 seconds rather than every frame
    private var batteryPct = 0
    private var batteryReadAt = 0L

    // Pebble blinks every few seconds
    private var nextBlinkAt = SystemClock.uptimeMillis() + 3000L

    init {
        scope.launch {
            combine(watchState.isAmbient, watchState.isVisible) { ambient, visible ->
                visible == true && ambient != true
            }.collect { live -> if (live) compass.start() else compass.stop() }
        }
    }

    override fun onDestroy() {
        compass.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun render(canvas: Canvas, bounds: Rect, zonedDateTime: ZonedDateTime, sharedAssets: Assets) {
        canvas.drawColor(Color.BLACK)
        canvas.save()
        canvas.translate(bounds.left.toFloat(), bounds.top.toFloat())
        val s = bounds.width() / SIZE
        canvas.scale(s, s)
        if (renderParameters.drawMode == DrawMode.AMBIENT) {
            drawAmbient(canvas, zonedDateTime)
        } else {
            drawInteractive(canvas, zonedDateTime)
        }
        canvas.restore()
    }

    override fun renderHighlightLayer(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime,
        sharedAssets: Assets
    ) {
        renderParameters.highlightLayer?.let { canvas.drawColor(it.backgroundTint) }
        for ((_, slot) in complicationSlotsManager.complicationSlots) {
            if (slot.enabled) slot.renderHighlightLayer(canvas, zonedDateTime, renderParameters)
        }
    }

    // ------------------------------------------------------------------ interactive

    private fun drawInteractive(c: Canvas, now: ZonedDateTime) {
        fill.color = BG
        c.drawCircle(C, C, 240f, fill)

        drawBezel(c)
        drawMinuteTrack(c)

        fill.color = DISC
        c.drawCircle(C, C, 174f, fill)
        stroke.color = 0xFF1F1F23.toInt(); stroke.strokeWidth = 2f
        c.drawCircle(C, C, 174f, stroke)

        drawArcs(c)
        drawSecondsDot(c, now)

        fill.color = ACCENT
        c.drawPath(lubber, fill)

        // Battery label running up the left arc
        c.save()
        c.rotate(-90f, 76f, C)
        drawCentredText(c, "$batteryPct%", 76f, C, 15f, labelFont, MUTED)
        c.restore()

        drawHeading(c)
        drawWeekdays(c, now)
        drawDateCards(c, now)
        drawTime(c, now, animate = true)
        drawDials(c)
        drawPebble(c)
    }

    private fun drawBezel(c: Canvas) {
        stroke.color = 0xFF141417.toInt(); stroke.strokeWidth = 38f
        c.drawCircle(C, C, 219f, stroke)
        stroke.color = 0xFF2A2A2E.toInt(); stroke.strokeWidth = 1.5f
        c.drawCircle(C, C, 200f, stroke)

        // Ease towards the sensor reading so the ring glides rather than jitters.
        if (compass.hasReading) {
            val delta = ((compass.heading - shownHeading + 540f) % 360f) - 180f
            shownHeading = (shownHeading + delta * 0.2f + 360f) % 360f
        }

        c.save()
        c.rotate(-shownHeading, C, C)

        stroke.strokeCap = Paint.Cap.ROUND
        for (d in 0 until 360 step 5) {
            val major = d % 45 == 0
            val mid = d % 15 == 0
            val inner = if (major) 228f else if (mid) 231f else 233f
            stroke.color = if (major || mid) 0xFF8A8A90.toInt() else 0xFF3E3E44.toInt()
            stroke.strokeWidth = if (major) 2f else 1.4f
            radialLine(c, d.toFloat(), 237f, inner)
        }

        val points = listOf(0 to "N", 45 to "NE", 90 to "E", 135 to "SE", 180 to "S", 225 to "SW", 270 to "W", 315 to "NW")
        for ((d, name) in points) {
            val cardinal = name.length == 1
            c.save()
            c.rotate(d.toFloat(), C, C)
            drawCentredText(
                c, name, C, C - 214f,
                if (cardinal) 25f else 15f,
                compassFont,
                when {
                    name == "N" -> ACCENT
                    cardinal -> INK
                    else -> MUTED
                }
            )
            c.restore()
        }
        for (d in 30 until 360 step 30) {
            if (d % 90 == 0) continue
            c.save()
            c.rotate(d.toFloat(), C, C)
            drawCentredText(c, d.toString(), C, C - 216f, 13f, compassFont, 0xFF6E6E76.toInt())
            c.restore()
        }
        c.restore()
    }

    private fun drawMinuteTrack(c: Canvas) {
        stroke.strokeCap = Paint.Cap.ROUND
        for (i in 0 until 60) {
            val five = i % 5 == 0
            stroke.color = if (five) INK else 0xFF4A4A50.toInt()
            stroke.strokeWidth = if (five) 2.4f else 1.2f
            radialLine(c, i * 6f, 197f, if (five) 189f else 193f)
        }
    }

    private fun drawArcs(c: Canvas) {
        val oval = RectF(C - 180f, C - 180f, C + 180f, C + 180f)
        stroke.strokeWidth = 8f
        stroke.strokeCap = Paint.Cap.ROUND

        // Battery: 8 to 10 o'clock
        refreshBattery()
        stroke.color = 0xFF2A2A2E.toInt()
        c.drawArc(oval, 244f - 90f, 52f, false, stroke)
        stroke.color = INK
        c.drawArc(oval, 244f - 90f, 52f * (batteryPct / 100f).coerceIn(0f, 1f), false, stroke)

        // Steps: 2 to 4 o'clock, segmented like the original face
        stroke.color = 0xFF2A2A2E.toInt()
        c.drawArc(oval, 64f - 90f, 52f, false, stroke)
        dashed.color = INK
        dashed.strokeWidth = 8f
        c.drawArc(oval, 64f - 90f, 52f * stepProgress(), false, dashed)
    }

    private fun drawSecondsDot(c: Canvas, now: ZonedDateTime) {
        val sec = now.second + now.nano / 1_000_000_000f
        val a = Math.toRadians((sec * 6f - 90f).toDouble())
        fill.color = ACCENT
        c.drawCircle(C + cos(a).toFloat() * 193f, C + sin(a).toFloat() * 193f, 4.5f, fill)
    }

    private fun drawHeading(c: Canvas) {
        val label = if (compass.hasReading) {
            val h = shownHeading.roundToInt() % 360
            "$h° ${direction(h)}"
        } else if (compass.available) "--°" else ""
        drawCentredText(c, label, C, 79f, 17f, labelFont, ACCENT)
    }

    private fun drawWeekdays(c: Canvas, now: ZonedDateTime) {
        val letters = arrayOf("M", "T", "W", "T", "F", "S", "S")
        val today = now.dayOfWeek.value - 1
        val startX = C - 102f
        for (i in 0 until 7) {
            val cx = startX + 12f + i * 30f
            if (i == today) {
                fill.color = ACCENT
                c.drawCircle(cx, 109f, 11f, fill)
            }
            drawCentredText(c, letters[i], cx, 109f, 16f, labelFont, if (i == today) BG else 0xFFC8C8CC.toInt())
            fill.color = if (i <= today) 0xFF5A5A62.toInt() else 0xFF2A2A2E.toInt()
            c.drawCircle(cx, 127.5f, 3.5f, fill)
        }
    }

    private fun drawDateCards(c: Canvas, now: ZonedDateTime) {
        val day = "%02d".format(now.dayOfMonth)
        val month = now.month.getDisplayName(TextStyle.SHORT, Locale.UK).uppercase(Locale.UK).take(3)
        val top = 146f
        drawCard(c, RectF(179f, top, 227f, top + 34f), 6f, day, 22f, labelFont, INK, CARD)
        drawCard(c, RectF(233f, top, 301f, top + 34f), 6f, month, 22f, labelFont, INK, CARD)
    }

    private fun drawTime(c: Canvas, now: ZonedDateTime, animate: Boolean) {
        val digits = "%02d%02d".format(now.hour, now.minute)
        val clock = SystemClock.uptimeMillis()
        if (shownDigits == null) shownDigits = digits
        if (digits != shownDigits) {
            previousDigits = shownDigits
            shownDigits = digits
            flipStartedAt = clock
        }

        val lefts = floatArrayOf(92f, 162f, 254f, 324f)
        val top = 192f
        for (i in 0 until 4) {
            val rect = RectF(lefts[i], top, lefts[i] + 64f, top + 96f)
            val new = digits[i].toString()
            val old = previousDigits?.get(i)?.toString() ?: new
            val p = if (!animate || old == new) 1f
            else ((clock - flipStartedAt - i * FLIP_STAGGER_MS).toFloat() / FLIP_MS).coerceIn(0f, 1f)
            drawFlipCard(c, rect, old, new, p)
        }

        fill.color = ACCENT
        c.drawCircle(C, top + 48f - 14.5f, 4.5f, fill)
        c.drawCircle(C, top + 48f + 14.5f, 4.5f, fill)
    }

    private fun drawDials(c: Canvas) {
        val leftText = complicationText(SLOT_LEFT) ?: "--"
        val rightText = complicationText(SLOT_RIGHT) ?: "--"

        // Left dial with a heart
        c.save()
        c.translate(144f - 10f, 306f)
        c.scale(20f / 24f, 20f / 24f)
        fill.color = ACCENT
        c.drawPath(heartPath, fill)
        c.restore()
        drawCentredText(c, leftText, 144f, 346f, fitSize(leftText), labelFont, INK)

        // Right dial with a footprint
        fill.color = ACCENT
        c.drawOval(RectF(326f, 306f, 334f, 321f), fill)
        c.drawOval(RectF(337f, 309f, 345f, 324f), fill)
        drawCentredText(c, rightText, 336f, 346f, fitSize(rightText), labelFont, INK)
    }

    private fun drawPebble(c: Canvas) {
        val cx = 240f
        val cy = 352f
        val r = 48.9f

        fill.color = 0xFF151518.toInt()
        c.drawCircle(cx, cy, r, fill)
        stroke.color = 0xFF2A2A2E.toInt(); stroke.strokeWidth = 2f
        c.drawCircle(cx, cy, r, stroke)

        val clip = Path().apply { addCircle(cx, cy, r - 1f, Path.Direction.CW) }
        c.save()
        c.clipPath(clip)
        c.translate(190f, 302f)
        c.scale(100f / 88f, 100f / 88f)
        c.translate(-6f, 30f)
        c.scale(0.5f, 0.5f)

        c.save()
        c.translate(7f, 9f)
        fill.color = PEBBLE_SHADE
        c.drawPath(pebbleBody, fill)
        c.restore()
        fill.color = PEBBLE
        c.drawPath(pebbleBody, fill)

        val clock = SystemClock.uptimeMillis()
        val blinking = clock in nextBlinkAt..(nextBlinkAt + 140L)
        if (clock > nextBlinkAt + 140L) nextBlinkAt = clock + 2500L + (Math.random() * 4000).toLong()

        if (blinking) {
            stroke.color = 0xFF0B0B12.toInt(); stroke.strokeWidth = 6f; stroke.strokeCap = Paint.Cap.ROUND
            c.drawLine(62f, 80f, 94f, 80f, stroke)
            c.drawLine(106f, 80f, 138f, 80f, stroke)
        } else {
            fill.color = Color.WHITE
            c.drawCircle(78f, 80f, 18f, fill)
            c.drawCircle(122f, 80f, 18f, fill)
            fill.color = 0xFF0B0B12.toInt()
            c.drawCircle(81f, 72f, 9f, fill)
            c.drawCircle(125f, 72f, 9f, fill)
        }
        val mouth = Path().apply { moveTo(88f, 116f); quadTo(100f, 126f, 112f, 116f) }
        stroke.color = 0xFF0B0B12.toInt(); stroke.strokeWidth = 6f; stroke.strokeCap = Paint.Cap.ROUND
        c.drawPath(mouth, stroke)
        c.restore()
    }

    // ------------------------------------------------------------------ always on

    private fun drawAmbient(c: Canvas, now: ZonedDateTime) {
        stroke.strokeCap = Paint.Cap.ROUND
        for (i in 0 until 60 step 5) {
            stroke.color = 0xFF3A3A3E.toInt(); stroke.strokeWidth = 2f
            radialLine(c, i * 6f, 197f, 189f)
        }

        val day = now.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.UK).uppercase(Locale.UK).take(3)
        val month = now.month.getDisplayName(TextStyle.SHORT, Locale.UK).uppercase(Locale.UK).take(3)
        drawCentredText(c, "$day %02d $month".format(now.dayOfMonth), C, 160f, 22f, labelFont, 0xFF7A7A80.toInt())

        val digits = "%02d%02d".format(now.hour, now.minute)
        val lefts = floatArrayOf(92f, 162f, 254f, 324f)
        for (i in 0 until 4) {
            val rect = RectF(lefts[i], 192f, lefts[i] + 64f, 288f)
            stroke.color = 0xFF2A2A2E.toInt(); stroke.strokeWidth = 2f
            c.drawRoundRect(rect, 9f, 9f, stroke)
            c.drawLine(rect.left, rect.centerY(), rect.right, rect.centerY(), stroke)
            drawCentredText(c, digits[i].toString(), rect.centerX(), rect.centerY(), 88f, cardFont, 0xFF9A9A9E.toInt())
        }
        fill.color = 0xFF5A3A12.toInt()
        c.drawCircle(C, 225.5f, 4.5f, fill)
        c.drawCircle(C, 254.5f, 4.5f, fill)

        stroke.color = 0xFF3A3F8A.toInt(); stroke.strokeWidth = 2f
        c.drawCircle(240f, 352f, 30f, stroke)

        // Keep the flip state in step so waking up doesn't replay a stale flip.
        shownDigits = digits
        previousDigits = digits
    }

    // ------------------------------------------------------------------ helpers

    private fun drawFlipCard(c: Canvas, rect: RectF, old: String, new: String, p: Float) {
        if (p >= 1f) {
            drawCard(c, rect, 9f, new, 88f, cardFont, INK, CARD)
            return
        }
        val hinge = rect.centerY()
        // Static halves: new digit revealed on top, old digit still showing below.
        drawHalf(c, rect, new, top = true, shade = 0)
        drawHalf(c, rect, old, top = false, shade = 0)

        c.save()
        if (p < 0.5f) {
            // Top flap with the old digit folds down towards the hinge.
            val k = 1f - p * 2f
            c.scale(1f, k.coerceAtLeast(0.001f), rect.centerX(), hinge)
            drawHalf(c, rect, old, top = true, shade = ((1f - k) * 140).toInt())
        } else {
            // Bottom flap with the new digit falls into place.
            val k = (p - 0.5f) * 2f
            c.scale(1f, k.coerceAtLeast(0.001f), rect.centerX(), hinge)
            drawHalf(c, rect, new, top = false, shade = ((1f - k) * 140).toInt())
        }
        c.restore()

        fill.color = Color.BLACK
        c.drawRect(rect.left, hinge - 1f, rect.right, hinge + 1f, fill)
    }

    private fun drawHalf(c: Canvas, rect: RectF, value: String, top: Boolean, shade: Int) {
        val hinge = rect.centerY()
        c.save()
        if (top) c.clipRect(rect.left, rect.top, rect.right, hinge)
        else c.clipRect(rect.left, hinge, rect.right, rect.bottom)
        fill.color = CARD
        c.drawRoundRect(rect, 9f, 9f, fill)
        drawCentredText(c, value, rect.centerX(), rect.centerY(), 88f, cardFont, INK)
        if (shade > 0) {
            fill.color = Color.argb(shade.coerceIn(0, 255), 0, 0, 0)
            c.drawRoundRect(rect, 9f, 9f, fill)
        }
        c.restore()
    }

    private fun drawCard(
        c: Canvas, rect: RectF, radius: Float, value: String,
        size: Float, font: Typeface, colour: Int, bg: Int
    ) {
        fill.color = bg
        c.drawRoundRect(rect, radius, radius, fill)
        drawCentredText(c, value, rect.centerX(), rect.centerY(), size, font, colour)
        fill.color = Color.BLACK
        c.drawRect(rect.left, rect.centerY() - 1f, rect.right, rect.centerY() + 1f, fill)
    }

    private fun drawCentredText(
        c: Canvas, value: String, x: Float, centreY: Float,
        size: Float, font: Typeface, colour: Int
    ) {
        text.typeface = font
        text.textSize = size
        text.color = colour
        val fm = text.fontMetrics
        c.drawText(value, x, centreY - (fm.ascent + fm.descent) / 2f, text)
    }

    private fun radialLine(c: Canvas, deg: Float, r1: Float, r2: Float) {
        val a = Math.toRadians((deg - 90f).toDouble())
        val cs = cos(a).toFloat()
        val sn = sin(a).toFloat()
        c.drawLine(C + cs * r1, C + sn * r1, C + cs * r2, C + sn * r2, stroke)
    }

    private fun fitSize(value: String) = when {
        value.length <= 3 -> 30f
        value.length <= 5 -> 26f
        else -> 22f
    }

    private fun direction(h: Int): String {
        val names = arrayOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        return names[((h + 22.5f) / 45f).toInt() % 8]
    }

    private fun refreshBattery() {
        val clock = SystemClock.uptimeMillis()
        if (batteryReadAt != 0L && clock - batteryReadAt < 30_000L) return
        batteryReadAt = clock
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        if (level >= 0 && scale > 0) batteryPct = (level * 100f / scale).roundToInt()
    }

    private fun complicationData(slotId: Int): ComplicationData? =
        complicationSlotsManager.complicationSlots[slotId]?.complicationData?.value

    private fun complicationText(slotId: Int): String? {
        val now = Instant.now()
        return when (val d = complicationData(slotId)) {
            is ShortTextComplicationData -> d.text.getTextAt(context.resources, now).toString()
            is RangedValueComplicationData ->
                d.text?.getTextAt(context.resources, now)?.toString() ?: d.value.roundToInt().toString()
            is LongTextComplicationData -> d.text.getTextAt(context.resources, now).toString()
            else -> null
        }?.takeIf { it.isNotBlank() }
    }

    private fun stepProgress(): Float {
        val d = complicationData(SLOT_RIGHT)
        if (d is RangedValueComplicationData && d.max > d.min) {
            return ((d.value - d.min) / (d.max - d.min)).coerceIn(0f, 1f)
        }
        val raw = complicationText(SLOT_RIGHT) ?: return 0f
        val lower = raw.lowercase(Locale.UK)
        val number = lower.filter { it.isDigit() || it == '.' }.toFloatOrNull() ?: return 0f
        val steps = if (lower.contains('k')) number * 1000f else number
        return (steps / STEP_GOAL).coerceIn(0f, 1f)
    }

    private fun loadFont(path: String, weight: Int?, fallbackStyle: Int): Typeface =
        try {
            val builder = Typeface.Builder(context.assets, path)
            if (weight != null) builder.setFontVariationSettings("'wght' $weight")
            builder.build() ?: Typeface.create("sans-serif-condensed", fallbackStyle)
        } catch (e: Exception) {
            Typeface.create("sans-serif-condensed", fallbackStyle)
        }
}
