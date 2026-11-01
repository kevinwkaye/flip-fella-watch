package com.kwkaye.flipfellawatch

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

/**
 * Reads the watch's heading in real time from the rotation vector sensor.
 * Only runs while the face is awake, so it costs nothing in always-on or with the screen off.
 */
class Compass(context: Context) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val sensor: Sensor? =
        sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR)

    private val rotation = FloatArray(9)
    private val orientation = FloatArray(3)
    private var running = false

    /** Degrees clockwise from magnetic north that the top of the watch (12 o'clock) points. */
    @Volatile
    var heading: Float = 0f
        private set

    @Volatile
    var hasReading: Boolean = false
        private set

    val available: Boolean get() = sensor != null

    fun start() {
        if (running) return
        val s = sensor ?: return
        running = sensorManager.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME)
    }

    fun stop() {
        if (!running) return
        sensorManager.unregisterListener(this)
        running = false
    }

    override fun onSensorChanged(event: SensorEvent) {
        SensorManager.getRotationMatrixFromVector(rotation, event.values)
        SensorManager.getOrientation(rotation, orientation)
        var deg = Math.toDegrees(orientation[0].toDouble()).toFloat()
        if (deg < 0f) deg += 360f
        heading = deg
        hasReading = true
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
