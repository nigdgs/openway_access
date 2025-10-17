package com.example.openway

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.navigation.NavController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.openway.ble.BleClient
import com.example.openway.util.TokenProvider

class MainActivity : ComponentActivity() {

    internal lateinit var bleClient: BleClient
    private var pendingToken: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bleClient = BleClient(this)

        setContent {
            AppNav() // без Theme-обертки
        }
    }

    /** Зовём из UI: (LocalContext.current as MainActivity).sendTokenWithPerms() */
    fun sendTokenWithPerms(token: String? = null) {
        ensureBlePermsAndSend(token)
    }

    // ---------- runtime permissions ----------
    private val blePermsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { res ->
        val ok = res.values.all { it == true }
        if (ok) {
            Log.d(TAG, "perms granted")
            reallySendToken(pendingToken)
        } else {
            Toast.makeText(this, "Нужны разрешения Bluetooth", Toast.LENGTH_SHORT).show()
            Log.d(TAG, "perms denied: $res")
        }
    }

    private fun ensureBlePermsAndSend(token: String? = null) {
        pendingToken = token ?: TokenProvider.getToken(this)

        val need = mutableListOf<String>().apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                add(Manifest.permission.BLUETOOTH_SCAN)
                add(Manifest.permission.BLUETOOTH_CONNECT)
            } else {
                add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }
        val toAsk = need.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (toAsk.isNotEmpty()) {
            blePermsLauncher.launch(toAsk.toTypedArray())
        } else {
            reallySendToken(pendingToken)
        }
    }    private fun reallySendToken(token: String?) {
        if (token.isNullOrBlank()) {
            Toast.makeText(this, "Пустой токен", Toast.LENGTH_SHORT).show()
            Log.d(TAG, "empty token")
            return
        }
        Log.d(TAG, "sending token len=${token.length}")
        bleClient.sendToken(token) { ok, msg ->
            Log.d(TAG, "sendToken result ok=$ok, msg=$msg")
            Toast.makeText(this, if (ok) "Токен отправлен" else "Ошибка: $msg", Toast.LENGTH_SHORT)
                .show()
        }
    }

    companion object {
        const val TAG = "BleClient"
    }
}

/* ======================= Навигация ======================= */
@Composable
fun AppNav() {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = "mainScreen") {
        composable("mainScreen") { MainScreen(nav) }
        composable("loginScreen") { LoginScreen(nav) }
    }
}

/* ======================= UI (ваш дизайн) ======================= */

@Composable
fun MainScreen(navController: NavController) {
    var flagTheme by remember { mutableStateOf(true) }


    val context = LocalContext.current
    val activity = context as? ComponentActivity

    // Изменяем цвет иконок в статус-баре
    LaunchedEffect(flagTheme) {
        if (activity != null) {
            val window = activity.window
            WindowInsetsControllerCompat(window, window.decorView).apply {
                isAppearanceLightStatusBars = if (flagTheme) false else true
            }
        }
    }


    val boxColor by animateColorAsState(
        targetValue = if (flagTheme) colorResource(R.color.dark_theme) else Color.White,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessLow
        )
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(boxColor)
            //.padding(35.dp) // отступ
    ) {
        Content(flagTheme, navController)

        PhotoIconToggleButton(
            flagIcButton = flagTheme,
            onIcButton = { flagTheme = !flagTheme },
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(45.dp)
        )
    }
}

@Composable
fun PhotoIconToggleButton(
    flagIcButton: Boolean,
    onIcButton: () -> Unit,
    modifier: Modifier = Modifier
) {
    IconButton(onClick = onIcButton, modifier = modifier
        .size(40.dp)
        .offset(x = 20.dp)) {
        Crossfade(targetState = flagIcButton, animationSpec = tween(900)) { on ->
            Image(
                painter = painterResource(id = if (on) R.drawable.dark_theme else R.drawable.light_theme),
                contentDescription = if (on) "Включено" else "Выключено",
                modifier = Modifier.size(40.dp),
                contentScale = ContentScale.Crop
            )
        }
    }
}

@Composable
fun Content(flagTheme: Boolean, navController: NavController) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        Spacer(Modifier.height(225.dp))
        TextButtonText(flagTheme)
        Spacer(Modifier.height(250.dp))
        AccSection(flagTheme, navController)
    }
}

@Composable
fun TextButtonText(flagTheme: Boolean) {
    var flagNfcButton by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val act = context as? MainActivity

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        Text(
            text = "Нажмите, чтобы пройти",
            color = if (flagTheme) Color.White else Color.Black,
            fontSize = 20.sp
        )

        Spacer(Modifier.height(50.dp))

        // Нажатие на большую кнопку -> проверяем пермишены и шлём токен
        BluetoothButton(
            flagNfcButton = flagNfcButton,
            flagTheme = flagTheme,
            onNfcButton = {
                flagNfcButton = !flagNfcButton
                if (flagNfcButton) {
                    act?.sendTokenWithPerms()
                }
            }
        )

        Spacer(Modifier.height(30.dp))
        Text(
                text = if (flagNfcButton) "BLE активен" else "BLE неактивен",
        color = if (flagTheme) Color.White else Color.Black
        )
    }
}

@Composable
fun BluetoothButton(flagNfcButton: Boolean, flagTheme: Boolean, onNfcButton: () -> Unit) {
    val buttonColor by animateColorAsState(
        targetValue = if (flagNfcButton) {
            colorResource(id = R.color.nfc_button_on)
        } else {
            if (flagTheme) Color.DarkGray else colorResource(id = R.color.light_nfc_button_on)
        },
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessMediumLow
        )
    )

    val imageColor by animateColorAsState(
        targetValue =
            if (flagNfcButton) if (flagTheme) Color.Black else Color.White
            else if (flagTheme) Color.White else Color.Black,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessVeryLow
        )
    )

    Button(
        onClick = onNfcButton,
        modifier = Modifier.size(225.dp),
        shape = CircleShape,
        colors = ButtonDefaults.buttonColors(containerColor = buttonColor)
    ) {
        Image(
            painter = painterResource(id = R.drawable.turn_on),
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            colorFilter = ColorFilter.tint(imageColor)
        )
    }
}

/* Остальная часть UI без изменений */
@Composable
fun AccSection(flagTheme: Boolean, navController: NavController) {
    val cardColor by animateColorAsState(
        targetValue = if (flagTheme) Color.Gray else Color.White,

        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessLow
        )
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 10.dp)
            .clip(RoundedCornerShape(20.dp))
            .background(
                color = if (flagTheme) Color.DarkGray else colorResource(R.color.inf_card),
                shape = RoundedCornerShape(20.dp)
            )
    ) {

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(5.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Top
        ) {
            Spacer(Modifier.height(7.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth() // Прямоугольник будет на всю ширину экрана
                    .height(20.dp) // Установите желаемую высоту прямоугольника
                    .padding(horizontal = 125.dp)
                    .background(
                        color = if (flagTheme) Color.Gray else Color.White, // Цвет фона прямоугольника
                        shape = RoundedCornerShape(10.dp) // Если хотите, добавьте закругленные углы
                    )
            )

            Spacer(Modifier.height(50.dp))

            Image(
                contentDescription = "Аватарка",
                modifier = Modifier
                    .size(115.dp)
                    .clip(CircleShape)
                    .background(cardColor),
                painter = painterResource(id = R.drawable.person),
                contentScale = ContentScale.Crop,
                colorFilter = if (flagTheme) ColorFilter.tint(Color.White) else ColorFilter.tint(Color.Black)
            )

            Spacer(Modifier.height(20.dp))

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp, horizontal = 15.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(cardColor),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text("Имя и Фамилия", color = if (flagTheme) Color.DarkGray else Color.Gray, fontSize = 12.sp)
                    Spacer(Modifier.height(5.dp))
                    Text(
                        "Андрей Арустамян",
                        color = if (flagTheme) Color.White else Color.Black,
                        fontSize = 15.sp
                    )
                }
            }

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp, horizontal = 15.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(cardColor)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text("Должность", color = if (flagTheme) Color.DarkGray else Color.Gray, fontSize = 12.sp)
                    Spacer(Modifier.height(5.dp))
                    Text(
                        "Генеральный директор",
                        color = if (flagTheme) Color.White else Color.Black,
                        fontSize = 15.sp
                    )
                }
            }
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp, horizontal = 15.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(cardColor)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text("Логин", color = if (flagTheme) Color.DarkGray else Color.Gray, fontSize = 12.sp)
                    Spacer(Modifier.height(5.dp))
                    Text(
                        "andrey",
                        color = if (flagTheme) Color.White else Color.Black,
                        fontSize = 15.sp
                    )
                }
            }

            exitAcc(navController)

            Spacer(Modifier.height(1.dp))
        }
    }
}

@Composable
fun exitAcc(navController: NavController) {
    Button(
        onClick = { navController.navigate("loginScreen") },
        modifier = Modifier
            .fillMaxWidth()
            .padding(41.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(colorResource(R.color.exit_button_light_theme))
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Start) {
            Icon(
                painter = painterResource(id = R.drawable.exit),
                contentDescription = "Выйти из аккаунта",
                modifier = Modifier.size(20.dp),
                tint = Color.Red
            )
            Spacer(Modifier.width(8.dp))
            Text("Выйти из аккаунта", color = Color.Red, fontSize = 16.sp)
        }
    }
}

