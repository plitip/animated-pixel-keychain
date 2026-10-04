/*
  Pixel Keychain
  Plays pixel-art animations on a 1.28" round GC9A01 screen (240x240).
  The animations live in sprites.h (generate it with tools/gif2keychain.py).
  Press the board's button to go to the next one:
    - Beetle ESP32-C6: the BOOT button
    - Raspberry Pi Pico / Pico 2: the white BOOTSEL button

  Lib: "GFX Library for Arduino" by Moon On Our Nation (Library Manager)

  ---- DFRobot Beetle ESP32-C6 ----  board package "esp32" by Espressif (3.x),
  board "DFRobot Beetle ESP32-C6"
    Screen VCC -> 3V3
    Screen GND -> GND
    Screen SCL -> 23
    Screen SDA -> 22
    Screen CS  -> 21
    Screen DC  -> 20
    Screen RST -> 19
    Screen BL  -> 7     (only if your screen has a BL pin)
    (pin 4 is left free: the board uses it to measure the battery)

  ---- Raspberry Pi Pico / Pico 2 ----  board package "Raspberry Pi Pico/RP2040/RP2350" by Earle Philhower
    VCC -> 3V3(OUT) pin 36 | GND -> GND pin 38 | SCL -> GP18 pin 24 | SDA -> GP19 pin 25
    CS  -> GP17 pin 22     | DC  -> GP20 pin 26 | RST -> GP21 pin 27 | BL  -> GP22 pin 29
*/
#include <Arduino_GFX_Library.h>
#include "sprites.h"

// ---------------- pins ----------------
#if defined(ARDUINO_ARCH_ESP32)       // Beetle ESP32-C6
  #define TFT_SCK  23
  #define TFT_MOSI 22
  #define TFT_CS   21
  #define TFT_DC   20
  #define TFT_RST  19
  #define TFT_BL   7
  #define BUTTON_PIN 9                // BOOT button (pressed = LOW)
#else                                 // Raspberry Pi Pico / Pico 2
  #define TFT_SCK  18
  #define TFT_MOSI 19
  #define TFT_CS   17
  #define TFT_DC   20
  #define TFT_RST  21
  #define TFT_BL   22
#endif

// SPI speed. If the picture is glitchy or striped with long jumper wires, change to 20000000.
#define SPI_SPEED 40000000
#define BG_COLOR  0x0861              // very dark blue-black

#if defined(ARDUINO_ARCH_ESP32)
Arduino_DataBus *bus = new Arduino_ESP32SPI(TFT_DC, TFT_CS, TFT_SCK, TFT_MOSI, GFX_NOT_DEFINED, FSPI);
#else
Arduino_DataBus *bus = new Arduino_RPiPicoSPI(TFT_DC, TFT_CS, TFT_SCK, TFT_MOSI, GFX_NOT_DEFINED, spi0);
#endif
Arduino_GFX *gfx = new Arduino_GC9A01(bus, TFT_RST, 0 /* rotation */, true /* IPS */);

// ---------------- layers ----------------
struct Layer {
  const Sprite *s = nullptr;          // nullptr = layer not used
  int frame = 0;
  unsigned long next = 0;             // millis() when the next frame is due
  int x = 0, y = 0;                   // top-left on screen
  uint8_t *cur, *prev;                // palette indices of the current / previously drawn frame
};

uint8_t frontCur[MAX_FRONT_PIXELS], frontPrev[MAX_FRONT_PIXELS];
uint8_t backCur[MAX_BACK_PIXELS],  backPrev[MAX_BACK_PIXELS];
Layer front, back;

int show = 0;
uint16_t line[240];
int16_t dirtyX1[240], dirtyX2[240];   // per screen row: the span that needs redrawing

// ---------------- background ----------------
static inline uint16_t bgAt(int sx, int sy) {
  int dx = sx - 120, dy = sy - 120;
  int d2 = dx * dx + dy * dy;
  if (d2 >= 112 * 112 && d2 < 116 * 116) return SHOWS[show].ringIn;
  if (d2 >= 116 * 116 && d2 < 120 * 120) return SHOWS[show].ringOut;
  return BG_COLOR;
}

// Colour index of a layer at a screen pixel (0 = transparent / outside)
// (layers can be enlarged by any amount: scale256 = 256 means 1x, 371 means 1.45x, ...)
static inline uint8_t layerIdx(const Layer &L, int sx, int sy) {
  if (!L.s || sx < L.x || sy < L.y) return 0;
  int fx = ((sx - L.x) << 8) / L.s->scale256, fy = ((sy - L.y) << 8) / L.s->scale256;
  if (fx >= L.s->w || fy >= L.s->h) return 0;
  return L.cur[fy * L.s->w + fx];
}

// Final colour on screen: front layer, then back layer, then background + ring
static inline uint16_t colourAt(int sx, int sy) {
  uint8_t i = layerIdx(front, sx, sy);
  if (i) return front.s->palette[i];
  i = layerIdx(back, sx, sy);
  if (i) return back.s->palette[i];
  return bgAt(sx, sy);
}

// ---------------- decoding ----------------
// RLE pairs of [count, value]: value 255 = keep the previous frame's pixels
void decodeFrame(Layer &L) {
  const Sprite *s = L.s;
  const int total = s->w * s->h;
  uint32_t p = s->offset[L.frame], end = s->offset[L.frame + 1];
  int i = 0;
  while (p < end && i < total) {
    uint8_t n = s->rle[p], v = s->rle[p + 1];
    p += 2;
    if (v == 255) { i += n; continue; }
    while (n-- && i < total) L.cur[i++] = v;
  }
}

void markDirty(int sy, int x1, int x2) {
  if (sy < 0 || sy >= 240) return;
  if (x1 < 0) x1 = 0;
  if (x2 > 239) x2 = 239;
  if (x2 < x1) return;
  if (x1 < dirtyX1[sy]) dirtyX1[sy] = x1;
  if (x2 > dirtyX2[sy]) dirtyX2[sy] = x2;
}

// Mark the screen area where this layer changed since it was last drawn (or all of it)
void markLayer(Layer &L, bool all) {
  const Sprite *s = L.s;
  for (int cy = 0; cy < s->h; cy++) {
    const uint8_t *row = &L.cur[cy * s->w], *old = &L.prev[cy * s->w];
    int x1 = 0, x2 = s->w - 1;
    if (!all) {
      while (x1 < s->w && row[x1] == old[x1]) x1++;
      if (x1 == s->w) continue;
      while (row[x2] == old[x2]) x2--;
    }
    const int S = s->scale256;
    int sy1 = L.y + ((cy * S) >> 8) - 1, sy2 = L.y + (((cy + 1) * S + 255) >> 8);   // 1px margin for rounding
    int sx1 = L.x + ((x1 * S) >> 8) - 1, sx2 = L.x + (((x2 + 1) * S + 255) >> 8);
    for (int sy = sy1; sy <= sy2; sy++) markDirty(sy, sx1, sx2);
  }
  memcpy(L.prev, L.cur, s->w * s->h);
}

void flushDirty() {
  for (int sy = 0; sy < 240; sy++) {
    if (dirtyX2[sy] < dirtyX1[sy]) continue;
    int n = dirtyX2[sy] - dirtyX1[sy] + 1;
    for (int k = 0; k < n; k++) line[k] = colourAt(dirtyX1[sy] + k, sy);
    gfx->draw16bitRGBBitmap(dirtyX1[sy], sy, line, n, 1);
    dirtyX1[sy] = 240; dirtyX2[sy] = -1;
  }
}

void setupLayer(Layer &L, const Sprite *s, unsigned long now) {
  L.s = s;
  if (!s) return;
  L.frame = 0;
  int wS = (s->w * s->scale256 + 255) >> 8, hS = (s->h * s->scale256 + 255) >> 8;   // size on screen
  L.x = (240 - wS) / 2 + s->offX;
  L.y = (240 - hS) / 2 + s->offY;
  decodeFrame(L);
  L.next = now + s->delay[0];
}

void selectShow(int n) {
  show = n;
  unsigned long now = millis();
  setupLayer(back, SHOWS[show].back, now);
  setupLayer(front, SHOWS[show].front, now);
  for (int y = 0; y < 240; y++) { dirtyX1[y] = 0; dirtyX2[y] = 239; }   // redraw the whole screen
  if (back.s) memcpy(back.prev, back.cur, back.s->w * back.s->h);
  memcpy(front.prev, front.cur, front.s->w * front.s->h);
  flushDirty();
}

// Advance a layer if its next frame is due. Returns true if it changed.
bool tick(Layer &L, unsigned long now) {
  if (!L.s || (long)(now - L.next) < 0) return false;
  L.frame = (L.frame + 1) % L.s->frames;
  decodeFrame(L);
  L.next += L.s->delay[L.frame];
  if ((long)(now - L.next) > 250) L.next = now + L.s->delay[L.frame];   // fell behind: catch up
  markLayer(L, false);
  return true;
}

// ---------------- button ----------------
bool buttonPressed() {
#if defined(ARDUINO_ARCH_ESP32)
  return digitalRead(BUTTON_PIN) == LOW;
#else
  return BOOTSEL;
#endif
}

void setup() {
  Serial.begin(115200);
#if defined(ARDUINO_ARCH_ESP32)
  pinMode(BUTTON_PIN, INPUT_PULLUP);
#endif
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);         // backlight on (harmless if your screen has no BL pin)

  front.cur = frontCur; front.prev = frontPrev;
  back.cur = backCur;   back.prev = backPrev;
  for (int y = 0; y < 240; y++) { dirtyX1[y] = 240; dirtyX2[y] = -1; }

  if (!gfx->begin(SPI_SPEED)) {
    Serial.println("Screen init failed - check the wiring");
  }
  selectShow(0);
}

void loop() {
  static bool wasPressed = false;
  static unsigned long lastPress = 0;
  bool pressed = buttonPressed();
  if (pressed && !wasPressed && millis() - lastPress > 200) {   // next animation
    lastPress = millis();
    selectShow((show + 1) % SHOW_COUNT);
  }
  wasPressed = pressed;

  unsigned long now = millis();
  bool changed = tick(back, now);
  changed |= tick(front, now);
  if (changed) flushDirty();
  else delay(1);
}
