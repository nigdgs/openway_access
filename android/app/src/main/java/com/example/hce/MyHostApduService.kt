
package com.example.hce

import android.nfc.cardemulation.HostApduService
import android.os.Bundle

class MyHostApduService : HostApduService() {
    private val SW_OK = byteArrayOf(0x90.toByte(), 0x00.toByte())
    private val SW_FAIL = byteArrayOf(0x6F.toByte(), 0x00.toByte())

    override fun processCommandApdu(apdu: ByteArray, extras: Bundle?): ByteArray {
        // Простейшее разделение: если это SELECT AID — отвечаем OK, иначе отдаем демо-токен + SW_OK
        return if (isSelectAid(apdu)) {
            SW_OK
        } else {
            val demo = "U-DEMO".toByteArray()
            demo + SW_OK
        }
    }

    override fun onDeactivated(reason: Int) {}

    private fun isSelectAid(apdu: ByteArray): Boolean {
        return apdu.size >= 5 && apdu[0] == 0x00.toByte() && apdu[1] == 0xA4.toByte()
    }
}
