package io.github.mikalio.claudewatch

import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.ColorBuilders.argb
import androidx.wear.protolayout.DimensionBuilders
import androidx.wear.protolayout.DimensionBuilders.degrees
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.expand
import androidx.wear.protolayout.DimensionBuilders.sp
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.ModifiersBuilders
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.protolayout.TypeBuilders
import androidx.wear.protolayout.expression.AnimationParameterBuilders
import androidx.wear.protolayout.expression.DynamicBuilders.DynamicFloat
import androidx.wear.protolayout.expression.DynamicBuilders.DynamicInstant
import androidx.wear.protolayout.expression.DynamicBuilders.DynamicInt32
import androidx.wear.protolayout.expression.DynamicBuilders.DynamicString
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * The Claude tile: a clock, the creature by its home
 * with its icon, and what Claude is doing and where. A tap anywhere opens the sessions. The home
 * shows the day from 06:00 to 18:00 and the night otherwise. Animated images don't play on the
 * Galaxy Watch4's tiles, so the creature and its icon move with the tile's own animations: it
 * breathes asleep, hammers at work, hops when it needs you and dances on your turn.
 */
class StatusTileService : TileService() {

    override fun onTileRequest(requestParams: RequestBuilders.TileRequest): ListenableFuture<TileBuilders.Tile> {
        val saved = ClaudeState.load(this)
        // The design is drawn for a 450 px screen; k turns its px into this watch's dp
        val k = requestParams.deviceConfiguration.screenWidthDp / 450f
        val now = System.currentTimeMillis()
        // The watch switches the tile by itself at these times: day and night, and "out of date"
        val changes = (dayNightChanges(now) + listOfNotNull(saved?.staleAt()?.times(1000)))
            .filter { it > now }.sorted()
        val timeline = TimelineBuilders.Timeline.Builder()
        (listOf(now) + changes).forEachIndexed { i, start ->
            val valid = TimelineBuilders.TimeInterval.Builder()
            if (i > 0) valid.setStartMillis(start)
            changes.getOrNull(i)?.let { valid.setEndMillis(it) }
            timeline.addTimelineEntry(
                TimelineBuilders.TimelineEntry.Builder()
                    .setValidity(valid.build())
                    .setLayout(LayoutElementBuilders.Layout.Builder().setRoot(screen(saved, start, k)).build())
                    .build()
            )
        }
        val tile = TileBuilders.Tile.Builder()
            .setResourcesVersion(RESOURCES_VERSION)
            .setTileTimeline(timeline.build())
            // Ask again now and then, in case the watch missed a push
            .setFreshnessIntervalMillis(15 * 60 * 1000L)
            .build()
        return Futures.immediateFuture(tile)
    }

    override fun onTileResourcesRequest(
        requestParams: RequestBuilders.ResourcesRequest,
    ): ListenableFuture<ResourceBuilders.Resources> {
        val resources = ResourceBuilders.Resources.Builder().setVersion(RESOURCES_VERSION)
        for ((id, drawable) in IMAGES) {
            resources.addIdToImageMapping(
                id,
                ResourceBuilders.ImageResource.Builder()
                    .setAndroidResourceByResId(
                        ResourceBuilders.AndroidImageResourceByResId.Builder().setResourceId(drawable).build()
                    )
                    .build(),
            )
        }
        return Futures.immediateFuture(resources.build())
    }

    /** The tile at time [t] (milliseconds), placed as in the design. */
    private fun screen(saved: ClaudeState?, t: Long, k: Float): LayoutElementBuilders.LayoutElement {
        val state = saved?.shown(t / 1000)
        val mood = state?.state ?: "sleeping"
        val texts = LayoutElementBuilders.Column.Builder()
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
            .addContent(spacer(0f, 56 * k))
            .addContent(line(clock(t, k), 380 * k, 40 * k))
            .addContent(spacer(0f, 167 * k))
            // each line keeps at least 12 px from the ring; a longer text ends in dots
            .addContent(line(text(fixed(state?.word ?: "Sleeping"), 36 * k, COLOURS.getValue(mood), bold = true), 340 * k, 40 * k))
            .addContent(spacer(0f, 2 * k))
            .addContent(line(detail(state, k), 336 * k, 28 * k))
            .addContent(spacer(0f, 2 * k))
            .addContent(line(sinceOrCounts(saved, state, k), 296 * k, 26 * k))
            .build()
        return LayoutElementBuilders.Box.Builder()
            .setWidth(expand()).setHeight(expand())
            .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_TOP)
            .setModifiers(ModifiersBuilders.Modifiers.Builder().setClickable(openApp("open")).build())
            .addContent(scene(mood, ClaudeState.isDay(t), k))
            .addContent(ring(mood, k))
            .addContent(texts)
            .build()
    }

    /** The home across the top, with the creature on the grass right of its house and its icon beside it. */
    private fun scene(mood: String, day: Boolean, k: Float): LayoutElementBuilders.LayoutElement {
        val scene = LayoutElementBuilders.Box.Builder()
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_START)
            .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_TOP)
            .addContent(image(if (day) "scene_${mood}_day" else "scene_$mood", 450 * k, 259 * k, null))
        creature(mood, day, k).forEach { scene.addContent(it) }
        // the hammer swings through the icon's usual spot, and the Zs stay clear of the hats
        val (iconX, iconY) = when (mood) {
            "working" -> 358f to 128f
            "sleeping" -> 346f to 122f
            else -> 329f to 149f
        }
        return scene.addContent(at(iconX * k, iconY * k, image("icon_$mood", 40 * k, 50 * k, iconMove(mood, k)))).build()
    }

    /** A tile has no free positioning, so spacers put each part at the design's spot. */
    private fun at(x: Float, y: Float, part: LayoutElementBuilders.LayoutElement) =
        LayoutElementBuilders.Column.Builder()
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_START)
            .addContent(spacer(0f, y))
            .addContent(
                LayoutElementBuilders.Row.Builder()
                    .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_TOP)
                    .addContent(spacer(x, 0f))
                    .addContent(part)
                    .build()
            )
            .build()

    /**
     * The creature on the grass. Asleep and at work it is several images, since a tile only moves whole
     * ones. Asleep it wears its sun hat by day and its nightcap at night, and hat and head rise and fall.
     */
    private fun creature(mood: String, day: Boolean, k: Float): List<LayoutElementBuilders.LayoutElement> = when (mood) {
        "sleeping" -> listOf(
            at(198 * k, 142 * k, image(if (day) "sleep_top_day" else "sleep_top_night", 140 * k, 91 * k, moves { setTranslationY(dpMove(0f, -8.75f * k, 2000)) })),
            at(198 * k, 212 * k, image("sleep_low", 140 * k, 35 * k, null)),
        )
        "working" -> listOf(
            at(317 * k, 226 * k, image("anvil", 63 * k, 21 * k, null)),
            at(310 * k, 170 * k, image("sparks", 98 * k, 56 * k, moves { setTranslationY(sparksFlash(k)) })),
            at(212 * k, 125 * k, worker(k)),
        )
        else -> listOf(at(219 * k, 135 * k, image(mood, 98 * k, 112 * k, creatureMove(mood, k))))
    }

    /** The worker and its arm, which jump together; the arm also turns at the shoulder, the middle of its picture. */
    private fun worker(k: Float) = LayoutElementBuilders.Box.Builder()
        .setWidth(dp(161 * k)).setHeight(dp(157 * k))
        .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_START)
        .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_TOP)
        .setModifiers(moves { setTranslationY(workerJump(k)) })
        .addContent(at(0f, 10 * k, image("working", 105 * k, 112 * k, null)))
        .addContent(at(21 * k, 10 * k, image("work_arm", 140 * k, 147 * k, moves { setRotation(hammerSwing()) })))
        .build()

    /*
     * One blow a second, all counted from the moment of impact. Each of these is one running
     * animation, and with the spinning icon that makes four, which keeps the worker from using more
     * than it needs on a watch that limits how many can run.
     */

    /** Rests on the anvil, is raised slowly, waits, and comes down fast. */
    private fun hammerSwing() = DimensionBuilders.DegreesProp.Builder(0f).setDynamicValue(
        DynamicFloat.animate(0f, HAMMER_TOP, blow(timing(560, 170), timing(120, 150)))
    ).build()

    /** A small jump as the hammer lands. */
    private fun workerJump(k: Float) = DimensionBuilders.DpProp.Builder(0f).setDynamicValue(
        DynamicFloat.animate(0f, -8.4f * k, blow(timing(95, 810), timing(95, 0), first = timing(95, 0)))
    ).build()

    /** The sparks show for the first fifth of each second, after the hit, and are moved out of sight the rest of it. */
    private fun sparksFlash(k: Float): DimensionBuilders.DpProp {
        val second = DynamicFloat.animate(
            0f, 1f,
            AnimationParameterBuilders.AnimationSpec.Builder()
                .setAnimationParameters(timing(1000, 0))
                .setRepeatable(AnimationParameterBuilders.Repeatable.INFINITE_REPEATABLE_WITH_RESTART)
                .build(),
        )
        return DimensionBuilders.DpProp.Builder(OUT_OF_SIGHT * k).setDynamicValue(
            // an animation starts slowly by default: it has only come this far a fifth of the way through
            DynamicFloat.onCondition(second.lt(0.134f)).use(DynamicFloat.constant(0f)).elseUse(DynamicFloat.constant(OUT_OF_SIGHT * k))
        ).build()
    }

    /** There and back for ever, with its own speed and wait each way. */
    private fun blow(
        forward: AnimationParameterBuilders.AnimationParameters,
        back: AnimationParameterBuilders.AnimationParameters,
        first: AnimationParameterBuilders.AnimationParameters = forward,
    ) = AnimationParameterBuilders.AnimationSpec.Builder()
        .setAnimationParameters(first)
        .setRepeatable(
            AnimationParameterBuilders.Repeatable.Builder()
                .setRepeatMode(AnimationParameterBuilders.REPEAT_MODE_REVERSE)
                .setForwardRepeatOverride(forward)
                .setReverseRepeatOverride(back)
                .build()
        )
        .build()

    private fun timing(millis: Long, wait: Long) =
        AnimationParameterBuilders.AnimationParameters.Builder()
            .setDurationMillis(millis)
            .setDelayMillis(wait)
            .build()

    /** The creature hops when it needs you and dances on your turn: sways, bobs and tilts. */
    private fun creatureMove(mood: String, k: Float) = when (mood) {
        "needs" -> moves { setTranslationY(dpMove(0f, -28 * k, 330)) }
        "done" -> moves {
            setTranslationX(dpMove(-7 * k, 7 * k, 440))
            setTranslationY(dpMove(0f, -7 * k, 220))
            setRotation(degreesMove(-6f, 6f, 440))
        }
        else -> null
    }

    /** The icons move instead of changing frames: the bubble bounces, the spinner turns, the Zs float, the sparkles pulse. */
    private fun iconMove(mood: String, k: Float) = when (mood) {
        "needs" -> moves { setTranslationY(dpMove(0f, -5 * k, 400)) }
        "working" -> moves { setRotation(degreesMove(0f, 360f, 640, back = false)) }
        "sleeping" -> moves { setTranslationY(dpMove(0f, -5 * k, 1000)) }
        "done" -> moves {
            setScaleX(scaleMove(0.85f, 1.1f, 450))
            setScaleY(scaleMove(0.85f, 1.1f, 450))
        }
        else -> null
    }

    private fun moves(transform: ModifiersBuilders.Transformation.Builder.() -> Unit) =
        ModifiersBuilders.Modifiers.Builder()
            .setTransformation(ModifiersBuilders.Transformation.Builder().apply(transform).build())
            .build()

    /** From [from] to [to] and back (or round again), forever; a watch that can't animate keeps it still. */
    private fun swing(from: Float, to: Float, millis: Long, back: Boolean) = DynamicFloat.animate(
        from, to,
        AnimationParameterBuilders.AnimationSpec.Builder()
            .setAnimationParameters(AnimationParameterBuilders.AnimationParameters.Builder().setDurationMillis(millis).build())
            .setRepeatable(
                if (back) AnimationParameterBuilders.Repeatable.INFINITE_REPEATABLE_WITH_REVERSE
                else AnimationParameterBuilders.Repeatable.INFINITE_REPEATABLE_WITH_RESTART
            )
            .build(),
    )

    private fun dpMove(from: Float, to: Float, millis: Long) =
        DimensionBuilders.DpProp.Builder(0f).setDynamicValue(swing(from, to, millis, back = true)).build()

    private fun degreesMove(from: Float, to: Float, millis: Long, back: Boolean = true) =
        DimensionBuilders.DegreesProp.Builder(0f).setDynamicValue(swing(from, to, millis, back)).build()

    private fun scaleMove(from: Float, to: Float, millis: Long) =
        TypeBuilders.FloatProp.Builder(1f).setDynamicValue(swing(from, to, millis, back = true)).build()

    /** A ring round the edge in the state's colour, dashed when out of date. */
    private fun ring(mood: String, k: Float): LayoutElementBuilders.LayoutElement {
        val colour = argb(RINGS.getValue(mood))
        val arc = LayoutElementBuilders.Arc.Builder().setAnchorAngle(degrees(0f))
        if (mood == "stale") {
            repeat(30) {
                arc.addContent(LayoutElementBuilders.ArcLine.Builder().setLength(degrees(6f)).setThickness(dp(6 * k)).setColor(colour).build())
                arc.addContent(LayoutElementBuilders.ArcSpacer.Builder().setLength(degrees(6f)).setThickness(dp(6 * k)).build())
            }
        } else {
            arc.addContent(LayoutElementBuilders.ArcLine.Builder().setLength(degrees(360f)).setThickness(dp(6 * k)).setColor(colour).build())
        }
        return LayoutElementBuilders.Box.Builder()
            .setWidth(expand()).setHeight(expand())
            .setModifiers(ModifiersBuilders.Modifiers.Builder().setPadding(ModifiersBuilders.Padding.Builder().setAll(dp(6 * k)).build()).build())
            .addContent(arc.build())
            .build()
    }

    /**
     * The time, kept current by the watch itself: the hours and minutes since this entry's local
     * midnight. (ProtoLayout 1.2 keeps its time-of-day helper private.) The tile is fetched again
     * every 15 minutes, which picks up a change to or from summer time.
     */
    private fun clock(t: Long, k: Float): LayoutElementBuilders.LayoutElement {
        val zone = ZoneId.systemDefault()
        val midnight = Instant.ofEpochMilli(t).atZone(zone).toLocalDate().atStartOfDay(zone).toInstant()
        val sinceMidnight = DynamicInstant.withSecondsPrecision(midnight).durationUntil(DynamicInstant.platformTimeWithSecondsPrecision())
        val value = twoDigits(sinceMidnight.hoursPart).concat(DynamicString.constant(":")).concat(twoDigits(sinceMidnight.minutesPart))
        val shown = TypeBuilders.StringProp.Builder(HH_MM.format(Instant.ofEpochMilli(t).atZone(zone))).setDynamicValue(value).build()
        return text(shown, 40 * k, WHITE, longest = "00:00", bold = true)
    }

    private fun twoDigits(n: DynamicInt32) =
        DynamicString.onCondition(n.lt(10)).use(DynamicString.constant("0").concat(n.format())).elseUse(n.format())

    private fun detail(state: ClaudeState?, k: Float) = when {
        state == null || state.state == "sleeping" -> text(fixed("No sessions running"), 24 * k, WHITE)
        state.state == "stale" -> text(ago(state.received, "Last update ", " min ago", "Last update just now"), 24 * k, WHITE, "Last update 9999 min ago")
        else -> text(fixed(state.named), 24 * k, WHITE)
    }

    /** How long the state has lasted, or the count per state when there are several sessions. */
    private fun sinceOrCounts(saved: ClaudeState?, state: ClaudeState?, k: Float): LayoutElementBuilders.LayoutElement = when {
        saved == null || state == null -> spacer(0f, 0f)
        state.state == "sleeping" -> text(fixed("Last active ${HH_MM.format(Instant.ofEpochSecond(state.received).atZone(ZoneId.systemDefault()))}"), 22 * k, GREY)
        state.state == "stale" -> text(fixed("Was: ${saved.word}"), 22 * k, GREY)
        state.needs + state.working + state.done > 1 -> counts(state, k)
        else -> {
            val (before, after, fresh) = SINCE.getValue(state.state)
            text(ago(state.since, before, after, fresh), 22 * k, GREY, "${before}9999$after")
        }
    }

    private fun counts(state: ClaudeState, k: Float): LayoutElementBuilders.LayoutElement {
        val row = LayoutElementBuilders.Row.Builder()
        state.tally
            .forEachIndexed { i, (mood, n, label) ->
                if (i > 0) row.addContent(spacer(14 * k, 0f))
                row.addContent(
                    LayoutElementBuilders.Box.Builder().setWidth(dp(10 * k)).setHeight(dp(10 * k))
                        .setModifiers(ModifiersBuilders.Modifiers.Builder().setBackground(ModifiersBuilders.Background.Builder().setColor(argb(COLOURS[mood] ?: COLOURS.getValue("idle"))).build()).build())
                        .build()
                )
                row.addContent(spacer(6 * k, 0f))
                row.addContent(text(fixed("$n $label"), 20 * k, LIGHT))
            }
        return row.build()
    }

    /** "waiting 3 min", counted up by the watch itself from [since] (seconds). */
    private fun ago(since: Long, before: String, after: String, fresh: String): TypeBuilders.StringProp {
        val minutes = DynamicInstant.withSecondsPrecision(Instant.ofEpochSecond(since))
            .durationUntil(DynamicInstant.platformTimeWithSecondsPrecision())
            .toIntMinutes()
        val now = (System.currentTimeMillis() / 1000 - since) / 60
        return TypeBuilders.StringProp.Builder(if (now < 1) fresh else "$before$now$after")
            .setDynamicValue(
                DynamicString.onCondition(minutes.lt(1)).use(DynamicString.constant(fresh))
                    .elseUse(DynamicString.constant(before).concat(minutes.format()).concat(DynamicString.constant(after)))
            )
            .build()
    }

    private fun image(id: String, width: Float, height: Float, moves: ModifiersBuilders.Modifiers?) =
        LayoutElementBuilders.Image.Builder()
            .setResourceId(id)
            .setWidth(dp(width)).setHeight(dp(height))
            .apply { if (moves != null) setModifiers(moves) }
            .build()

    /** A box of the given size with [content] centred in it, so each row sits where the design puts it. */
    private fun line(content: LayoutElementBuilders.LayoutElement, width: Float, height: Float) =
        LayoutElementBuilders.Box.Builder().setWidth(dp(width)).setHeight(dp(height)).addContent(content).build()

    private fun spacer(width: Float, height: Float) =
        LayoutElementBuilders.Spacer.Builder().setWidth(dp(width)).setHeight(dp(height)).build()

    private fun fixed(value: String) = TypeBuilders.StringProp.Builder(value).build()

    private fun text(value: TypeBuilders.StringProp, size: Float, colour: Int, longest: String? = null, bold: Boolean = false) =
        LayoutElementBuilders.Text.Builder()
            .setText(value)
            // a text that changes by itself needs room for its longest form
            .apply { if (longest != null) setLayoutConstraintsForDynamicText(TypeBuilders.StringLayoutConstraint.Builder(longest).build()) }
            .setMaxLines(1)
            .setOverflow(LayoutElementBuilders.TEXT_OVERFLOW_ELLIPSIZE_END)
            .setFontStyle(
                LayoutElementBuilders.FontStyle.Builder()
                    .setSize(sp(size))
                    .setColor(argb(colour))
                    .setWeight(if (bold) LayoutElementBuilders.FONT_WEIGHT_BOLD else LayoutElementBuilders.FONT_WEIGHT_NORMAL)
                    .build()
            )
            .build()

    private fun openApp(id: String) = ModifiersBuilders.Clickable.Builder()
        .setId(id)
        .setOnClick(
            ActionBuilders.LaunchAction.Builder()
                .setAndroidActivity(
                    ActionBuilders.AndroidActivity.Builder()
                        .setPackageName(packageName)
                        .setClassName(MainActivity::class.java.name)
                        .build()
                )
                .build()
        )
        .build()

    /** The next switches between day (from 06:00) and night (from 18:00), over the coming two days. */
    private fun dayNightChanges(now: Long): List<Long> {
        val zone = ZoneId.systemDefault()
        val today = Instant.ofEpochMilli(now).atZone(zone).toLocalDate()
        return (0L..1L).flatMap { days ->
            listOf(ClaudeState.DAY_STARTS, ClaudeState.NIGHT_STARTS).map { hour -> today.plusDays(days).atTime(hour, 0).atZone(zone).toInstant().toEpochMilli() }
        }
    }

    private companion object {
        const val RESOURCES_VERSION = "6" // raise when the images change, or the watch keeps the old ones
        const val WHITE = 0xFFF5F6F8.toInt()
        const val GREY = 0xFFB9BEC8.toInt()
        const val LIGHT = 0xFFD5D8DF.toInt()
        const val HAMMER_TOP = -78f // degrees, raised
        const val OUT_OF_SIGHT = 2000f
        val HH_MM: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm")
        val COLOURS = ClaudeState.COLOURS
        val RINGS = mapOf(
            "sleeping" to 0xFF2E2C4A.toInt(), "working" to 0xFF5BC2FF.toInt(), "needs" to 0xFFFFC233.toInt(),
            "done" to 0xFF3EE6A0.toInt(), "stale" to 0xFF5A5F69.toInt(),
        )
        /** Before and after the minutes, and what to say in the first minute. */
        val SINCE = mapOf(
            "working" to Triple("for ", " min", "just started"),
            "needs" to Triple("waiting ", " min", "just now"),
            "done" to Triple("finished ", " min ago", "finished just now"),
        )
        val IMAGES = mapOf(
            "sleep_top_day" to R.drawable.sleep_top_day, "sleep_top_night" to R.drawable.sleep_top_night,
            "sleep_low" to R.drawable.sleep_low,
            "working" to R.drawable.creature_working, "work_arm" to R.drawable.work_arm,
            "anvil" to R.drawable.anvil, "sparks" to R.drawable.sparks,
            "needs" to R.drawable.creature_needs, "done" to R.drawable.creature_done, "stale" to R.drawable.creature_stale,
            "scene_sleeping" to R.drawable.scene_sleeping, "scene_sleeping_day" to R.drawable.scene_sleeping_day,
            "scene_working" to R.drawable.scene_working, "scene_working_day" to R.drawable.scene_working_day,
            "scene_needs" to R.drawable.scene_needs, "scene_needs_day" to R.drawable.scene_needs_day,
            "scene_done" to R.drawable.scene_done, "scene_done_day" to R.drawable.scene_done_day,
            "scene_stale" to R.drawable.scene_stale, "scene_stale_day" to R.drawable.scene_stale_day,
            "icon_sleeping" to R.drawable.icon_sleeping, "icon_working" to R.drawable.icon_working,
            "icon_needs" to R.drawable.icon_needs, "icon_done" to R.drawable.icon_done, "icon_stale" to R.drawable.icon_stale,
        )
    }
}
