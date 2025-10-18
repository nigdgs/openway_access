package com.example.openway.util

import android.content.Context
import com.example.openway.BuildConfig

object TokenProvider {
    private const val PREFS = "openway_prefs"
    private const val KEY = "user_token"

    fun getToken(context: Context): String {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = sp.getString(KEY, null)
        if (saved != null) return saved
        // Debug-only fallback; never ship demo token in release
        return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
    }

    fun saveToken(context: Context, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, token).apply()
    }

    /** Clears stored auth token. Used on logout. */
    fun clearToken(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(KEY).apply()
    }

    /** Check if user has a valid token stored. */
    fun hasToken(context: Context): Boolean = getToken(context).isNotBlank()
}

