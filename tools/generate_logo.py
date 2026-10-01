#!/usr/bin/env python3
"""generate_logo.py — 生成 AKIA 应用图标（可复现的品牌资产）

设计说明
--------
主图标：冷瓷白渐变瓷砖 + 左上柔光 + 底部内阴影，形成三层纵深：
  1. 外部投影（浮起）
  2. 瓷砖本体（对角渐变 + 顶部高光 + 底部内阴影 + 边缘描边）
  3. 字标（品牌红 A / 藏青 KIA，带底部投影与竖向渐变）

冷瓷白而非纯白/浅灰：在应用的深色界面（#0d2847 splash / #1c1c24 对话框）
上有足够对比，同时保留字标原本的红/藏青品牌色。

产物（仓库内）：
  logo.png            1024×1024  主窗口图标 / splash
  assets/logo.png      256×256   Linux AppImage 图标
  assets/logo.ico      16–256    Windows 可执行文件 / 安装包图标

预演（不覆盖资产）：
  TEMP/logo_alt_dark.png        深海军蓝背景备选方案

用法: python tools/generate_logo.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
WORDMARK = ROOT / "assets" / "logo_wordmark.png"
MASTER = ROOT / "logo.png"
ICON_256 = ROOT / "assets" / "logo.png"
ICON_ICO = ROOT / "assets" / "logo.ico"
ALT_PREVIEW = ROOT / "TEMP" / "logo_alt_dark.png"

CANVAS = 1024
TILE_INSET = 62          # 瓷砖外沿留白（含外投影空间）
LETTERS_WIDTH_RATIO = 0.66
LETTERS_CENTER_Y = 0.500

# 品牌色（取自字标）
BRAND_RED_DARK = (118, 0, 0)
BRAND_NAVY_DARK = (42, 61, 116)
BRAND_RED_LIGHT = (224, 0, 0)
BRAND_BLUE_LIGHT = (79, 115, 220)


# ── 基础工具 ────────────────────────────────────────────────


def linear_gradient(size: int, c0, c1, angle_deg: float = 90.0) -> Image.Image:
    """角度渐变（angle_deg 指向 c1：0=向右，90=向下）。"""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    a = math.radians(angle_deg)
    t = xx * math.cos(a) + yy * math.sin(a)
    t = (t - t.min()) / max(t.max() - t.min(), 1e-6)
    c0a = np.array(c0, np.float32)
    c1a = np.array(c1, np.float32)
    arr = c0a[None, None, :] + (c1a - c0a)[None, None, :] * t[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def radial_mask(size: int, cx: float, cy: float, radius: float,
                power: float = 2.0) -> Image.Image:
    """径向衰减遮罩，中心 255 → 半径外 0。"""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - cx * size) ** 2 + (yy - cy * size) ** 2) / radius
    m = np.clip(1.0 - d, 0.0, 1.0) ** power
    return Image.fromarray((m * 255).astype(np.uint8), "L")


def vertical_mask(size: int, top: int, bottom: int,
                  power: float = 1.0) -> Image.Image:
    v = top + (bottom - top) * (np.linspace(0.0, 1.0, size) ** power)
    return Image.fromarray(
        np.tile(v[:, None], (1, size)).astype(np.uint8), "L")


def squircle_mask(size: int, inset: float, n: float = 4.6,
                  ss: int = 3) -> Image.Image:
    """超椭圆（squircle）遮罩，超采样后缩回以获得平滑边缘。"""
    s = size * ss
    r = s / 2 - inset * ss
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    x = (xx - s / 2) / r
    y = (yy - s / 2) / r
    inside = (np.abs(x) ** n + np.abs(y) ** n) <= 1.0
    m = Image.fromarray((inside * 255).astype(np.uint8), "L")
    return m.resize((size, size), Image.LANCZOS)


def color_layer(size: int, color, mask: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (*color, 0))
    layer.putalpha(mask)
    return layer


def scaled(mask: Image.Image, factor: float) -> Image.Image:
    """遮罩乘以比例（factor 0–1）。"""
    return mask.point(lambda v: int(v * factor))


def resize_rgba_premultiplied(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """按预乘 alpha 缩放，避免透明边缘出现黑边。"""
    arr = np.asarray(im).astype(np.float32) / 255.0
    alpha = arr[..., 3:4]
    pm = np.concatenate([arr[..., :3] * alpha, alpha], axis=2)
    pm_img = Image.fromarray((pm * 255.0 + 0.5).astype(np.uint8), "RGBA")
    pm_small = np.asarray(pm_img.resize(size, Image.LANCZOS)).astype(np.float32) / 255.0
    a_small = pm_small[..., 3:4]
    rgb = np.where(a_small > 1e-6, pm_small[..., :3] / np.maximum(a_small, 1e-6), 0.0)
    out = np.concatenate([np.clip(rgb, 0.0, 1.0), a_small], axis=2)
    return Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), "RGBA")


# ── 字标 ────────────────────────────────────────────────────


def load_wordmark_layers() -> tuple[Image.Image, Image.Image]:
    """把字标拆成 A（红）与 KIA（蓝）两张带 alpha 的图层。"""
    wm = Image.open(WORDMARK).convert("RGBA")
    wm = wm.crop(wm.getchannel("A").getbbox())
    arr = np.asarray(wm).astype(np.int16)
    alpha = arr[..., 3]
    red = (alpha > 40) & (arr[..., 0] > arr[..., 2] + 30)
    blue = (alpha > 40) & ~red
    a_alpha = Image.fromarray(np.where(red, alpha, 0).astype(np.uint8), "L")
    k_alpha = Image.fromarray(np.where(blue, alpha, 0).astype(np.uint8), "L")
    return a_alpha, k_alpha


def recolor_letters(size: int, a_alpha: Image.Image, k_alpha: Image.Image,
                    a_colors, k_colors) -> Image.Image:
    """按目标尺寸生成重着色的字标图层（A 与 KIA 各自渐变）。"""
    h = round(size * a_alpha.height / a_alpha.width)
    grad_a = linear_gradient(h, *a_colors, 90).resize((size, h), Image.LANCZOS)
    grad_k = linear_gradient(h, *k_colors, 90).resize((size, h), Image.LANCZOS)
    out = Image.new("RGBA", (size, h), (0, 0, 0, 0))
    for grad, mask in ((grad_a, a_alpha), (grad_k, k_alpha)):
        m = mask.resize((size, h), Image.LANCZOS)
        layer = grad.convert("RGBA")
        layer.putalpha(m)
        out = Image.alpha_composite(out, layer)
    return out


# ── 图标组装 ────────────────────────────────────────────────


def build_icon(dark: bool = True, with_shadow: bool = True) -> Image.Image:
    size = CANVAS
    mask = squircle_mask(size, TILE_INSET)

    # 1) 瓷砖底色：对角渐变 + 左上柔光 + 字标背光
    if dark:
        tile = linear_gradient(size, (60, 90, 158), (10, 16, 34), 125)
        tile = Image.composite(
            Image.new("RGB", (size, size), (96, 128, 208)),
            tile, scaled(radial_mask(size, 0.30, 0.12, 700, 2.2), 0.20))
        tile = Image.composite(
            Image.new("RGB", (size, size), BRAND_BLUE_LIGHT),
            tile, scaled(radial_mask(size, 0.50, 0.52, 420, 2.4), 0.36))
    else:
        tile = linear_gradient(size, (253, 254, 255), (203, 215, 236), 125)
        tile = Image.composite(
            Image.new("RGB", (size, size), (255, 255, 255)),
            tile, scaled(radial_mask(size, 0.30, 0.12, 700, 2.2), 0.55))
        tile = Image.composite(
            Image.new("RGB", (size, size), (176, 195, 226)),
            tile, scaled(radial_mask(size, 0.50, 0.92, 520, 2.6), 0.30))

    tile_rgba = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile_rgba.paste(tile, (0, 0), mask)

    # 2) 边缘立体：顶部高光 + 底部内阴影 + 底部内晕
    inner = squircle_mask(size, TILE_INSET + 3)
    rim = ImageChops.subtract(mask, inner).filter(ImageFilter.GaussianBlur(1.6))
    if dark:
        top_light = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        top_light.putalpha(scaled(
            ImageChops.multiply(rim, vertical_mask(size, 235, 30, 1.4)), 0.55))
        bottom_dark = Image.new("RGBA", (size, size), (4, 7, 15, 0))
        bottom_dark.putalpha(scaled(
            ImageChops.multiply(rim, vertical_mask(size, 0, 255, 1.2)), 0.65))
    else:
        top_light = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        top_light.putalpha(scaled(
            ImageChops.multiply(rim, vertical_mask(size, 255, 90, 1.3)), 0.85))
        bottom_dark = Image.new("RGBA", (size, size), (120, 140, 175, 0))
        bottom_dark.putalpha(scaled(
            ImageChops.multiply(rim, vertical_mask(size, 0, 255, 1.2)), 0.55))

    deeper = ImageChops.subtract(
        squircle_mask(size, TILE_INSET + 6),
        squircle_mask(size, TILE_INSET + 42)).filter(ImageFilter.GaussianBlur(16))
    inner_shade = Image.new("RGBA", (size, size), (5, 9, 20, 0))
    inner_shade.putalpha(scaled(
        ImageChops.multiply(deeper, vertical_mask(size, 0, 255, 2.1)),
        0.38 if dark else 0.22))

    # 深色背景下用一圈极弱的环境光勾勒轮廓
    edge_light = None
    if dark:
        outer = squircle_mask(size, TILE_INSET - 2).filter(
            ImageFilter.GaussianBlur(10))
        ring = scaled(ImageChops.subtract(outer, mask), 0.10)
        edge_light = color_layer(size, (210, 225, 255), ring)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for layer in (edge_light, tile_rgba, inner_shade, top_light, bottom_dark):
        if layer is None:
            continue
        canvas = Image.alpha_composite(canvas, layer)

    # 3) 字标：底部投影 + 渐变字形
    a_alpha, k_alpha = load_wordmark_layers()
    letters_w = round(size * LETTERS_WIDTH_RATIO)
    if dark:
        letters = recolor_letters(
            letters_w, a_alpha, k_alpha,
            ((255, 92, 74), (198, 14, 30)),
            ((255, 255, 255), (185, 205, 255)))
    else:
        letters = recolor_letters(
            letters_w, a_alpha, k_alpha,
            ((150, 10, 10), BRAND_RED_DARK),
            ((58, 82, 152), BRAND_NAVY_DARK))

    letters_x = (size - letters.width) // 2
    letters_y = round(size * LETTERS_CENTER_Y - letters.height / 2)
    letter_alpha = letters.getchannel("A")

    letter_shadow_alpha = Image.new("L", (size, size), 0)
    letter_shadow_alpha.paste(letter_alpha, (letters_x, letters_y + 14))
    letter_shadow_alpha = letter_shadow_alpha.filter(ImageFilter.GaussianBlur(16))
    letter_shadow = Image.new("RGBA", (size, size), (3, 6, 14, 0))
    letter_shadow.putalpha(scaled(letter_shadow_alpha, 0.50 if dark else 0.30))
    canvas = Image.alpha_composite(canvas, letter_shadow)
    canvas.alpha_composite(letters, (letters_x, letters_y))

    # 4) 外部投影（浮起感；仅用于 PNG 版本）
    if not with_shadow:
        return canvas
    shadow_mask = Image.new("L", (size, size), 0)
    shadow_mask.paste(mask.filter(ImageFilter.GaussianBlur(26)), (0, 26))
    shadow = Image.new("RGBA", (size, size), (8, 12, 24, 0))
    shadow.putalpha(scaled(shadow_mask, 0.42 if dark else 0.30))
    return Image.alpha_composite(shadow, canvas)


def main() -> int:
    if not WORDMARK.exists():
        print(f"字标文件缺失: {WORDMARK}", file=sys.stderr)
        return 1

    icon = build_icon(dark=False, with_shadow=True)
    icon.save(MASTER)
    print(f"[logo] {MASTER.relative_to(ROOT)}  {icon.width}×{icon.height}")

    icon_256 = resize_rgba_premultiplied(icon, (256, 256))
    icon_256.save(ICON_256)
    print(f"[logo] {ICON_256.relative_to(ROOT)}  256×256")

    flat = build_icon(dark=False, with_shadow=False)
    flat_256 = resize_rgba_premultiplied(flat, (256, 256))
    flat_256.save(ICON_ICO, format="ICO",
                  sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                         (64, 64), (128, 128), (256, 256)])
    print(f"[logo] {ICON_ICO.relative_to(ROOT)}  16–256")

    ALT_PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    alt = build_icon(dark=True, with_shadow=True)
    alt.save(ALT_PREVIEW)
    print(f"[alt ] {ALT_PREVIEW.relative_to(ROOT)}（深蓝备选预演，未启用）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
