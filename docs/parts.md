# Parts list

Everything I used, and where I bought it in Qatar. Prices are what I paid (QAR).

| Part | Why | Where | Price |
|---|---|---|---|
| 1.28" round IPS display (GC9A01, 240x240, SPI) | the screen | [Voltaat](https://www.voltaat.com/products/1-28-round-ips-color-tft-lcd-display) | 55 |
| DFRobot Beetle ESP32-C6 | tiny board (20.5 x 25 mm) with built-in LiPo charging | [Voltaat](https://www.voltaat.com/products/beetle-esp32-c6-mini-development-board) | 29 |
| Female-to-female jumper wires (40 pack) | testing / wiring | [Voltaat](https://www.voltaat.com/products/jumper-wires-famale-to-female-40-pack) | 10 |
| Mini slide switch (3 pack) | power switch | [Voltaat](https://www.voltaat.com/products/3mm-toggle-switch) | 1 |
| 3.7V LiPo battery (1S) | portable power | [Al Annabi](https://alannabi.qa/product-category/batteries/3-7v-lithium-polymer-replacement-batteries/) | 15 |
| Header pins | so jumpers can plug into the Beetle | any electronics shop | ~2 |

**Total: about 112 QAR.**

## Optional

| Part | Why |
|---|---|
| Raspberry Pi Pico / Pico 2 | the firmware runs on it too, and its pins come pre-soldered, so it's the easiest way to test the screen without soldering |
| TP4056 Type-C charger | only needed with the Pico (the Beetle charges the battery itself) |
| Soldering iron + thin rosin-core solder | for the Beetle's header pins and the battery |

## Notes

- A smaller battery (e.g. 300-400 mAh, about 25 x 30 mm) fits right behind the screen and makes the keychain much thinner.
- Use a USB-C **data** cable. Charge-only cables are the #1 reason the board doesn't show up.
