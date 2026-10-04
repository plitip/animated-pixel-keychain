#!/usr/bin/env python3
"""
gif2keychain.py - turn GIFs into the sprites.h file the keychain firmware plays.

    python tools/gif2keychain.py tools/animations.json -o firmware/PokemonKeychain/sprites.h

animations.json lists "shows". Each show has an optional "back" layer, a "front" layer and
two ring colours. A layer looks like:

    {
      "file": "tools/examples/orb.gif",
      "native_pixel": "auto",     // shrink upscaled pixel art back to real pixels ("auto", a number, or null)
      "crop": [x, y, w, h],       // optional, in (native) pixels
      "frame_step": 1,            // keep every Nth frame (delays are stretched to keep the speed)
      "colors": 254,              // max colours (reduced with median-cut if needed)
      "scale": 1,                 // size on screen, e.g. 2 or 1.45
      "offset": [0, 0]            // extra nudge in screen pixels
    }

Frames are stored as RLE pairs [count, value]: 0 = transparent, 255 = unchanged from the previous
frame, anything else = palette index. Every frame is decoded again after encoding to check it.
"""
import argparse, json, math, sys
import numpy as np
from PIL import Image, ImageSequence

SCREEN = 240
VISIBLE_R = 111          # radius inside the edge ring
SKIP = 255
MAX_COLOURS = 254        # indices 1..254 (0 = transparent, 255 = skip)


def load(path):
    im = Image.open(path)
    frames, delays = [], []
    for f in ImageSequence.Iterator(im):
        frames.append(np.array(f.convert("RGBA")))
        delays.append(int(f.info.get("duration", 50)) or 50)
    return frames, delays


def detect_native_grid(a, axis_len, other_len, horizontal):
    """Find how many real pixels fit across an upscaled pixel-art image (works for non-integer upscales)."""
    best = None
    for n in range(16, min(axis_len, 400)):
        p = axis_len / n
        if p < 1.5:
            break
        centres = (p * np.arange(n) + p / 2).astype(int)
        left = np.clip((centres - p * 0.3).astype(int), 0, axis_len - 1)
        right = np.clip((centres + p * 0.3).astype(int), 0, axis_len - 1)
        if horizontal:
            err = (a[:, left] != a[:, centres]).any(2).mean() + (a[:, right] != a[:, centres]).any(2).mean()
        else:
            err = (a[left] != a[centres]).any(2).mean() + (a[right] != a[centres]).any(2).mean()
        if best is None or err < best[0] - 1e-4:
            best = (err, n)
    return best[1]


def to_native(frames, native_pixel):
    h, w = frames[0].shape[:2]
    if native_pixel == "auto":
        nx = detect_native_grid(frames[0], w, h, True)
        ny = detect_native_grid(frames[0], h, w, False)
    else:
        nx, ny = round(w / native_pixel), round(h / native_pixel)
    xs = (w / nx * np.arange(nx) + w / nx / 2).astype(int)
    ys = (h / ny * np.arange(ny) + h / ny / 2).astype(int)
    print(f"    native pixel grid: {nx} x {ny} (from {w} x {h})")
    return [f[ys][:, xs].copy() for f in frames]


def reduce_colours(frames, n):
    sample = Image.fromarray(np.vstack([f[:, :, :3] for f in frames[:: max(1, len(frames) // 8)]]))
    pal = sample.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    out = []
    for f in frames:
        rgb = np.array(Image.fromarray(f[:, :, :3]).quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB"))
        out.append(np.dstack([rgb, f[:, :, 3]]))
    return out


def rgb565(f):
    return ((f[:, :, 0].astype(np.uint32) & 0xF8) << 8) | ((f[:, :, 1].astype(np.uint32) & 0xFC) << 3) | (f[:, :, 2].astype(np.uint32) >> 3)


def placement(w, h, s256, offx, offy):
    ws, hs = (w * s256 + 255) // 256, (h * s256 + 255) // 256
    return (SCREEN - ws) // 2 + offx, (SCREEN - hs) // 2 + offy


def mask_to_circle(frames, s256, offx, offy):
    h, w = frames[0].shape[:2]
    x0, y0 = placement(w, h, s256, offx, offy)
    yy, xx = np.mgrid[0:h, 0:w]
    outside = np.hypot(x0 + (xx + 0.5) * s256 / 256 - 120, y0 + (yy + 0.5) * s256 / 256 - 120) > VISIBLE_R
    for f in frames:
        f[outside, 3] = 0
    return frames


def prepare_layer(spec):
    print(f"  {spec['file']}")
    frames, delays = load(spec["file"])
    if spec.get("native_pixel"):
        frames = to_native(frames, spec["native_pixel"])
    if spec.get("crop"):
        x, y, cw, ch = spec["crop"]
        frames = [f[y:y + ch, x:x + cw].copy() for f in frames]
    step = int(spec.get("frame_step", 1))
    if step > 1:
        frames, delays = frames[::step], [d * step for d in delays[::step]]
    ncol = min(int(spec.get("colors", MAX_COLOURS)), MAX_COLOURS)
    if len(np.unique(np.concatenate([rgb565(f)[f[:, :, 3] >= 128] for f in frames]))) > ncol:
        frames = reduce_colours(frames, ncol)
    h, w = frames[0].shape[:2]
    offx, offy = spec.get("offset", [0, 0])
    s256 = round(float(spec.get("scale", 1)) * 256)
    frames = mask_to_circle(frames, s256, offx, offy)
    print(f"    {len(frames)} frames, {w}x{h}, scale {s256 / 256:.2f}x, offset ({offx},{offy})")
    return frames, delays, s256, offx, offy


def encode(frames):
    h, w = frames[0].shape[:2]
    pal, lut, idx = [0], {}, []
    for f in frames:
        c, vis = rgb565(f), f[:, :, 3] >= 128
        for v in np.unique(c[vis]):
            if int(v) not in lut:
                lut[int(v)] = len(pal)
                pal.append(int(v))
        o = np.zeros((h, w), np.uint8)
        if vis.any():
            keys = np.array(sorted(lut), np.uint32)
            vals = np.array([lut[k] for k in sorted(lut)], np.uint8)
            o[vis] = vals[np.searchsorted(keys, c[vis])]
        idx.append(o)
    assert len(pal) <= MAX_COLOURS + 1, f"too many colours ({len(pal) - 1})"
    data, offs = bytearray(), []
    for k, f in enumerate(idx):
        offs.append(len(data))
        flat = f.flatten().astype(np.int16)
        if k > 0:
            flat = np.where(flat == idx[k - 1].flatten(), SKIP, flat)
        i = 0
        while i < len(flat):
            v, n = flat[i], 1
            while i + n < len(flat) and flat[i + n] == v and n < 255:
                n += 1
            data += bytes([n, int(v)])
            i += n
    offs.append(len(data))
    cur = np.zeros(w * h, np.uint8)            # decode again exactly like the firmware does
    for k, f in enumerate(idx):
        d, i = data[offs[k]:offs[k + 1]], 0
        for j in range(0, len(d), 2):
            if d[j + 1] != SKIP:
                cur[i:i + d[j]] = d[j + 1]
            i += d[j]
        assert i == w * h and np.array_equal(cur.reshape(h, w), f), f"round-trip failed on frame {k}"
    return pal, offs, data


def c_ident(s):
    return "".join(ch if ch.isalnum() else "_" for ch in s.lower()).strip("_")


def hex565(colour):
    colour = colour.lstrip("#")
    r, g, b = int(colour[0:2], 16), int(colour[2:4], 16), int(colour[4:6], 16)
    return f"0x{((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3):04X}"


HEADER = """#pragma once
// Generated by tools/gif2keychain.py - do not edit by hand.
#include <stdint.h>

// RLE frames: pairs of [count, value]. value 0 = transparent, 255 = keep previous frame's pixel,
// anything else = palette index.
struct Sprite {
  uint16_t w, h, frames;
  uint16_t scale256;   // size on screen = pixels * scale256 / 256 (256 = 1x)
  int8_t offX, offY;
  const uint16_t *palette;
  const uint16_t *delay;
  const uint32_t *offset;
  const uint8_t *rle;
};

// A "show" is up to two layers: back (may be nullptr) and front, plus the edge ring colours.
struct Show {
  const char *name;
  const Sprite *back;
  const Sprite *front;
  uint16_t ringIn, ringOut;
};

"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("config")
    ap.add_argument("-o", "--output", default="firmware/PokemonKeychain/sprites.h")
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    out, shows, sizes, total = [HEADER], [], {"front": 1, "back": 1}, 0
    for show in cfg["shows"]:
        print(f"{show['name']}:")
        refs = {}
        for role in ("back", "front"):
            spec = show.get(role)
            if not spec:
                refs[role] = "nullptr"
                continue
            name = c_ident(f"{show['name']}_{role}")
            frames, delays, s256, ox, oy = prepare_layer(spec)
            assert -128 <= ox <= 127 and -128 <= oy <= 127, "offset out of range"
            pal, offs, data = encode(frames)
            h, w = frames[0].shape[:2]
            sizes[role] = max(sizes[role], w * h)
            total += len(data)
            rows = ",\n  ".join(", ".join(str(b) for b in data[i:i + 32]) for i in range(0, len(data), 32))
            out.append(f"// {name}: {spec['file']} - {len(frames)} frames, {w}x{h}, {len(pal) - 1} colours, {len(data)} bytes\n"
                       f"const uint16_t {name}_palette[] = {{{', '.join(f'0x{c:04X}' for c in pal)}}};\n"
                       f"const uint16_t {name}_delay[] = {{{', '.join(map(str, delays))}}};\n"
                       f"const uint32_t {name}_offset[] = {{{', '.join(map(str, offs))}}};\n"
                       f"const uint8_t {name}_rle[] = {{\n  {rows}\n}};\n"
                       f"const Sprite {name} = {{{w}, {h}, {len(frames)}, {s256}, {ox}, {oy}, "
                       f"{name}_palette, {name}_delay, {name}_offset, {name}_rle}};\n\n")
            refs[role] = "&" + name
        ring = show.get("ring", ["#FFA400", "#A50000"])
        shows.append(f'  {{"{show["name"]}", {refs["back"]}, {refs["front"]}, {hex565(ring[0])}, {hex565(ring[1])}}},')
    out.append("const Show SHOWS[] = {\n" + "\n".join(shows) + "\n};\n")
    out.append(f"const int SHOW_COUNT = {len(shows)};\n#define MAX_FRONT_PIXELS {sizes['front']}\n#define MAX_BACK_PIXELS {sizes['back']}\n")
    open(args.output, "w").write("".join(out))
    print(f"wrote {args.output}: {len(shows)} shows, {total / 1024:.0f} KB of frames")


if __name__ == "__main__":
    main()
