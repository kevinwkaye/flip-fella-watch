package com.kwkaye.flipfellawatch

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasComplication
import androidx.wear.watchface.CanvasComplicationFactory
import androidx.wear.watchface.ComplicationSlot
import androidx.wear.watchface.ComplicationSlotsManager
import androidx.wear.watchface.RenderParameters
import androidx.wear.watchface.WatchFace
import androidx.wear.watchface.WatchFaceService
import androidx.wear.watchface.WatchFaceType
import androidx.wear.watchface.WatchState
import androidx.wear.watchface.complications.ComplicationSlotBounds
import androidx.wear.watchface.complications.DefaultComplicationDataSourcePolicy
import androidx.wear.watchface.complications.SystemDataSources
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.NoDataComplicationData
import androidx.wear.watchface.style.CurrentUserStyleRepository
import java.time.ZonedDateTime

const val SLOT_LEFT = 100
const val SLOT_RIGHT = 101

private val SUPPORTED_TYPES = listOf(ComplicationType.SHORT_TEXT, ComplicationType.RANGED_VALUE)

/**
 * Flip Fella for the Galaxy Watch Ultra: face E from the design canvas.
 * Flip cards in the middle, a live compass bezel round the edge, two dials and Pebble.
 */
class FlipFellaWatchFaceService : WatchFaceService() {

    override fun createComplicationSlotsManager(
        currentUserStyleRepository: CurrentUserStyleRepository
    ): ComplicationSlotsManager {
        val factory = CanvasComplicationFactory { _, _ -> DataOnlyComplication() }

        // Left dial: pick heart rate (or anything else) from Customise on the watch.
        val left = ComplicationSlot.createRoundRectComplicationSlotBuilder(
            SLOT_LEFT,
            factory,
            SUPPORTED_TYPES,
            DefaultComplicationDataSourcePolicy(),
            ComplicationSlotBounds(RectF(100f / 480f, 296f / 480f, 188f / 480f, 372f / 480f))
        ).build()

        // Right dial: steps by default, which also drives the right-hand arc.
        val right = ComplicationSlot.createRoundRectComplicationSlotBuilder(
            SLOT_RIGHT,
            factory,
            SUPPORTED_TYPES,
            DefaultComplicationDataSourcePolicy(
                SystemDataSources.DATA_SOURCE_STEP_COUNT,
                ComplicationType.SHORT_TEXT
            ),
            ComplicationSlotBounds(RectF(292f / 480f, 296f / 480f, 380f / 480f, 372f / 480f))
        ).build()

        return ComplicationSlotsManager(listOf(left, right), currentUserStyleRepository)
    }

    override suspend fun createWatchFace(
        surfaceHolder: SurfaceHolder,
        watchState: WatchState,
        complicationSlotsManager: ComplicationSlotsManager,
        currentUserStyleRepository: CurrentUserStyleRepository
    ): WatchFace {
        val renderer = FlipRenderer(
            applicationContext,
            surfaceHolder,
            watchState,
            complicationSlotsManager,
            currentUserStyleRepository
        )
        return WatchFace(WatchFaceType.DIGITAL, renderer)
    }
}

/**
 * Holds complication data without drawing it. The renderer reads the data and
 * draws the dials itself so they match the rest of the face.
 */
class DataOnlyComplication : CanvasComplication {
    private var data: ComplicationData = NoDataComplicationData()

    private val highlightPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    override fun render(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime,
        renderParameters: RenderParameters,
        slotId: Int
    ) {
        // Drawn by FlipRenderer.
    }

    override fun drawHighlight(
        canvas: Canvas,
        bounds: Rect,
        boundsType: Int,
        zonedDateTime: ZonedDateTime,
        color: Int
    ) {
        highlightPaint.color = if (color == 0) Color.WHITE else color
        val r = bounds.height() / 2f
        canvas.drawRoundRect(RectF(bounds), r, r, highlightPaint)
    }

    override fun getData(): ComplicationData = data

    override fun loadData(complicationData: ComplicationData, loadDrawablesAsynchronous: Boolean) {
        data = complicationData
    }
}
