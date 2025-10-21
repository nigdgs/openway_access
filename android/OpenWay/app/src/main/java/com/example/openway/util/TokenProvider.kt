package com.example.openway.util

import android.content.Context

object TokenProvider {
    private const val PREFS = "openway_prefs"
    private const val KEY = "user_token"

    /**
     * Returns the stored auth token or empty string if none.
     * No debug fallback — empty means "not logged in".
     **/
    fun getToken(context: Context): String {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return sp.getString(KEY, "") ?: ""
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

    /** True only when a real token is stored in prefs. */
    fun hasToken(context: Context): Boolean {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = sp.getString(KEY, null)
        return !saved.isNullOrBlank()
    }
}

