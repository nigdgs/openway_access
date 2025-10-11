package com.example.openway.ble

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.*
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.ActivityCompat
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.atomic.AtomicBoolean

class BleClient(private val context: Context) {

    private val TAG = "BleClient"
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // текущее соединение
    private var gatt: BluetoothGatt? = null

    // синхронизация, чтобы не запускать две операции параллельно
    private val opMutex = Mutex()
    private val isClosed = AtomicBoolean(false)

    // ---- публичный API ------------------------------------------------------

    /**
     * Подключиться к устройству по MAC и отправить токен целиком как UTF-8.
     * Результат приходит в onResult(success, message).
     */
    fun sendToken(
        token: String,
        onResult: (Boolean, String) -> Unit = { _, _ -> }
    ) {
        scope.launch {
            val res = runCatching { sendTokenInternal(token) }
            withContext(Dispatchers.Main) {
                res.onSuccess { ok ->
                    onResult(ok, if (ok) "OK" else "Не удалось записать характеристику")
                }.onFailure { e ->
                    onResult(false, e.message ?: "Ошибка")
                }
            }
        }
    }

    /** Закрыть BLE (вызывайте из onDestroy Activity). */
    fun close() {
        if (isClosed.getAndSet(true)) return
        try { gatt?.disconnect() } catch (_: Throwable) {}
        try { gatt?.close() } catch (_: Throwable) {}
        gatt = null
        scope.cancel()
    }

    // ---- основная логика ----------------------------------------------------

    @SuppressLint("MissingPermission")
    private suspend fun sendTokenInternal(token: String): Boolean = opMutex.withLock {
        require(hasBlePermissions()) { "Нет BLE-разрешений (CONNECT/SCAN или Location)" }
        require(token.isNotEmpty()) { "Пустой токен" }

        val bt = (context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
            ?: throw IllegalStateException("BluetoothAdapter = null")

        val device = try {
            bt.getRemoteDevice(BleConfig.DEVICE_MAC)
        } catch (e: IllegalArgumentException) {
            throw IllegalStateException("Неверный MAC ${BleConfig.DEVICE_MAC}")
        }

        // единый колбэк с деферами
        val state = CallbackState()

        // подключение (лучше дергать на главном потоке)
        val g = withContext(Dispatchers.Main) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                device.connectGatt(context, false, state.cb, BluetoothDevice.TRANSPORT_LE)
            } else {
                @Suppress("DEPRECATION")
                device.connectGatt(context, false, state.cb)
            }
        }
        gatt = g

        // ждём подключения
        val connected = withTimeoutOrNull(BleConfig.CONNECT_TIMEOUT_MS) { state.connected.await() } ?: false
        if (!connected) {
            Log.w(TAG, "connect timeout/fail")
            cleanupGatt()
            return@withLock false
        }
        Log.d(TAG, "connected")

        // discovery
        if (!g.discoverServices()) {
            Log.w(TAG, "discoverServices() returned false")
            cleanupGatt(); return@withLock false
        }
        val discovered = withTimeoutOrNull(BleConfig.DISCOVER_TIMEOUT_MS) { state.servicesDiscovered.await() } ?: false
        if (!discovered) {
            Log.w(TAG, "services discover timeout/fail")
            cleanupGatt(); return@withLock false
        }
        Log.d(TAG, "services discovered")        // MTU (нужно > 43, чтобы влезли 40 байт + заголовок/запас)
        val mtuOk = if (g.requestMtu(100)) {
            withTimeoutOrNull(3000) { state.mtuChanged.await() } ?: false
        } else false
        Log.d(TAG, "mtuOk=$mtuOk (это нормально, если false — используем дефолт 23)")

        val service = g.getService(BleConfig.SERVICE_UUID)
            ?: run { Log.w(TAG, "service not found"); cleanupGatt(); return@withLock false }

        val ch = service.getCharacteristic(BleConfig.CHAR_UUID)
            ?: run { Log.w(TAG, "characteristic not found"); cleanupGatt(); return@withLock false }

        val mtu = state.lastMtu.coerceAtLeast(23)
        val maxPayload = mtu - 3
        val data = token.toByteArray(Charsets.UTF_8)
        if (data.size > maxPayload) {
            // без чанков запись не влезет, если MTU переговоры не прошли
            Log.w(TAG, "token=${data.size} bytes > maxPayload=$maxPayload (нет увеличенного MTU)")
            cleanupGatt(); return@withLock false
        }

        ch.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT // с подтверждением
        ch.value = data

        if (!g.writeCharacteristic(ch)) {
            Log.w(TAG, "writeCharacteristic() returned false")
            cleanupGatt(); return@withLock false
        }
        val writeOk = withTimeoutOrNull(BleConfig.WRITE_TIMEOUT_MS) { state.writeComplete.await() } ?: false
        Log.d(TAG, "writeOk=$writeOk")

        cleanupGatt()
        return@withLock writeOk
    }

    @SuppressLint("MissingPermission")
    private fun cleanupGatt() {
        try { gatt?.disconnect() } catch (_: Throwable) {}
        try { gatt?.close() } catch (_: Throwable) {}
        gatt = null
    }

    // ---- permissions --------------------------------------------------------

    private fun hasBlePermissions(): Boolean {
        val need = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            need += Manifest.permission.BLUETOOTH_CONNECT
            need += Manifest.permission.BLUETOOTH_SCAN
        } else {
            need += Manifest.permission.ACCESS_FINE_LOCATION
        }
        return need.all {
            ActivityCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    // ---- callback/state -----------------------------------------------------

    private inner class CallbackState {
        val connected = CompletableDeferred<Boolean>()
        val servicesDiscovered = CompletableDeferred<Boolean>()
        val mtuChanged = CompletableDeferred<Boolean>()
        val writeComplete = CompletableDeferred<Boolean>()
        var lastMtu: Int = 23

        val cb = object : BluetoothGattCallback() {
            override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                Log.d(TAG, "onConnectionStateChange s=$status state=$newState")
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    if (!connected.isCompleted) connected.complete(false)
                    return
                }
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    connected.complete(true)
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    if (!connected.isCompleted) connected.complete(false)
                }
            }

            override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                Log.d(TAG, "onServicesDiscovered s=$status")
                servicesDiscovered.complete(status == BluetoothGatt.GATT_SUCCESS)
            }
            override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
                Log.d(TAG, "onMtuChanged mtu=$mtu s=$status")
                if (status == BluetoothGatt.GATT_SUCCESS) {
                    lastMtu = mtu
                    mtuChanged.complete(true)
                } else {
                    mtuChanged.complete(false)
                }
            }            override fun onCharacteristicWrite(
                gatt: BluetoothGatt,
                characteristic: BluetoothGattCharacteristic,
                status: Int
            ) {
                Log.d(TAG, "onCharacteristicWrite s=$status")
                writeComplete.complete(status == BluetoothGatt.GATT_SUCCESS)
            }
        }
    }
}