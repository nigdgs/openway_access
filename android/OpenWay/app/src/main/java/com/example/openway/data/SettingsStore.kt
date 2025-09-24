package com.example.openway.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "controller_settings")

object SettingsKeys {
    val ESP_IP = stringPreferencesKey("esp_ip")
    val GATE_ID = stringPreferencesKey("gate_id")
}

class SettingsStore(private val context: Context) {
    val espIp: Flow<String> = context.dataStore.data.map { it[SettingsKeys.ESP_IP] ?: "192.168.1.50" }
    val gateId: Flow<String> = context.dataStore.data.map { it[SettingsKeys.GATE_ID] ?: "gate-01" }

    suspend fun setEspIp(value: String) = context.dataStore.edit { it[SettingsKeys.ESP_IP] = value.trim() }
    suspend fun setGateId(value: String) = context.dataStore.edit { it[SettingsKeys.GATE_ID] = value.trim().lowercase() }
}
