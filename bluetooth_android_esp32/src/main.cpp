#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <NimBLEDevice.h>

// ====== НАСТРОЙКИ ======
const char* WIFI_SSID     = "MOKA";
const char* WIFI_PASS = "MOKAMOKA";
static const char* BACKEND_HOST = "192.168.10.228"; 
static const uint16_t BACKEND_PORT = 8001;
static const char* VERIFY_PATH = "/api/v1/access/verify";
static const char* HEALTH_PATH = "/health";
static const char* GATE_ID = "GATE-01";
static const uint32_t HTTP_TIMEOUT_MS = 7000;

// ====== BLE UUID ======
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// ====== OLED (опционально) ======
/*
 * Если есть OLED SSD1306 по I2C:
 * SDA = 21, SCL = 22, адрес обычно 0x3C
 * Если нет — можно закомментировать весь блок OLED
*/
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void oledMsg(const String& l1, const String& l2="") {
  static bool oledOK = true;
  if (!oledOK) return;
  display.clearDisplay();
  display.setTextSize(2); display.setTextColor(SSD1306_WHITE);
  display.setCursor(0,0); display.println(l1.substring(0,10));
  display.setTextSize(1); display.setCursor(0,36); display.println(l2.substring(0,21));
  display.display();
}

// ====== LED (опционально) ======
#define LED_GREEN 25
#define LED_RED   26
void blinkRed(uint8_t n=3, uint16_t ms=150) {
  pinMode(LED_RED, OUTPUT);
  for (uint8_t i=0; i<n; i++) { digitalWrite(LED_RED,1); delay(ms); digitalWrite(LED_RED,0); delay(ms); }
}

// ====== Wi-Fi с BLE-коэкзистенцией ======
#include <esp_wifi.h>

bool wifiEnsure() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);

  // Коэкзистенция с BLE
  WiFi.setSleep(true);
  esp_wifi_set_ps(WIFI_PS_MIN_MODEM);

  Serial.printf("[WiFi] Connecting to %s ...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  uint32_t t0 = millis();
  while (millis() - t0 < 15000) {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("[WiFi] Connected. IP: %s\n", WiFi.localIP().toString().c_str());
      return true;
    }
    delay(250);
  }
  Serial.println("[WiFi] connect timeout");
  return false;
}

// На время отладки Wi-Fi оставляем включённым (не вызываем WiFi.mode(WIFI_OFF)),
// чтобы не ловить "wifi un-init timeout" и видеть стабильные логи.
// Если нужно — можно добавить принудительное выключение после запросов.

// ====== HTTP helpers ======
bool httpHealth() {
  if (!wifiEnsure()) return false;
  HTTPClient http;
  String url = String("http://") + BACKEND_HOST + ":" + String(BACKEND_PORT) + HEALTH_PATH;
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(url)) { Serial.println("[HTTP] begin fail (/health)"); return false; }
  int code = http.GET();
  String resp = http.getString();
  Serial.printf("[HTTP] GET %s -> %d (%s), %s\n",
      url.c_str(), code, HTTPClient::errorToString(code).c_str(), resp.c_str());
  http.end();
  return (code==200 && resp.indexOf("\"ok\"")>=0);
}

bool verifyToken(const String& token) {
  if (!wifiEnsure()) { Serial.println("[WiFi] connect fail"); return false; }

  // Быстрый пинг /health (даст понять, виден ли сервер и порт)
  if (!httpHealth()) {
    Serial.println("[HTTP] /health not reachable");
    oledMsg("NET ERR", "/health fail");
    return false;
  }

  String url  = String("http://") + BACKEND_HOST + ":" + String(BACKEND_PORT) + VERIFY_PATH;
  String body = String("{\"gate_id\":\"") + GATE_ID + "\",\"token\":\"" + token + "\"}";

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(url)) { Serial.println("[HTTP] begin fail (/verify)"); return false; }
  http.addHeader("Content-Type","application/json");
  int code = http.POST(body);
  String resp = http.getString();
  http.end();

  Serial.printf("[HTTP] POST %s -> %d (%s), %s\n",
      url.c_str(), code, HTTPClient::errorToString(code).c_str(), resp.c_str());

  return (code==200 && resp.indexOf("\"decision\":\"ALLOW\"")>=0);
}

// ====== BLE callbacks ======
class CB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* ch) override {
    std::string v = ch->getValue();
    String token = String(v.c_str()); token.trim();
    if (token.isEmpty()) return;

    Serial.printf("[BLE] token: %s\n", token.c_str());
    oledMsg("VERIFY", "Sending...");

    bool allow = verifyToken(token);
    if (allow) {
      pinMode(LED_GREEN, OUTPUT); digitalWrite(LED_GREEN, 1);
      oledMsg("ALLOW", "Gate " + String(GATE_ID));
      delay(1200);
      digitalWrite(LED_GREEN, 0);
      oledMsg("READY", "Write token");
    } else {
      blinkRed();
      oledMsg("DENY", "Bad token/perm");
      delay(1000);
      oledMsg("READY", "Write token");
    }
  }
};

void setup() {
  Serial.begin(115200);
  delay(200);

  // OLED init (если подключён)
  Wire.begin(21, 22);
  Wire.setClock(100000);
  bool oledInited = display.begin(SSD1306_SWITCHCAPVCC, 0x3C, false, false);
  if (!oledInited) oledInited = display.begin(SSD1306_SWITCHCAPVCC, 0x3D, false, false);
  if (oledInited) {
    oledMsg("OpenWay", "BLE ready");
  }

  // BLE init
  NimBLEDevice::init("OpenWay ESP32");
  NimBLEServer* s = NimBLEDevice::createServer();
  NimBLEService* svc = s->createService(SERVICE_UUID);
  NimBLECharacteristic* ch = svc->createCharacteristic(
      CHAR_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  ch->setCallbacks(new CB());
  svc->start();
  s->getAdvertising()->start();

  Serial.println("[BLE] Advertising started");

  // Разовая проверка сети
  if (wifiEnsure()) {
    httpHealth(); // выведет в Serial код и ответ
  }
  if (oledInited) oledMsg("READY", "Write token");
}

void loop() {
  delay(500);
}
