package com.example.openway

import android.content.Context

data class User ( // польлзователь
    val name: String, // имя
    val surname: String, // фамилия
    val position: String, // должность
    val login: String // логин
)


// Функция сохранения данных пользователя в постоянное хранилище
fun SaveUser(context: Context, user: User) {
    // Получаем доступ к хранилищу
    val storage = context.getSharedPreferences("user_data", Context.MODE_PRIVATE)

    with(storage.edit()) {
        putString("name", user.name) // сохраняем имя
        putString("surname", user.surname) // сохраняем имя
        putString("position", user.position) // сохраняем имя
        putString("login", user.login) // сохраняем имя
        apply()
    }
}


// Функция загрузки данных пользователя из постоянного хранилища
fun LoadUser (context: Context): User? {
    // Получаем доступ к хранилищу
    val storage = context.getSharedPreferences("user_data", Context.MODE_PRIVATE)

    val name = storage.getString("name", null) // загружаем имя
    val surname = storage.getString("surname", null) // загружаем фамилию
    val position = storage.getString("position", null)     // Загружаем должность
    val login = storage.getString("login", null)     // Загружаем должность

    // создаем объект User
    if (name != null && surname != null && position != null && login != null) {
        return User(name, surname, position, login)
    }
    else {
        return null
    }
}


// Функция очищения данных пользователя при выходе из аккаунта
fun ClearUser(context: Context) {
    // Получаем доступ к хранилищу
    val storage = context.getSharedPreferences("user_data", Context.MODE_PRIVATE)

    storage.edit().clear().apply() //
}