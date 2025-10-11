package com.example.openway.ble

import java.util.*

object BleConfig {
    // === ВАШИ ДАННЫЕ ===
    const val DEVICE_MAC: String = "00:4B:12:F1:58:2E"

    // UUID’ы должны совпадать с прошивкой ESP32
    val SERVICE_UUID: UUID = UUID.fromString("4fafc201-1fb5-459e-8fcc-c5c9c331914b")
    val CHAR_UUID: UUID    = UUID.fromString("beb5483e-36e1-4688-b7f5-ea07361b26a8")

    // таймауты
    const val CONNECT_TIMEOUT_MS = 10_000L
    const val DISCOVER_TIMEOUT_MS = 7_000L
    const val WRITE_TIMEOUT_MS = 5_000L
}