package com.example.openway



import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.navigation.NavController


@Composable
fun LoginScreen(navController: NavController) {
    // Состояния логина и пароля
    var login by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    // Состояние показывать ли пароль в виде текста или точками
    var flagPassword by rememberSaveable { mutableStateOf(false) }

    // Основной котейнер
    Box(
        modifier = Modifier
            .fillMaxSize() // растягиваем на весь экран
            .background(colorResource(R.color.dark_theme)) // цвет фона
            .padding(16.dp) // отступы
    ) {
        // Колонки
        Column(
            modifier = Modifier
                .align(Alignment.Center) // выравневание колонок по цетру
                .fillMaxWidth(), // растягивание колонок на всю ширину
            horizontalAlignment = Alignment.CenterHorizontally // сожержимое колонки по центру
        ) {
            Text(
                text = "Добро пожаловать",
                fontSize = 22.sp,
                color = Color.White
            )

            Spacer(Modifier.height(20.dp)) // отступ

            // Поле логина
            OutlinedTextField(
                value = login, // текущее значение поля
                onValueChange = { login = it},
                placeholder = { // подсказка
                    Text(
                        text = "Введите логин",
                        color = Color.Gray
                    )
                },

                singleLine = true, // поля в одну строку

                keyboardOptions = KeyboardOptions( // натсройка клавиатуры
                    keyboardType = KeyboardType.Text, // обычная клавиатура
                    imeAction = ImeAction.Next        // кнопка "Далее" на клавиатуре
                ),

                textStyle = LocalTextStyle.current.copy( // стиль текста ввода
                    color = Color.White, // цвет
                    fontSize = 16.sp // рахмер
                ),

                leadingIcon = {
                    Icon( // иконка пользователя
                        painter = painterResource(R.drawable.person),
                        contentDescription = "Логин",
                        modifier = Modifier.size(25.dp),
                        tint = Color.Gray
                    )
                },

                modifier = Modifier
                    .fillMaxWidth() // растягиваем на все ширину
                    .padding(horizontal = 10.dp, vertical = 2.dp),
                shape = RoundedCornerShape(13.dp), // cкругление

                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.White, // активный цвет контура
                    unfocusedBorderColor = Color.Gray, // не активный цвет контура
                )
            )

            Spacer(Modifier.height(12.dp)) // отступ

            // поле пароля
            OutlinedTextField(
                value = password, // текущее значение пароля
                onValueChange = { password = it },
                placeholder = { // подсказка
                    Text(
                        text = "Введите пароль",
                        color = Color.Gray
                    )
                },
                singleLine = true,

                // Настройка отображения текста
                visualTransformation = if (flagPassword) {
                    VisualTransformation.None
                } else {
                    PasswordVisualTransformation()
                },

                //
                keyboardOptions = KeyboardOptions ( // натсройка клавиатуры
                    keyboardType = KeyboardType.Password, // клавиатура для пароля
                    imeAction = ImeAction.Done // кнопка "Готово" на клавиатуре
                ),

                textStyle = LocalTextStyle.current.copy( // стиль текста ввода
                    color = Color.White, // цвет
                    fontSize = 16.sp // рахмер
                ),

                leadingIcon = {
                    Icon( // иконка замка
                        painter = painterResource(R.drawable.lock),
                        contentDescription = "Логин",
                        modifier = Modifier.size(25.dp),
                        tint = Color.Gray
                    )
                },

                // Иконка справа - "Глаз", чтобы покказывать/скрывать пароль
                trailingIcon = {
                    IconButton( onClick = { flagPassword = !flagPassword} ) {
                        Icon( // иконка глаза
                            painter = painterResource(
                                id = if (flagPassword) R.drawable.crossed_eye
                                else R.drawable.eye
                            ),
                            contentDescription = "Показать/скрыть пароль",
                            tint = colorResource(R.color.icons)
                        )
                    }
                },

                modifier = Modifier
                    .fillMaxWidth() // растягиваем на все ширину
                    .padding(horizontal = 10.dp, vertical = 2.dp),
                shape = RoundedCornerShape(13.dp), // cкругление

                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.White, // активный цвет контура
                    unfocusedBorderColor = Color.Gray, // не активный цвет контура
                )
            )

            Spacer(Modifier.height(20.dp))

            Button(
                onClick = {
                    navController.navigate("mainScreen") // проверка что навигация работает
                },
                modifier = Modifier
                    .fillMaxWidth() // кнопка на всю ширину
                    .padding(horizontal = 10.dp, vertical = 5.dp)
                    .height(48.dp), // высота кнопки
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = Color.Black
                )
            ) {
                Text("Войти", fontSize = 16.sp) // надпись на кнопке
            }
        }
    }
}
