package io.github.mikalio.wristling

import android.app.Application
import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging

/** Listens on the relay's Firebase topic from the moment the app first runs. */
class ClaudeWatchApp : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseMessaging.getInstance().subscribeToTopic(BuildConfig.FCM_TOPIC).addOnCompleteListener { task ->
            Log.i("ClaudeWatch", "topic subscription ok: ${task.isSuccessful}")
            ClaudeState.prefs(this).edit().putBoolean("subscribed", task.isSuccessful).apply()
        }
    }
}
