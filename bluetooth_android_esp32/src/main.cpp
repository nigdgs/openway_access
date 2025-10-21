#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <NimBLEDevice.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <esp_wifi.h>  // ⬅ добавили

// ==== НАСТРОЙКИ ====
static const char* WIFI_SSID = "Oykumen_2.4GHZ";
static const char* WIFI_PASS = "mncphqqk22";
static const char* BACKEND_HOST = "192.168.1.221";
static const uint16_t BACKEND_PORT = 8000;
static const char* VERIFY_PATH = "/api/v1/access/verify";
static const char* GATE_ID = "GATE-01";
static const uint32_t HTTP_TIMEOUT_MS = 5000;

// OLED
#define I2C_SDA 21
#define I2C_SCL 22
Adafruit_SSD1306 display(128, 64, &Wire, -1);
void oledMsg(const String& l1, const String& l2="") {
  display.clearDisplay();
  display.setTextSize(2); display.setTextColor(SSD1306_WHITE);
  display.setCursor(0,0); display.println(l1.substring(0,10));
  display.setTextSize(1); display.setCursor(0,36); display.println(l2.substring(0,21));
  display.display();
}

// BLE
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// LED (опц.)
#define LED_GREEN 25
#define LED_RED   26
void blinkRed(uint8_t n=3, uint16_t ms=150){ pinMode(LED_RED,OUTPUT); for(uint8_t i=0;i<n;i++){digitalWrite(LED_RED,1);delay(ms);digitalWrite(LED_RED,0);delay(ms);}}

// Wi-Fi по требованию (с коэкзистенцией)
bool wifiEnsure() {
  if (WiFi.status() == WL_CONNECTED) return true;
  
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);

    WiFi.setSleep(true);                 // ⬅ обязательно при BLE
    esp_wifi_set_ps(WIFI_PS_MIN_MODEM);  // ⬅ то же на уровне esp-idf

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    uint32_t t0 = millis();
    while (millis() - t0 < 12000) {
      if (WiFi.status() == WL_CONNECTED) return true;
      delay(100);
    }
    
    Serial.printf("[WiFi] attempt %u/3 failed\n", attempt + 1);
    if (attempt < 2) {
      delay(1000u << attempt);  // 1s, 2s backoff
    }
  }
  return false;
}
void wifiOff() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
}

// HTTP verify
bool verifyToken(const String& token, String& err) {
  if (!wifiEnsure()) {
    Serial.println("[WiFi] connect fail");
    err = "Wi-Fi fail";
    return false;
  }

  String url = String("http://") + BACKEND_HOST + ":" + String(BACKEND_PORT) + VERIFY_PATH;
  String body = String("{\"gate_id\":\"") + GATE_ID + "\",\"token\":\"" + token + "\"}";

  HTTPClient http; http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(url)) {
    Serial.println("[HTTP] begin fail");
    err = "HTTP init fail";
    wifiOff();
    return false;
  }
  http.addHeader("Content-Type","application/json");
  int code = http.POST(body);
  String resp = http.getString();
  http.end();

  Serial.printf("[HTTP] %s -> %d, %s\n", url.c_str(), code, resp.c_str());
  wifiOff(); // освобождаем радио

  bool hasAllow = (resp.indexOf("\"decision\":\"ALLOW\"") >= 0);
  if (code != 200) {
    err = "HTTP " + String(code);
    return false;
  }
  if (!hasAllow) {
    err = "Backend DENY";
    return false;
  }
  return true;
}

class CB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* ch) override {
    String token = String(ch->getValue().c_str()); token.trim();
    if (token.isEmpty()) return;
    Serial.printf("[BLE] token: %s***\n", token.substring(0,8).c_str());
    oledMsg("VERIFY","Sending...");

    String err = "";
    bool allow = verifyToken(token, err);
    if (allow) {
      pinMode(LED_GREEN,OUTPUT); digitalWrite(LED_GREEN,1);
      oledMsg("ALLOW","Gate GATE-01");
      delay(1200);
      digitalWrite(LED_GREEN,0);
      oledMsg("READY","Write token");
    } else {
      blinkRed();
      oledMsg("DENY", err.isEmpty() ? "Bad token" : err);
      delay(1000);
      oledMsg("READY","Write token");
    }
  }
};

void setup() {
  Serial.begin(115200);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C, false, false)) {
    display.begin(SSD1306_SWITCHCAPVCC, 0x3D, false, false);
  }
  oledMsg("OpenWay","BLE ready");

  NimBLEDevice::init("OpenWay ESP32");
  NimBLEServer* s = NimBLEDevice::createServer();
  NimBLEService* svc = s->createService(SERVICE_UUID);
  NimBLECharacteristic* ch = svc->createCharacteristic(CHAR_UUID,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  ch->setCallbacks(new CB());
  svc->start();
  s->getAdvertising()->start();

  Serial.println("[BLE] Advertising started");
  oledMsg("READY","Write token");
}

void loop(){ delay(500); }
