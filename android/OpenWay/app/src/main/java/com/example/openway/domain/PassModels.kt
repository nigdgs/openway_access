package com.example.openway.domain

import org.json.JSONObject

data class PassResult(val decision: String, val reason: String) {
    val allowed get() = decision.equals("ALLOW", ignoreCase = true)
    companion object {
        fun parse(json: String): PassResult {
            val o = JSONObject(json)
            return PassResult(
                decision = o.optString("decision", "DENY"),
                reason = o.optString("reason", "UNKNOWN"),
            )
        }
    }
}
