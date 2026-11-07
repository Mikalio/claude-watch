package io.github.mikalio.claudewatch

import android.app.Activity
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.TextUtils
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Every session and its agents. To spare the battery it
 * only draws when it opens or a push arrives, and nothing on it moves.
 */
class MainActivity : Activity() {
    private lateinit var list: LinearLayout
    private lateinit var scroller: ScrollView
    private var k = 1f // the design is drawn for a 450 px screen; k turns its px into this watch's px

    // A push saves all its values at once and "received" is in each one, so this draws once per push
    private val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        if (key == "received" || key == "subscribed") show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        k = resources.displayMetrics.widthPixels / 450f
        list = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(0, px(44), 0, px(72))
        }
        scroller = ScrollView(this).apply {
            setBackgroundColor(Color.BLACK)
            isFocusableInTouchMode = true
            addView(list)
        }
        setContentView(scroller)
    }

    override fun onResume() {
        super.onResume()
        ClaudeState.prefs(this).registerOnSharedPreferenceChangeListener(listener)
        show()
        scroller.requestFocus() // the watch's wheel scrolls whichever view has the focus
    }

    override fun onPause() {
        ClaudeState.prefs(this).unregisterOnSharedPreferenceChangeListener(listener)
        super.onPause()
    }

    private fun show() {
        val now = System.currentTimeMillis() / 1000
        val state = ClaudeState.load(this)
        list.removeAllViews()
        list.addView(text("Sessions", 26f, WHITE, bold = true).apply { gravity = Gravity.CENTER })
        if (state == null) {
            list.addView(note("Waiting for Claude"))
            list.addView(note("The creature wakes up when a Claude Code session sends its first update."))
        } else {
            if (state.shown(now).state == "stale") list.addView(note("Out of date"))
            val rows = rows(state.sessions)
            when {
                state.sessions.isEmpty() -> list.addView(note("Waiting for the next update"))
                rows.isEmpty() -> list.addView(note("No sessions running"))
                else -> rows.forEach { list.addView(row(it, now)) }
            }
            list.addView(note("Last update ${clock(state.received)}, took ${state.received - state.sent} s"))
        }
        if (!ClaudeState.prefs(this).getBoolean("subscribed", false)) list.addView(note("Not listening yet"))
    }

    private fun rows(json: String): List<JSONObject> =
        if (json.isEmpty()) emptyList() else JSONArray(json).let { all -> List(all.length()) { all.getJSONObject(it) } }

    /** One session: "Working · 3 agents · 6 min", or "Working · PC · 6 min" without agents. */
    private fun row(session: JSONObject, now: Long): View {
        val state = session.getString("state")
        val place = ClaudeState.place(session.optInt("agents"), session.getString("where"))
        val status = "${ClaudeState.wordFor(state)} · $place · ${age(now - session.getLong("since"))}"
        val texts = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(text(session.getString("project"), 24f, WHITE, bold = true))
            addView(text(status, 18f, ClaudeState.COLOURS[state] ?: GREY))
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(px(20), 0, px(20), 0)
            background = GradientDrawable().apply {
                setColor(CARD)
                cornerRadius = 28 * k
            }
            layoutParams = LinearLayout.LayoutParams(px(340), px(92)).apply { topMargin = px(10) }
            addView(ImageView(this@MainActivity).apply {
                setImageResource(CREATURES[state] ?: if (ClaudeState.isDay(now * 1000)) R.drawable.creature_sleeping_day else R.drawable.creature_sleeping_night)
                layoutParams = LinearLayout.LayoutParams(px(56), px(48)).apply { marginEnd = px(14) }
            })
            addView(texts, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
    }

    private fun age(seconds: Long): String {
        val minutes = seconds / 60
        return when {
            minutes < 1 -> "now"
            minutes < 60 -> "$minutes min"
            else -> "${minutes / 60} h"
        }
    }

    private fun note(value: String) = TextView(this).apply {
        text = value
        setTextColor(GREY)
        setTextSize(TypedValue.COMPLEX_UNIT_PX, 18 * k)
        gravity = Gravity.CENTER
        layoutParams = LinearLayout.LayoutParams(px(340), LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = px(14) }
    }

    private fun text(value: String, size: Float, colour: Int, bold: Boolean = false) = TextView(this).apply {
        text = value
        setTextColor(colour)
        setTextSize(TypedValue.COMPLEX_UNIT_PX, size * k)
        if (bold) typeface = Typeface.DEFAULT_BOLD
        maxLines = 1
        ellipsize = TextUtils.TruncateAt.END
    }

    private fun px(designPx: Int) = (designPx * k).toInt()

    private fun clock(seconds: Long) =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(seconds * 1000))

    private companion object {
        const val WHITE = 0xFFF5F6F8.toInt()
        const val GREY = 0xFFB9BEC8.toInt()
        const val CARD = 0xFF1C1E23.toInt()
        val CREATURES = mapOf(
            "working" to R.drawable.creature_working, "needs" to R.drawable.creature_needs,
            "done" to R.drawable.creature_done,
        )
    }
}
