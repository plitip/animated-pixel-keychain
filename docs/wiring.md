# Wiring & soldering

## Screen -> Beetle ESP32-C6

| Screen pin | Beetle pin |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SCL (CLK) | 23 |
| SDA (DIN) | 22 |
| CS | 21 |
| DC | 20 |
| RST | 19 |
| BL (only if your screen has it) | 7 |

Pin **4** is left free on purpose - on the Beetle it's wired to the battery-voltage divider.

## Screen -> Raspberry Pi Pico / Pico 2

| Screen pin | Pico pin | Physical pin |
|---|---|---|
| VCC | 3V3(OUT) | 36 |
| GND | GND | 38 |
| SCL | GP18 | 24 |
| SDA | GP19 | 25 |
| CS | GP17 | 22 |
| DC | GP20 | 26 |
| RST | GP21 | 27 |
| BL | GP22 | 29 |

## Soldering the Beetle

The Beetle comes with holes, not pins, and the screen has pins. Two ways to connect them:

**Header pins (what I did).** Solder header pins into the Beetle, then plug the screen in with
female-to-female jumpers. The two rows on the Beetle are:

- Side 1: `IO6, IO20, IO19, 3V3, GND, IO4, IO5, IO7`
- Side 2: `BAT, GND, VUSB, IO22, IO23, IO21, TX (16), RX (17)`

Easiest is to fill both rows. Short end of the pins through the holes, solder on the other side, so the long
ends stick out for the jumpers. Solder one pin at each end first, check the strip sits straight, then do the rest.

**Direct wires (slimmest).** Cut female-to-female jumpers in half, push the plug end onto the screen pin,
strip ~3 mm off the cut end and solder the bare copper into the matching Beetle hole. Only 7 joints, and the
screen stays plug-in.

### Soldering basics

1. Iron at ~350 °C, tin the tip, wipe it on a damp sponge.
2. Touch the iron to the pin **and** the metal ring of the hole at the same time, count two seconds.
3. Feed solder into the joint (not onto the iron). It should flow into a small shiny cone.
4. Remove solder, then the iron, and don't move it for a couple of seconds.

A dull ball = not enough heat, just reheat it. Two pins joined = drag the clean hot tip between them.

## Power

It's powered through the board's USB-C port, so no battery is needed.

*Optional:* to make it battery-powered, solder a 3.7V LiPo's red wire to the Beetle's **BAT** pin and black
to **GND** (USB unplugged, and never touch the iron to the battery). The Beetle charges it over USB-C.
