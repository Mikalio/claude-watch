package io.github.mikalio.claudewatch

import android.content.ComponentName
import android.content.Context
import androidx.wear.tiles.TileService
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Receives the relay's silent pushes and refreshes the tile and the complication. A push that
 * changes nothing on them (a keepalive, the session list) is only saved, to spare the battery: the
 * face and the tile pick up its time at their own next refresh, well before "out of date" is due.
 */
class MessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val now = System.currentTimeMillis() / 1000
        val new = ClaudeState.fromPush(message.data, now)
        val old = ClaudeState.load(this)
        if (old != null && new.sent < old.sent) return // held back while the watch slept, and overtaken
        ClaudeState.save(this, new)
        if (old == null || !new.looksLike(old.shown(now))) refreshEverywhere(this)
    }

    override fun onNewToken(token: String) {
        // The relay sends to a topic, not to this device's token: nothing to report
    }
}

fun refreshEverywhere(context: Context) {
    TileService.getUpdater(context).requestUpdate(StatusTileService::class.java)
    ComplicationDataSourceUpdateRequester
        .create(context, ComponentName(context, StatusComplicationService::class.java))
        .requestUpdateAll()
}
