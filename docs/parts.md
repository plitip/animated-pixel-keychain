# Parts list

Everything I used, and where I bought it in Qatar. Prices are what I paid (QAR).

| Part | Why | Where | Price |
|---|---|---|---|
| 1.28" round IPS display (GC9A01, 240x240, SPI) | the screen | [Voltaat](https://www.voltaat.com/products/1-28-round-ips-color-tft-lcd-display) | 55 |
| DFRobot Beetle ESP32-C6 | tiny board (20.5 x 25 mm), USB-C | [Voltaat](https://www.voltaat.com/products/beetle-esp32-c6-mini-development-board) | 29 |
| Female-to-female jumper wires (40 pack) | testing / wiring | [Voltaat](https://www.voltaat.com/products/jumper-wires-famale-to-female-40-pack) | 10 |
| Header pins | so jumpers can plug into the Beetle | any electronics shop | ~2 |

**Total: about 96 QAR.** It's powered over USB-C (phone charger, power bank or laptop), so no battery is needed.

## Optional

| Part | Why |
|---|---|
| Raspberry Pi Pico / Pico 2 | the firmware runs on it too, and its pins come pre-soldered, so it's the easiest way to test the screen without soldering |
| Soldering iron + thin rosin-core solder | for the Beetle's header pins |
| 3.7V LiPo + slide switch | if you want it battery-powered: the Beetle can charge a LiPo on its BAT pin (with a Pico you'd also need a TP4056 charger) |

## Notes

- Use a USB-C **data** cable. Charge-only cables are the #1 reason the board doesn't show up.
