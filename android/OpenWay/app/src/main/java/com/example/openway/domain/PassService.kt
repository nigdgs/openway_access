package com.example.openway.domain

import android.content.Context
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import com.example.openway.data.SettingsStore
import com.example.openway.data.TokenStore
import com.example.openway.net.EspClient
import com.example.openway.net.BackendClient

/**
 * PassService — тонкая обёртка, которую можно вызывать из существующего UI.
 * Никаких UI-правок делать не нужно: UI просто дергает эти методы.
 */
class PassService(private val appContext: Context) {
    private val settings = SettingsStore(appContext)
    private val tokens = TokenStore(appContext)

    val espIpFlow: Flow<String> get() = settings.espIp
    val gateIdFlow: Flow<String> get() = settings.gateId

    suspend fun setEspIp(ip: String) = settings.setEspIp(ip)
    suspend fun setGateId(gate: String) = settings.setGateId(gate)

    fun setDeviceToken(token: String) = tokens.setToken(token)
    fun clearDeviceToken() = tokens.clear()
    fun tokenPreview(): String = tokens.preview()

    /**
     * Выполняет проход: берёт актуальные espIp/gateId из DataStore и token из защищённого хранилища.
     * Если directBackendBase != null — вызываем backend напрямую (для эмулятора).
     * Пример: directBackendBase = "http://10.0.2.2:8001"
     * Возвращает Result<PassResult> (без UI).
     */
    suspend fun pass(debug: Boolean = false, directBackendBase: String? = null): Result<PassResult> {
        val token = tokens.getToken().orEmpty()
        if (token.isBlank()) return Result.success(PassResult("DENY", "TOKEN_INVALID"))
        val espIp = espIpFlow.first()
        val gateId = gateIdFlow.first()
        return if (directBackendBase != null) {
            BackendClient.verify(debug, directBackendBase, gateId, token).mapCatching { PassResult.parse(it) }
        } else {
            EspClient.enter(debug, espIp, token, gateId).mapCatching { PassResult.parse(it) }
        }
    }
}
