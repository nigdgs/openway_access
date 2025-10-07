package com.example.openway.ble

import com.example.openway.BuildConfig
import java.util.UUID

object BleConfig {
    val SERVICE_UUID: UUID = UUID.fromString(BuildConfig.SERVICE_UUID)
    val CHAR_UUID: UUID = UUID.fromString(BuildConfig.CHAR_UUID)
    const val NAME_HINT: String = BuildConfig.BLE_NAME_HINT
}

