
#include <Arduino.h>
#include <WiFi.h>
#include <SPI.h>
#include <Adafruit_PN532.h>
#include <HTTPClient.h>

// Пины SPI для PN532 (пример)
#define PN532_SCK  18
#define PN532_MOSI 23
#define PN532_SS    5
#define PN532_MISO 19
#define PN532_RST  22

Adafruit_PN532 nfc(PN532_SS, PN532_SCK, PN532_MOSI, PN532_MISO, PN532_RST);

const char* WIFI_SSID = "YourWiFi";
const char* WIFI_PASS = "YourPass";
const char* API_BASE  = "http://10.0.2.2:8000/api";

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" OK");

  nfc.begin();
  uint32_t ver = nfc.getFirmwareVersion();
  if (!ver) { Serial.println("PN532 not found"); while(true) delay(1000); }
  nfc.SAMConfig(); // режим чтения
  Serial.println("PN532 ready");
}

void loop() {
  uint8_t uid[7]; uint8_t uidLen;
  if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLen)) {
    String token="";
    for (int i=0;i<uidLen;i++){ if (uid[i]<16) token+="0"; token+=String(uid[i],HEX); }
    Serial.printf("Token demo: %s\n", token.c_str());

    if (WiFi.status()==WL_CONNECTED) {
      HTTPClient http;
      http.begin(String(API_BASE)+"/access/verify");
      http.addHeader("Content-Type","application/json");
      // Демопакет (будете формировать из APDU ответа телефона)
      String body = String("{"door_id":"D-1","ts":1693567200,"
                           ""apdu":{"user_id":"U-1","exp":9999999999,"
                           ""payload_b64":"Zm9v","sig_b64":"YmFy"},"
                           ""controller_info":{"id":"C-1","fw":"1.0.0"}}");
      int code = http.POST(body);
      String resp = http.getString();
      http.end();
      Serial.printf("VERIFY HTTP %d %s\n", code, resp.c_str());
    }
    delay(1500);
  }
}
