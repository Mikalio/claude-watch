package io.github.mikalio.wristling

import android.content.ComponentName
import android.content.Context
import android.util.Log
import androidx.wear.tiles.TileService
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.json.JSONObject

/**
 * Receives the relay's silent pushes and refreshes the tile and the complication. A push that
 * changes nothing on them (a keepalive, the session list) is only saved, to spare the battery: the
 * face and the tile pick up its time at their own next refresh, well before "out of date" is due.
 */
class MessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val now = System.currentTimeMillis() / 1000
        val new = ClaudeState.fromPush(opened(message.data) ?: return, now)
        val old = ClaudeState.load(this)
        if (old != null && new.sent < old.sent) return // held back while the watch slept, and overtaken
        ClaudeState.save(this, new)
        if (old == null || !new.looksLike(old.shown(now))) refreshEverywhere(this)
    }

    /** What the push says. Null if it's sealed and this build can't open it. */
    private fun opened(data: Map<String, String>): Map<String, String>? {
        val sealed = data["sealed"] ?: return data
        return try {
            val json = JSONObject(Sealed.open(sealed, BuildConfig.PUSH_KEY))
            Log.i("ClaudeWatch", "opened a sealed push")
            json.keys().asSequence().associateWith { json.getString(it) }
        } catch (e: Exception) {
            Log.w("ClaudeWatch", "a sealed push couldn't be opened: check PUSH_KEY on the relay and in this build", e)
            null
        }
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
