package com.example.openway.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenStore(context: Context) {
    private val prefs = runCatching {
        val key = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            context, "device_token_secure", key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }.getOrElse { context.getSharedPreferences("device_token_fallback", Context.MODE_PRIVATE) }

    fun getToken(): String? = prefs.getString("device_token", null)
    fun setToken(token: String) { prefs.edit().putString("device_token", token.trim()).apply() }
    fun clear() { prefs.edit().remove("device_token").apply() }

    fun preview(): String {
        val t = getToken().orEmpty()
        return if (t.length > 8) t.take(4) + "…" + t.takeLast(4) else t
    }
}