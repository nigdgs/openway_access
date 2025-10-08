package com.example.openway.ble

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner

class BleClient(private val activity: ComponentActivity) {

    private val ctx: Context get() = activity
    private val bluetoothManager = ctx.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val adapter: BluetoothAdapter? get() = bluetoothManager.adapter
    private val scanner: BluetoothLeScanner? get() = adapter?.bluetoothLeScanner

    @Volatile private var isScanning = false
    private var scanCallback: ScanCallback? = null
    private var gatt: BluetoothGatt? = null
    private val main = Handler(Looper.getMainLooper())

    // --- permissions & enable BT ---
    private val permissionLauncher: ActivityResultLauncher<Array<String>> =
        activity.registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { res: Map<String, Boolean> ->
            if (res.values.all { it }) startFlow()
            else toast("Нужны разрешения для BLE")
        }

    private val btEnableLauncher: ActivityResultLauncher<Intent> =
        activity.registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { _ ->
            if (adapter?.isEnabled == true) startFlow()
            else toast("Включи Bluetooth и повтори")
        }

    init {
        // Авто-очистка ресурсов, если Activity уничтожается
        activity.lifecycle.addObserver(object : DefaultLifecycleObserver {
            override fun onDestroy(owner: LifecycleOwner) {
                cleanup()
            }
        })
    }

    @SuppressLint("MissingPermission")
    private fun cleanup() {
        stopScan()
        try { gatt?.disconnect() } catch (_: Exception) {}
        try { gatt?.close() } catch (_: Exception) {}
        gatt = null
        main.removeCallbacksAndMessages(null)
    }

    private var pendingToken: String? = null

    fun sendToken(token: String) {
        pendingToken = token
        ensurePrerequisites()
    }

    private fun ensurePrerequisites() {
        if (adapter == null) { toast("На устройстве нет Bluetooth"); return }
        if (adapter?.isEnabled != true) {
            btEnableLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            return
        }
        val needs = neededPermissions()
        val missing = needs.filter {
            ContextCompat.checkSelfPermission(ctx, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            permissionLauncher.launch(needs)
            return
        }
        startFlow()
    }

    private fun neededPermissions(): Array<String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
            arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
        else
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)

    private fun startFlow() {
        val token = pendingToken ?: return
        startScan(
            onFound = { device ->
                stopScan()
                connectAndWrite(device, token)
            },
            onTimeout = {
                toast("ESP32 не найден. Проверь рекламу и близость")
            }
        )
    }

    // --- scan ---
    @SuppressLint("MissingPermission")
    private fun startScan(onFound: (BluetoothDevice) -> Unit, onTimeout: () -> Unit) {
        if (isScanning) return
        stopScan()
        isScanning = true

        val filters = mutableListOf<ScanFilter>()
        filters += ScanFilter.Builder().setServiceUuid(ParcelUuid(BleConfig.SERVICE_UUID)).build()
        if (BleConfig.NAME_HINT.isNotBlank()) {
            filters += ScanFilter.Builder().setDeviceName(BleConfig.NAME_HINT).build()
        }
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        val cb = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                result.device?.let { onFound(it) }
            }
        }
        scanCallback = cb
        scanner?.startScan(filters, settings, cb)

        main.postDelayed({
            if (isScanning) {
                stopScan()
                onTimeout()
            }
        }, 10_000)
    }

    @SuppressLint("MissingPermission")
    private fun stopScan() {
        try { scanCallback?.let { scanner?.stopScan(it) } } catch (_: Exception) {}
        scanCallback = null
        isScanning = false
    }

    // --- connect & write ---
    @SuppressLint("MissingPermission")
    private fun connectAndWrite(device: BluetoothDevice, token: String) {
        gatt?.close()
        gatt = device.connectGatt(ctx, false, object : BluetoothGattCallback() {
            override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    gatt.discoverServices()
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    gatt.close()
                }
            }

            override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    toast("Ошибка discover: $status"); return
                }
                val svc = gatt.getService(BleConfig.SERVICE_UUID)
                val ch = svc?.getCharacteristic(BleConfig.CHAR_UUID)
                if (ch == null) { toast("Characteristic не найдена"); return }

                val value = token.toByteArray(Charsets.UTF_8)
                val props = ch.properties
                ch.writeType = if (props and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE != 0)
                    BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
                else
                    BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT

                val ok = if (Build.VERSION.SDK_INT >= 33) {
                    gatt.writeCharacteristic(ch, value, ch.writeType) == BluetoothStatusCodes.SUCCESS
                } else {
                    ch.value = value
                    gatt.writeCharacteristic(ch)
                }
                if (!ok) toast("Не удалось начать запись")
            }

            override fun onCharacteristicWrite(
                gatt: BluetoothGatt,
                characteristic: BluetoothGattCharacteristic,
                status: Int
            ) {
                if (status == BluetoothGatt.GATT_SUCCESS) {
                    toast("Токен отправлен по BLE")
                } else {
                    toast("Ошибка записи: $status")
                }
                // мягко закрываем соединение
                main.postDelayed({ gatt.disconnect() }, 300)
            }
        }, BluetoothDevice.TRANSPORT_LE)
    }

    private fun toast(msg: String) =
        Toast.makeText(ctx, msg, Toast.LENGTH_SHORT).show()
}

