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
}

