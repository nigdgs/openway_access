package com.example.openway.util

import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException

/**
 * Maps common networking exceptions to human-readable Russian messages.
 * Keep messages short and action-focused for UI.
 */
fun humanizeNetworkError(t: Throwable): String =
    when (t) {
        is SocketTimeoutException -> "Таймаут ожидания ответа"
        is IOException -> "Нет соединения или сервер недоступен"
        is HttpException -> {
            val code = t.code()
            when {
                code == 400 -> "Неверный логин или пароль"
                code in 500..599 -> "Сервер недоступен (ошибка $code)"
                else -> "Ошибка HTTP $code"
            }
        }
        else -> t.message ?: "Неизвестная ошибка"
    }

