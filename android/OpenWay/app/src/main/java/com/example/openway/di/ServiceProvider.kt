package com.example.openway.di

import android.content.Context
import com.example.openway.domain.PassService

object ServiceProvider {
    @Volatile private var _pass: PassService? = null
    fun passService(appContext: Context): PassService =
        _pass ?: synchronized(this) {
            _pass ?: PassService(appContext.applicationContext).also { _pass = it }
        }
}
