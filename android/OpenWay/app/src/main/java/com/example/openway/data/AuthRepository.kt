package com.example.openway.data

import android.content.Context
import com.example.openway.api.AuthApi
import com.example.openway.api.LoginRequest
import com.example.openway.util.TokenProvider

class AuthRepository(private val api: AuthApi) {
    suspend fun login(context: Context, username: String, password: String): Result<String> =
        runCatching {
            val resp = api.login(LoginRequest(username, password))
            TokenProvider.saveToken(context, resp.token)
            resp.token
        }
}


