package com.example.openway



import androidx.activity.ComponentActivity
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
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.core.view.WindowInsetsControllerCompat
import androidx.navigation.NavController
import kotlinx.coroutines.launch
import com.example.openway.api.ApiFactory
import com.example.openway.data.AuthRepository
import com.example.openway.util.humanizeNetworkError


@Composable
fun LoginScreen(navController: NavController) {

    val isLoginFocused = remember { mutableStateOf(false) }
    val isPasswordFocused = remember { mutableStateOf(false) }


    val context_Status_Bar = LocalContext.current
    val activity = context_Status_Bar as? ComponentActivity

    // Изменяем цвет иконок в статус-баре
    if (activity != null) {
        val window = activity.window
        WindowInsetsControllerCompat(window, window.decorView).apply {
            isAppearanceLightStatusBars = true
        }
    }

    // Состояния логина и пароля
    var login by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var errorText by rememberSaveable { mutableStateOf("") }
    var isLoading by rememberSaveable { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val focusManager = LocalFocusManager.current
    val authRepo = remember { AuthRepository(ApiFactory.authApi) }
    val canSubmit = !isLoading && login.isNotBlank() && password.isNotBlank()

    // Helper to avoid code duplication between button and IME Done
    fun submitLogin() {
        if (!canSubmit) return
        errorText = ""
        keyboardController?.hide()
        scope.launch {
            isLoading = true
            try {
                val res = authRepo.login(context, login, password)
                res.onSuccess {
                    navController.navigate("mainScreen")
                }.onFailure { e ->
                    errorText = humanizeNetworkError(e)
                }
            } finally {
                isLoading = false
            }
        }
    }

    // Состояние показывать ли пароль в виде текста или точками
    var flagPassword by rememberSaveable { mutableStateOf(false) }

    // Основной котейнер
    Box(
        modifier = Modifier
            .fillMaxSize() // растягиваем на весь экран
            .background(Color.White) // цвет фона
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
                color = Color.Black
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

                keyboardActions = KeyboardActions(
                    onNext = { focusManager.moveFocus(FocusDirection.Down) }
                ),

                textStyle = LocalTextStyle.current.copy( // стиль текста ввода
                    color = Color.Black, // цвет
                    fontSize = 16.sp // рахмер
                ),


                leadingIcon = {
                    Icon( // иконка пользователя
                        painter = painterResource(R.drawable.people_1_2),
                        contentDescription = "Логин",
                        modifier = Modifier.size(25.dp),
                        tint = if (isLoginFocused.value) Color.Black else Color.Gray
                    )
                },
                modifier = Modifier
                    .fillMaxWidth() // растягиваем на все ширину
                    .padding(horizontal = 10.dp, vertical = 2.dp)
                    .onFocusChanged { isLoginFocused.value = it.isFocused }, // отслеживаем фокус для цвета иконок
                shape = RoundedCornerShape(13.dp), // cкругление

                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.Black, // активный цвет контура
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

                keyboardActions = KeyboardActions(
                    onDone = {
                        keyboardController?.hide()
                        submitLogin()
                    }
                ),

                textStyle = LocalTextStyle.current.copy( // стиль текста ввода
                    color = Color.Black, // цвет
                    fontSize = 16.sp // рахмер
                ),

                leadingIcon = {
                    Icon( // иконка замка
                        painter = painterResource(R.drawable.lock),
                        contentDescription = "Логин",
                        modifier = Modifier.size(25.dp),
                        tint = if (isPasswordFocused.value) Color.Black else Color.Gray
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
                            tint = if (isPasswordFocused.value) Color.Black else Color.Gray
                        )
                    }
                },

                modifier = Modifier
                    .fillMaxWidth() // растягиваем на все ширину
                    .padding(horizontal = 10.dp, vertical = 2.dp)
                    .onFocusChanged { isPasswordFocused.value = it.isFocused }, // отслеживаем фокус для цвета иконок
                shape = RoundedCornerShape(13.dp), // cкругление

                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.Black, // активный цвет контура
                    unfocusedBorderColor = Color.Gray, // не активный цвет контура
                )
            )

            Spacer(Modifier.height(20.dp))

            Button(
                enabled = canSubmit,
                onClick = { submitLogin() },
                modifier = Modifier
                    .fillMaxWidth() // кнопка на всю ширину
                    .padding(horizontal = 10.dp, vertical = 5.dp)
                    .height(48.dp), // высота кнопки
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.Black,
                    contentColor = Color.White
                )
            ) {
                Text(if (isLoading) "Входим…" else "Войти", fontSize = 16.sp)
            }
            if (isLoading) {
                Spacer(Modifier.height(8.dp))
                CircularProgressIndicator(modifier = Modifier.size(24.dp))
            }
            if (errorText.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(text = errorText, color = Color.Red, fontSize = 14.sp)
            }
        }
    }
}
