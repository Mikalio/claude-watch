package io.github.mikalio.wristling

import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Opens a push the relay sealed, so that only the relay and this watch can read it, not Firebase: AES-256-GCM,
 * in base64, as a 12-byte nonce and then the ciphertext with its tag. A push that was changed or sealed with
 * another key throws.
 */
object Sealed {
    fun open(sealed: String, key: String): String {
        val bytes = Base64.getDecoder().decode(sealed)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(Base64.getDecoder().decode(key), "AES"), GCMParameterSpec(128, bytes, 0, 12))
        return String(cipher.doFinal(bytes, 12, bytes.size - 12), Charsets.UTF_8)
    }
}
