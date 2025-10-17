package com.example.openway.api

import retrofit2.http.Body
import retrofit2.http.Headers
import retrofit2.http.POST

data class VerifyRequest(val gate_id: String, val token: String)
data class VerifyResponse(val decision: String, val reason: String, val duration_ms: Int? = null)

interface VerifyApi {
    @Headers("Content-Type: application/json")
    @POST("/api/v1/access/verify")
    suspend fun verify(@Body body: VerifyRequest): VerifyResponse
}


