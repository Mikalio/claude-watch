package io.github.mikalio.wristling

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/** The same push and key as tests/test_web.py on the relay's side, so the two can't drift apart. */
class SealedTest {
    private val key = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
    private val sealed = "ZGVmZ2hpamtsbW5vMzmtEhidM7wEQDGNvwEZ327gdnjkBpYR0/OWarzRyivxmzngI3T9YY+AWkIoAjoCqK5TgmdmYbAB7TD2"

    @Test
    fun opensWhatTheRelaySealed() {
        assertEquals("""{"state":"needs","project":"Grocery offers"}""", Sealed.open(sealed, key))
    }

    @Test
    fun refusesAnotherKey() {
        val other = "HyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4="
        assertThrows(Exception::class.java) { Sealed.open(sealed, other) }
    }
}
