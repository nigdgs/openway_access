package com.example.openway.data

import com.example.openway.api.VerifyApi
import com.example.openway.api.VerifyRequest

class VerifyRepository(private val api: VerifyApi) {
    suspend fun verify(gateId: String, token: String) =
        runCatching { api.verify(VerifyRequest(gate_id = gateId, token = token)) }
}


