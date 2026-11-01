package com.kwkaye.flipfellawatch

import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import androidx.wear.watchface.editor.EditorSession
import kotlinx.coroutines.launch

/**
 * Opens from Customise on the watch. Lets you choose what the two dials show,
 * for example Samsung Health heart rate on the left.
 */
class FlipFellaEditorActivity : ComponentActivity() {

    private var session: EditorSession? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val pad = (resources.displayMetrics.widthPixels * 0.15f).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(pad, pad, pad, pad)
        }
        column.addView(button(getString(R.string.slot_left)) { choose(SLOT_LEFT) })
        column.addView(button(getString(R.string.slot_right)) { choose(SLOT_RIGHT) })
        column.addView(button(getString(R.string.editor_done)) { finishEditing() })
        setContentView(ScrollView(this).apply { addView(column) })

        lifecycleScope.launch {
            session = EditorSession.createOnWatchEditorSession(this@FlipFellaEditorActivity)
        }
    }

    private fun button(label: String, onClick: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { onClick() }
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = 12 }
    }

    private fun choose(slotId: Int) {
        val s = session ?: return
        lifecycleScope.launch { s.openComplicationDataSourceChooser(slotId) }
    }

    private fun finishEditing() {
        session?.close()
        session = null
        finish()
    }

    override fun onDestroy() {
        session?.close()
        session = null
        super.onDestroy()
    }
}
