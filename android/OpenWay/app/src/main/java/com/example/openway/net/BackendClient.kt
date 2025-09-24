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

object BackendClient {
    private val json = "application/json; charset=utf-8".toMediaType()

    private fun client(debug: Boolean) = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.SECONDS)
        .retryOnConnectionFailure(false)
        .apply {
            if (debug) addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
        }.build()

    suspend fun verify(
        debug: Boolean,
        baseUrl: String,      // например, "http://10.0.2.2:8001"
        gateId: String,
        token: String
    ): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val c = client(debug)
            val url = "${baseUrl.trimEnd('/')}/api/v1/access/verify"
            val body = JSONObject()
                .put("gate_id", gateId)
                .put("token", token)
                .toString()
                .toRequestBody(json)

            val req = Request.Builder()
                .url(url)
                .addHeader("Content-Type", "application/json")
                .post(body)
                .build()

            c.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) error("HTTP ${resp.code}")
                resp.body?.string() ?: error("Empty body")
            }
        }
    }
}
