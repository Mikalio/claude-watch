package io.github.mikalio.claudewatch

import android.content.Context
import java.time.Instant
import java.time.ZoneId

/** What the relay last pushed: the Claude session it picked, and when the push was sent and received. */
data class ClaudeState(
    val state: String,
    val project: String,
    val where: String,
    val since: Long,
    val needs: Int,
    val working: Int,
    val done: Int,
    val agents: Int,
    val sessions: String, // the relay's session list as JSON, only read when the app is open
    val sent: Long,
    val received: Long,
) {
    val word: String get() = wordFor(state)

    /**
     * The session this state is about, as "Grocery offers · PC" or "Grocery offers · 3 agents". A long
     * name is shortened so the line fits and where it runs still shows; the Sessions screen has it whole.
     */
    val named: String
        get() {
            val place = place(agents, where)
            val room = NAMED_LENGTH - place.length - " · ".length
            val name = if (project.length <= room) project else project.take(room - 1).trimEnd() + "…"
            return "$name · $place"
        }

    /** Which sessions to mention, in the order the relay picks from: mood, how many, words. Three kinds would not fit, so the last two become "3 more". */
    val tally: List<Triple<String, Int, String>>
        get() {
            val kinds = listOf(Triple("needs", needs, "needs you"), Triple("working", working, "working"), Triple("done", done, "your turn"))
                .filter { it.second > 0 }
            return if (kinds.size < 3) kinds else listOf(kinds[0], Triple("more", kinds.drop(1).sumOf { it.second }, "more"))
        }

    /** "1 needs you · 2 working" when several sessions are active; else null. */
    val counts: String?
        get() = if (state == "stale" || needs + working + done < 2) null else tally.joinToString(" · ") { "${it.second} ${it.third}" }

    /** Whether the tile and the face would look the same, so a push needn't redraw them. */
    fun looksLike(other: ClaudeState) = forScreen() == other.forScreen()

    private fun forScreen() = copy(sessions = "", sent = 0, received = 0)

    /** The state as a number, for a watch face that compares complication values. */
    val code: Int get() = CODES.indexOf(state).coerceAtLeast(0)

    /** "Out of date" when Claude was busy but the relay's keepalive pushes stopped coming. */
    fun shown(now: Long): ClaudeState = staleAt().let { if (it != null && now > it) copy(state = "stale") else this }

    /** When this state turns "out of date" if no new push comes, in seconds; never while sleeping. */
    fun staleAt(): Long? = if (state != "sleeping") received + STALE_AFTER else null

    companion object {
        val CODES = listOf("sleeping", "working", "needs", "done", "stale")
        private val WORDS = mapOf(
            "sleeping" to "Sleeping", "working" to "Working", "needs" to "Needs you",
            "done" to "Your turn", "stale" to "Out of date", "idle" to "Idle",
        )
        val COLOURS = mapOf(
            "sleeping" to 0xFFA9A4F5.toInt(), "working" to 0xFF5BC2FF.toInt(), "needs" to 0xFFFFC233.toInt(),
            "done" to 0xFF3EE6A0.toInt(), "stale" to 0xFFAEB4BE.toInt(), "idle" to 0xFFAEB4BE.toInt(),
        )
        private const val STALE_AFTER = 40 * 60L // the relay repeats every 15 minutes while busy
        private const val NAMED_LENGTH = 27 // about what fits between the ring's sides on the face
        private const val PREFS = "claude_state"
        val SAMPLE = ClaudeState("needs", "Grocery offers", "PC", 0, 1, 0, 0, 0, "", 0, 0)

        const val DAY_STARTS = 6
        const val NIGHT_STARTS = 18

        /** Whether the home shows the day and a sleeper wears its sun hat rather than its nightcap. */
        fun isDay(millis: Long) = Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault()).hour in DAY_STARTS until NIGHT_STARTS

        fun wordFor(state: String) = WORDS[state] ?: state

        /** "3 agents" while agents run, otherwise where the session runs. */
        fun place(agents: Int, where: String) = when (agents) {
            0 -> where
            1 -> "1 agent"
            else -> "$agents agents"
        }

        fun fromPush(data: Map<String, String>, receivedAt: Long) = ClaudeState(
            state = data["state"] ?: "sleeping",
            project = data["project"].orEmpty(),
            where = data["where"].orEmpty(),
            since = data["since"]?.toLongOrNull() ?: 0,
            needs = data["needs"]?.toIntOrNull() ?: 0,
            working = data["working"]?.toIntOrNull() ?: 0,
            done = data["done"]?.toIntOrNull() ?: 0,
            agents = data["agents"]?.toIntOrNull() ?: 0,
            sessions = data["sessions"].orEmpty(),
            sent = data["sent"]?.toLongOrNull() ?: 0,
            received = receivedAt,
        )

        fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

        fun load(context: Context): ClaudeState? {
            val p = prefs(context)
            if (!p.contains("state")) return null
            return ClaudeState(
                state = p.getString("state", "sleeping")!!,
                project = p.getString("project", "")!!,
                where = p.getString("where", "")!!,
                since = p.getLong("since", 0),
                needs = p.getInt("needs", 0),
                working = p.getInt("working", 0),
                done = p.getInt("done", 0),
                agents = p.getInt("agents", 0),
                sessions = p.getString("sessions", "")!!,
                sent = p.getLong("sent", 0),
                received = p.getLong("received", 0),
            )
        }

        fun save(context: Context, s: ClaudeState) {
            prefs(context).edit()
                .putString("state", s.state).putString("project", s.project).putString("where", s.where)
                .putLong("since", s.since).putInt("needs", s.needs).putInt("working", s.working)
                .putInt("done", s.done).putInt("agents", s.agents).putString("sessions", s.sessions)
                .putLong("sent", s.sent).putLong("received", s.received)
                .apply()
        }
    }
}
