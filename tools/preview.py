#!/usr/bin/env python3
"""
preview.py - see what the keychain will show, without the hardware.

    python tools/preview.py firmware/PokemonKeychain/sprites.h -o media/

Reads the generated sprites.h and renders one animated GIF per show, using the same
layer order, scaling, frame timing and ring colours as the firmware.
"""
import argparse, os, re
import numpy as np
from PIL import Image

BG = 0x0861


def arr(src, name):
    body = re.search(r"const \w+ " + name + r"\[\] = \{(.*?)\};", src, re.S).group(1)
    return np.array([int(v, 0) for v in body.replace("\n", "").split(",")])


def load(path):
    src = open(path).read()
    sprites = {}
    for m in re.finditer(r"const Sprite (\w+) = \{(\d+), (\d+), (\d+), (\d+), (-?\d+), (-?\d+),", src):
        n = m.group(1)
        w, h, frames, s, ox, oy = map(int, m.groups()[1:])
        ws, hs = (w * s + 255) >> 8, (h * s + 255) >> 8
        sprites[n] = dict(w=w, h=h, n=frames, s=s, x=(240 - ws) // 2 + ox, y=(240 - hs) // 2 + oy,
                          pal=arr(src, n + "_palette"), off=arr(src, n + "_offset"),
                          rle=arr(src, n + "_rle"), delay=arr(src, n + "_delay"))
    shows = [(name, None if back == "nullptr" else back.lstrip("&"), front, int(ri, 16), int(ro, 16))
             for name, back, front, ri, ro in
             re.findall(r'\{"([^"]+)", (&?\w+|nullptr), &(\w+), (0x\w+), (0x\w+)\}', src)]
    return sprites, shows


def rgb(c):
    return np.stack([((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31], -1).astype(np.uint8)


def decode(layer):
    s, f = layer["s"], layer["frame"]
    d, i = s["rle"][s["off"][f]:s["off"][f + 1]], 0
    for j in range(0, len(d), 2):
        if d[j + 1] != 255:
            layer["cur"][i:i + d[j]] = d[j + 1]
        i += d[j]


def render(show, sprites, ms, step=20):
    name, back, front, ring_in, ring_out = show
    yy, xx = np.mgrid[0:240, 0:240]
    d2 = (xx - 120) ** 2 + (yy - 120) ** 2
    bg = np.full((240, 240), BG)
    bg[(d2 >= 112 ** 2) & (d2 < 116 ** 2)] = ring_in
    bg[(d2 >= 116 ** 2) & (d2 < 120 ** 2)] = ring_out
    layers = []
    for n in ([back] if back else []) + [front]:
        s = sprites[n]
        layer = dict(s=s, frame=0, cur=np.zeros(s["w"] * s["h"], int))
        decode(layer)
        layer["next"] = s["delay"][0]
        layers.append(layer)
    frames, t = [], 0
    while t < ms:
        for L in layers:
            while t >= L["next"]:
                L["frame"] = (L["frame"] + 1) % L["s"]["n"]
                decode(L)
                L["next"] += L["s"]["delay"][L["frame"]]
        screen = bg.copy()
        for L in layers:
            s = L["s"]
            fx = ((xx - s["x"]) << 8) // s["s"]
            fy = ((yy - s["y"]) << 8) // s["s"]
            ok = (xx >= s["x"]) & (yy >= s["y"]) & (fx < s["w"]) & (fy < s["h"])
            idx = np.zeros((240, 240), int)
            idx[ok] = L["cur"].reshape(s["h"], s["w"])[fy[ok], fx[ok]]
            screen = np.where(idx > 0, s["pal"][idx], screen)
        img = rgb(screen)
        img[d2 >= 120 ** 2] = (22, 24, 29)
        frames.append(Image.fromarray(img))
        t += step
    return frames


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sprites", nargs="?", default="firmware/PokemonKeychain/sprites.h")
    ap.add_argument("-o", "--outdir", default="media")
    ap.add_argument("--seconds", type=float, default=3)
    ap.add_argument("--zoom", type=int, default=2)
    args = ap.parse_args()
    sprites, shows = load(args.sprites)
    os.makedirs(args.outdir, exist_ok=True)
    for show in shows:
        frames = [f.resize((240 * args.zoom,) * 2, Image.NEAREST) for f in render(show, sprites, args.seconds * 1000)]
        path = os.path.join(args.outdir, "preview_" + re.sub(r"\W+", "_", show[0].lower()) + ".gif")
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=20, loop=0)
        print("wrote", path)


if __name__ == "__main__":
    main()
