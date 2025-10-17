package com.example.openway.api

import retrofit2.http.Body
import retrofit2.http.POST

data class LoginRequest(val username: String, val password: String)
data class TokenResponse(val token: String)

interface AuthApi {
    @POST("/api/v1/auth/token")
    suspend fun login(@Body body: LoginRequest): TokenResponse
}


