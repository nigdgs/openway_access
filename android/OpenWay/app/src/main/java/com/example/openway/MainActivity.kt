package com.example.openway

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MainScreen()
        }
    }
}


@Composable
fun MainScreen ( ) {
    Box ( // главный контейнер
        modifier = Modifier
            .fillMaxSize() // занимает весь экран
            .background(Color.White) // цвет
            .systemBarsPadding() // отступы от статусбара (то есть верхней системы!)
            .background(Color.White) // светло-серый
    ) {
        Text( // текст (надо будет поставить иконку палитры цветов!)
            text = "Иконка",
            modifier = Modifier // модификатооры
                .align(Alignment.TopEnd) // ставим в правый верхний угол
                .padding(12.dp) // отступ от угла
        )

        Content()
    }
}

@Composable
fun Content() {
    Column ( // главный скрол, который лежит в MainScreen(главный контейнер)
        modifier = Modifier
            .fillMaxSize() // занимает весь экран
            .verticalScroll(rememberScrollState()) // включение скрола по вертикале
            .padding(horizontal = 16.dp), // отступы по краям
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top // элементы начинаеются сверху
    ) {
        Spacer(modifier = Modifier.height(250.dp)) // отступ

        TextButtonText()

        Spacer(modifier = Modifier.height(150.dp))

        AccSection()
    }
}


@Composable
fun TextButtonText() {
    var flag_button by remember { mutableStateOf(false) } // переменная состояния кнопки

    Column (
        modifier = Modifier
            .fillMaxWidth(), // растягивается на всю ширину
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top // элементы начинаются сверху
    ) {
        Text(
            text = "Нажмите, чтобы пройти",
            color = Color.Black,
            fontSize = 20.sp
        )

        Spacer(modifier = Modifier.height(50.dp)) // отступ

        NfcButton(flag = flag_button, onToggle = { flag_button = !flag_button })

        Spacer(modifier = Modifier.height(30.dp)) // отступ

        Text(
            text = if (flag_button) "NFC включен" else "NFC отключен",
            color = Color.Black
        )
    }
}


@Composable
fun NfcButton (flag: Boolean, onToggle: () -> Unit) {
    val transition_color by animateColorAsState( // переменная плавного перехода цвета
        targetValue = if (flag) Color.Green else colorResource(id = R.color.nfc_button_on),
        animationSpec = tween (500) // время перехода
    )

    Button(
        onClick = onToggle,// дейсвтие при нажатии
        modifier = Modifier.size(225.dp), // размер
        shape = CircleShape, // форма - круг
        colors = ButtonDefaults.buttonColors( // цвет
            containerColor = transition_color, // в переменной все написано
            contentColor = if (flag) Color.White else Color.Black // текст
        )
    ) {
        Image( // векторное изображение
            painter = painterResource(id = R.drawable.turn_on), // изображение в drawable
            contentDescription = null,
            modifier = Modifier.size(80.dp), // размер
            colorFilter = ColorFilter.tint(if (flag) Color.White else Color.Black) // цвет
        )
    }

}


@Composable
fun AccSection() { // Функция Личного кабинета

    // Получаем контекст приложения для доступа к SharedPreferences
    val context = LocalContext.current

    // Создаем состояние для хранения данных пользователя
    // remember сохраняет значение при перерисовке Composable
    // mutableStateOf делает значение наблюдаемым для обновления UI
    var user by remember { mutableStateOf (User(
        "...", "...", "...", "...",)
    ) }

    // LaunchedEffect выполняет код при первом запуске Composable
    // Unit означает, что эффект запустится только один раз
    LaunchedEffect(Unit) {
        // Закгружаем пользователя из хранилища
        val betaUser = LoadUser(context)
        user = betaUser ?: User (
            name = "Андрей",
            surname = "Арустамян",
            position = "Глава вселенной",
            login = "arustamayn"
        )
    }

    Column (
        modifier = Modifier
            .fillMaxWidth() // растягивается на всю ширину
            .padding(5.dp),
        horizontalAlignment = Alignment.CenterHorizontally, // выравнивание по центру по горизонтали
        verticalArrangement = Arrangement.Top, // элементы начинаются сверху

    ) {
        Text(
            text = "Личный кабинет",
            color = Color.Black,
            fontSize = 20.sp
        )

        Spacer(modifier = Modifier.height(16.dp)) // отступ

        Image(
            contentDescription = "Аватарка",
            modifier = Modifier
                .size(150.dp)
                .clip(CircleShape)
                .background(Color.White)
                .border(5.dp, colorResource(id = R.color.inf_card), CircleShape),
            painter = painterResource(id = R.drawable.ic_launcher_background),
            contentScale = ContentScale.Crop,
        )

        Spacer(modifier = Modifier.height(16.dp)) // отступ

        Card ( // карточки имени и фамилии
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(
                colorResource(id = R.color.inf_card)
            )
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
                    text = "${user.name} ${user.surname}",
                    color = Color.Black,
                    fontSize = 17.sp
                )
            }

        }

        Card ( // карточка должности
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(
                colorResource(id = R.color.inf_card)
            )
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
                    text = "${user.position}",
                    color = Color.Black,
                    fontSize = 17.sp
                )
            }

        }

        Card ( // карточка логина
            modifier = Modifier
                .fillMaxWidth() // растягиваем по ширине
                .padding(vertical = 12.dp), // отступы по вертикале
            shape = RoundedCornerShape(12.dp), // закругление
            colors = CardDefaults.cardColors(
                colorResource(id = R.color.inf_card)
            )
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
                    text = "${user.login}",
                    color = Color.Black,
                    fontSize = 17.sp
                )
            }
        }
    }
}

fun HisSection() {

}