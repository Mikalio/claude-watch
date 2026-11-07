package io.github.mikalio.claudewatch

import android.app.PendingIntent
import android.content.Intent
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationText
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.CountUpTimeReference
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.data.TimeDifferenceComplicationText
import androidx.wear.watchface.complications.data.TimeDifferenceStyle
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import java.time.Instant

/**
 * Claude's state for watch faces: as a word (short text), and as a number from 0 to 4 (ranged
 * value) so a watch face can pick a scene by comparing numbers. See ClaudeState.CODES. The ranged
 * value also carries the line under the word as its text and the count per state as its title, for
 * the Claude face.
 */
class StatusComplicationService : SuspendingComplicationDataSourceService() {

    override fun getPreviewData(type: ComplicationType): ComplicationData? = data(type, ClaudeState.SAMPLE)

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? =
        data(request.complicationType, ClaudeState.load(this)?.shown(System.currentTimeMillis() / 1000))

    private fun data(type: ComplicationType, state: ClaudeState?): ComplicationData? {
        val shown = state ?: ClaudeState.SAMPLE.copy(state = "sleeping", project = "")
        val word = PlainComplicationText.Builder(shown.word).build()
        val description = PlainComplicationText.Builder("Claude: ${shown.word}").build()
        return when (type) {
            ComplicationType.SHORT_TEXT -> ShortTextComplicationData.Builder(word, description)
                .setTapAction(openApp())
                .build()
            ComplicationType.RANGED_VALUE ->
                RangedValueComplicationData.Builder(
                    value = shown.code.toFloat(),
                    min = 0f,
                    max = (ClaudeState.CODES.size - 1).toFloat(),
                    contentDescription = description,
                )
                    .setTitle(shown.counts?.let { PlainComplicationText.Builder(it).build() })
                    .setText(detail(shown))
                    .setTapAction(openApp())
                    .build()
            else -> null
        }
    }

    /** The line under the word on the Claude face; "Last update 12 min ago" counts up by itself. */
    private fun detail(s: ClaudeState): ComplicationText = when (s.state) {
        "sleeping" -> PlainComplicationText.Builder("No sessions running").build()
        "stale" -> TimeDifferenceComplicationText.Builder(
            TimeDifferenceStyle.SHORT_SINGLE_UNIT,
            CountUpTimeReference(Instant.ofEpochSecond(s.received)),
        ).setText("Last update ^1 ago").build()
        else -> PlainComplicationText.Builder(s.named).build()
    }

    private fun openApp() = PendingIntent.getActivity(
        this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
    )
}
