package com.example.openway.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object EspClient {
    private val json = "application/json; charset=utf-8".toMediaType()

    private fun buildClient(debug: Boolean): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(2, TimeUnit.SECONDS)
            .readTimeout(3, TimeUnit.SECONDS)
            .retryOnConnectionFailure(false)
            .apply {
                if (debug) addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
            }.build()

    suspend fun enter(debug: Boolean, espIp: String, token: String, gateId: String): Result<String> =
        withContext(Dispatchers.IO) {
            runCatching {
                val client = buildClient(debug)
                val url = "http://$espIp/enter"
                val body = JSONObject().put("token", token).put("gate_id", gateId).toString()
                    .toRequestBody(json)
                fun exec(): String {
                    val req = Request.Builder().url(url)
                        .addHeader("Content-Type", "application/json")
                        .post(body).build()
                    client.newCall(req).execute().use { resp ->
                        if (!resp.isSuccessful) error("HTTP ${resp.code}")
                        resp.body?.string() ?: error("Empty body")
                    }
                }
                try { exec() } catch (_: Exception) { exec() } // 1 ретрай
            }
        }
}
