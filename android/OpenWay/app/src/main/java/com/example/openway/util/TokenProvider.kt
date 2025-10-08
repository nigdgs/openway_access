package com.example.openway.util

import android.content.Context
import com.example.openway.BuildConfig

object TokenProvider {
    private const val PREFS = "openway_prefs"
    private const val KEY = "user_token"

    fun getToken(context: Context): String {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return sp.getString(KEY, null) ?: BuildConfig.DEMO_DRF_TOKEN
    }

    fun saveToken(context: Context, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, token).apply()
    }
}

