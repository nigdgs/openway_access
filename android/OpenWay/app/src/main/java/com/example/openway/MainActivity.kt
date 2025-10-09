package com.example.openway

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.openway.ble.BleClient
import com.example.openway.util.TokenProvider



class MainActivity : ComponentActivity() {
    internal lateinit var bleClient: BleClient
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bleClient = BleClient(this)
        setContent {
            AppNav()
        }
    }
}


@Composable
fun AppNav() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = "mainScreen") {
        composable("loginScreen") {
            LoginScreen(navController)  // Экран авторизации
        }
        composable("mainScreen") {
            MainScreen(navController)  // Главный экран
        }
    }
}



@Composable
fun MainScreen (navController: NavController) {
    var flagTheme by remember { mutableStateOf(false) } // переменная состояния кнопки светлого/темного режима

    val box_color by animateColorAsState( // переменная плавного перехода цвета
        targetValue = if (flagTheme) {
            colorResource(R.color.dark_theme)
        } else {
            Color.White
        },
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy, // амортизация для плавного перехода
            stiffness = Spring.StiffnessLow // жесткость перехода
        )
    )

    Box ( // главный контейнер
        modifier = Modifier
            .fillMaxSize() // занимает весь экран
            .background(Color.White) // цвет
            .systemBarsPadding() // отступы от статусбара (то есть верхней системы!)
            .background(box_color) // в переменной все написанно
    ) {
        Content(flagTheme, navController)

        PhotoIconToggleButton(
            flagIcButton = flagTheme,
            onIcButton = {flagTheme = !flagTheme},
            modifier = Modifier
                .align (Alignment.TopEnd) // ставим в правый верхний угол
                .padding(12.dp) // отступ от угла
        )
    }
}


@Composable
fun PhotoIconToggleButton (
    flagIcButton: Boolean, // флаг состояния вкл/выкл
    onIcButton: () -> Unit,
    modifier: Modifier = Modifier // Модификатор
) {
    IconButton(
        onClick = onIcButton, // переключение состояния
        modifier = modifier.size(40.dp) // размер кнопки
    ) {
        Crossfade(
            targetState = flagIcButton, // состояние
            animationSpec = tween (durationMillis = 900) // время перехода изображения
        ) { on -> // сотсояние
            Image(
                painter = painterResource(
                    id = if (on) R.drawable.dark_theme else R.drawable.light_theme
                ),
                contentDescription = if (on) "Включенно" else "Выключено", // для слобовидящих(это строчка обязательно)
                modifier = Modifier.size(40.dp), // размер изображения
                contentScale = ContentScale.Crop // подгоняем изображения без искажений
            )
        }
    }
}

@Composable
fun Content(flagTheme: Boolean, navController: NavController) {

    Column ( // главный скрол, который лежит в MainScreen(главный контейнер)
        modifier = Modifier
            .fillMaxSize() // занимает весь экран
            .verticalScroll(rememberScrollState()) // включение скрола по вертикале
            .padding(horizontal = 16.dp), // отступы по краям
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top // элементы начинаеются сверху
    ) {
        Spacer(modifier = Modifier.height(250.dp)) // отступ

        TextButtonText(flagTheme)

        Spacer(modifier = Modifier.height(150.dp))

        AccSection(flagTheme, navController)
    }
}


@Composable
fun TextButtonText (flagTheme: Boolean) {
    var flagNfcButton by remember { mutableStateOf(false) } // переменная состояния кнопки nfc
    val context = LocalContext.current
    val mainActivity = context as? MainActivity

    Column (
        modifier = Modifier
            .fillMaxWidth(), // растягивается на всю ширину
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top // элементы начинаются сверху
    ) {
        Text(
            text = "Нажмите, чтобы пройти",
            color = if (flagTheme) Color.White else Color.Black,
            fontSize = 20.sp
        )

        Spacer(modifier = Modifier.height(50.dp)) // отступ

        NfcButton(
            flagNfcButton = flagNfcButton,
            flagTheme,
            onNfcButton = {
                flagNfcButton = !flagNfcButton
                if (flagNfcButton) {
                    mainActivity?.let {
                        val token = TokenProvider.getToken(it)
                        it.bleClient.sendToken(token)
                    }
                } else {
                    // ничего не делаем при выключении
                }
            })

        Spacer(modifier = Modifier.height(30.dp)) // отступ

        Text(
            text = if (flagNfcButton) "NFC включен" else "NFC отключен",
            color = if (flagTheme) Color.White else Color.Black
        )
    }
}


@Composable
fun NfcButton (flagNfcButton: Boolean, flagTheme: Boolean, onNfcButton: () -> Unit) {
    var lastTheme by remember { mutableStateOf(flagTheme) }

    val button_color by animateColorAsState( // переменная плавного перехода цвета
        targetValue = if (flagNfcButton) {
            colorResource(id = R.color.nfc_button_on)
        } else {
            if (flagTheme) {
                Color.DarkGray
            } else {
                colorResource(id = R.color.light_nfc_button_on)
            }
        },
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy, // амортизация для плавного перехода
            stiffness = Spring.StiffnessMediumLow // жесткость перехода
        )
    )

    val image_color by animateColorAsState( // переменная плавного перехода цвета
        targetValue = if (flagNfcButton) {
            if (flagTheme) {
                Color.Black
            } else {
                Color.White
            }
        } else {
            if (flagTheme) {
                Color.White
            } else {
                Color.Black
            }
        },
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy, // амортизация для плавного перехода
            stiffness = Spring.StiffnessVeryLow // жесткость перехода
        )
    )

    Button(
        onClick = onNfcButton, // дейсвтие при нажатии
        modifier = Modifier.size(225.dp), // размер
        shape = CircleShape, // форма - круг
        colors = ButtonDefaults.buttonColors(containerColor = button_color)
    ) {
        Image( // векторное изображение
            painter = painterResource(id = R.drawable.turn_on), // изображение в drawable
            contentDescription = null,
            modifier = Modifier.size(80.dp), // размер
            //colorFilter = ColorFilter.tint(if (flagNfcButton) Color.White else Color.Black) // цвет
            colorFilter = ColorFilter.tint(image_color) // в переменной все написанно
        )
    }
}


@Composable
fun AccSection (flagTheme: Boolean, navController: NavController) { // Функция Личного кабинета

    // Получаем контекст приложения для доступа к SharedPreferences
    val context = LocalContext.current


    val card_color by animateColorAsState( // переменная плавного перехода цвета
        targetValue = if (flagTheme) {
            Color.DarkGray
        } else {
            colorResource(id = R.color.inf_card)
        },
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy, // амортизация для плавного перехода
            stiffness = Spring.StiffnessLow // жесткость перехода
        )
    )

    Column (
        modifier = Modifier
            .fillMaxWidth() // растягивается на всю ширину
            .padding(5.dp),
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top, // элементы начинаются сверху
    ) {
        Text(
            text = "Личный кабинет",
            color = if (flagTheme) Color.White else Color.Black,
            fontSize = 20.sp
        )

        Spacer(modifier = Modifier.height(16.dp)) // отступ

        Image(
            contentDescription = "Аватарка",
            modifier = Modifier
                .size(130.dp)
                .clip(CircleShape)
                .background(card_color),
            painter = painterResource(id = R.drawable.ic_launcher_background),
            contentScale = ContentScale.Crop,
        )

        Spacer(modifier = Modifier.height(16.dp)) // отступ

        Card ( // карточки имени и фамилии
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(card_color)
        ) {
            Column (
                modifier = Modifier.padding(16.dp) // отступы
            ) {
                Text(
                    text = "Имя и Фамилия",
                    color = Color.Gray,
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(5.dp)) // отступ

                Text (
                    text = "Андрей Арустамян",
                    color = if (flagTheme) Color.White else Color.Black,
                    fontSize = 17.sp
                )
            }

        }

        Card ( // карточка должности
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(card_color)
        ) {
            Column (
                modifier = Modifier.padding(16.dp) // отступы
            ) {
                Text(
                    text = "Должность",
                    color = Color.Gray,
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(5.dp)) // отступ

                Text (
                    text = "Генеральный директор",
                    color = if (flagTheme) Color.White else Color.Black,
                    fontSize = 17.sp
                )
            }

        }

        Card ( // карточка логина
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(card_color)
        ) {
            Column (
                modifier = Modifier.padding(16.dp) // отступы
            ) {
                Text(
                    text = "Логин",
                    color = Color.Gray,
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(5.dp)) // отступ

                Text (
                    text = "andrey",
                    color = if (flagTheme) Color.White else Color.Black,
                    fontSize = 15.sp
                )
            }
        }

        exitAcc(navController)

    }
}


@Composable
fun exitAcc (navController: NavController) {
    Button(
        onClick = {
            navController.navigate("LoginScreen")
        }, // пока что без логики
        modifier = Modifier
            .fillMaxWidth() // Кнопка занимает всю ширину
            .padding(16.dp), // Отступы вокруг кнопки
        shape = RoundedCornerShape(12.dp), // Закругленные углы
        colors = ButtonDefaults.buttonColors(colorResource(R.color.exit_button_light_theme))

    ) {
        // Используем Row для горизонтального расположения иконки и текста
        Row(
            verticalAlignment = Alignment.CenterVertically, // Центрируем иконку и текст по вертикали
            horizontalArrangement = Arrangement.Start // Располагаем элементы слева
        ) {
            Icon(
                painter = painterResource(id = R.drawable.exit), // Иконка для выхода (поставь свою иконку)
                contentDescription = "Выйти из аккаунта", // Описание для доступности
                modifier = Modifier.size(20.dp), // Размер иконки
                tint = Color.Red// Цвет иконки
            )
            Spacer(modifier = Modifier.width(8.dp)) // Отступ между иконкой и текстом
            Text(
                text = "Выйти из аккаунта", // Текст кнопки
                color = Color.Red, // Цвет текста
                fontSize = 16.sp // размер текста
            )
        }
    }
}