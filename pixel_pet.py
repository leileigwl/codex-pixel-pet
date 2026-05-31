#!/usr/bin/env python3
"""
模板换肤：任意图 → 提取配色 → 刷到标准像素猫模板 → 渲染。
复古粗像素：低分辨率手绘像素图，整数倍最近邻放大，保持硬边。

第一阶段只验证「底图 + 换肤」效果，动画后续加。
"""
from PIL import Image

# ---- 像素调色板角色 ----
# . 透明  X 描边  F 主毛色  D 暗毛/条纹  B 浅色肚皮  P 耳内粉  E 眼  N 鼻  H 高光
LEGEND = set(".XFDBPENH")

# ---- 正面端坐的像素猫模板（每字符 = 1 像素）----
CAT = [
    "....XX..........XX....",
    "...XFFX........XFFX...",
    "...XFPFX......XFPFX...",
    "..XFFPFXX....XXFPFFX..",
    "..XFFFFFXXXXXXFFFFFX..",
    "..XFFFFFFFFFFFFFFFFX..",
    ".XFFFFFFFFFFFFFFFFFFX.",
    ".XFFDFFFFFFFFFFFFDFFX.",
    ".XFFDFFFFFFFFFFFFDFFX.",
    ".XFFFFEEHFFFFHEEFFFFX.",
    ".XFFFFEEFFFFFFEEFFFFX.",
    ".XFFFFFFFFNNFFFFFFFFX.",
    ".XFFFFFFFXNNXFFFFFFFX.",
    "..XFFFFFFFFFFFFFFFFX..",
    "..XFFFFFFFFFFFFFFFFX..",
    "...XFFFFFFFFFFFFFFX...",
    "...XFBBBBBBBBBBBBFX...",
    "..XFFBBBBBBBBBBBBFFX..",
    "..XFFBBBBBBBBBBBBFFX..",
    "..XFFBBBBBBBBBBBBFFXD.",
    "..XFFBBBBBBBBBBBBFFXDD",
    "..XFFXBBBBBBBBBBXFFXD.",
    "..XXX.XXX....XXX.XXX..",
]

W = max(len(r) for r in CAT)
H = len(CAT)


def _clamp(v):
    return max(0, min(255, int(v)))


def _shade(rgb, f):
    return tuple(_clamp(c * f) for c in rgb)


def _mix(a, b, t):
    return tuple(_clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def extract_palette(img: Image.Image) -> dict:
    """从图片提取换肤配色：主毛色 + 自动明暗，眼/鼻/耳用可爱默认值。"""
    im = img.convert("RGBA")
    px = [p for p in im.getdata() if p[3] > 128]
    if not px:
        px = list(im.convert("RGBA").getdata())
    # 主毛色 = 不太亮也不太暗的像素均值（去掉接近白/黑的极端）
    mids = [p for p in px if 40 < (p[0] + p[1] + p[2]) / 3 < 220]
    src = mids or px
    n = len(src)
    fur = (sum(p[0] for p in src) // n,
           sum(p[1] for p in src) // n,
           sum(p[2] for p in src) // n)
    return {
        "X": _shade(fur, 0.32),          # 描边：主色压暗
        "F": fur,                        # 主毛色
        "D": _shade(fur, 0.70),          # 条纹/暗部
        "B": _mix(fur, (255, 255, 255), 0.62),  # 浅肚皮
        "P": (245, 170, 175),            # 耳内粉
        "E": (40, 45, 60),               # 眼（深蓝灰，可爱）
        "N": (225, 140, 150),            # 鼻粉
        "H": (255, 255, 255),            # 高光
        ".": None,
    }


def render_lowres(palette: dict) -> Image.Image:
    """渲染 W×H 低分辨率底图（不放大）。"""
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bpx = base.load()
    for y, row in enumerate(CAT):
        for x, ch in enumerate(row):
            col = palette.get(ch)
            if col:
                bpx[x, y] = (col[0], col[1], col[2], 255)
    return base


# 眼睛像素坐标（用于眨眼/难过表情）
EYE_PX = [(x, y) for y, row in enumerate(CAT) for x, ch in enumerate(row) if ch in "EH"]


# ---------- 低分辨率变换工具（保持硬边像素）----------

def low_shift(im, dx, dy):
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (int(round(dx)), int(round(dy))))
    return out


def low_squash(im, sx, sy):
    """以底部中心为锚点缩放，画布保持 W×H。"""
    nw, nh = max(1, round(W * sx)), max(1, round(H * sy))
    s = im.resize((nw, nh), Image.NEAREST)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(s, ((W - nw) // 2, H - nh))
    return out


def low_tint(im, color, strength):
    overlay = Image.new("RGBA", im.size, (*color, 0))
    overlay.putalpha(im.split()[3].point(lambda a: int(a * strength)))
    return Image.alpha_composite(im, overlay)


def close_eyes(im, palette):
    """眨眼/难过：把眼睛像素涂成描边色（闭眼一道线）。"""
    im = im.copy()
    p = im.load()
    eye = palette["X"]
    for x, y in EYE_PX:
        p[x, y] = (*eye, 255)
    return im


def draw_heart(im, palette, cx, cy):
    im = im.copy()
    p = im.load()
    h = (235, 90, 110)
    pts = [(0, 0), (1, 0), (3, 0), (4, 0), (0, 1), (1, 1), (2, 1), (3, 1),
           (4, 1), (1, 2), (2, 2), (3, 2), (2, 3)]
    for dx, dy in pts:
        x, y = cx + dx, cy + dy
        if 0 <= x < W and 0 <= y < H:
            p[x, y] = (*h, 255)
    return im


# ---------- 8 状态动画（低分辨率层）+ 整图位移（放大后层）----------
import math

STATES = ["idle", "wave", "run", "failed", "review", "jump", "extra1", "extra2"]


def anim_frame(state, base_low, palette, i, n, scale, frame_w, frame_h):
    """返回放进单帧 (frame_w×frame_h) 的 RGBA。"""
    t = i / n
    s = math.sin(2 * math.pi * t)
    s2 = math.sin(4 * math.pi * t)
    low = base_low
    ox = oy = 0.0  # 放大后整图位移

    if state == "idle":
        if i in (4, 5):
            low = close_eyes(low, palette)          # 眨眼
        oy = [0, 0, -1, -1, 0, 0, 0, 0, 0][i] * scale
    elif state == "wave":
        ox = round(0.8 * s * scale)                 # 左右摆
        oy = -abs(round(0.4 * s * scale))
    elif state == "run":
        oy = -round(1.4 * abs(s2) * scale)          # 快速弹跳
        ox = round(0.5 * s * scale)
        if abs(s2) < 0.3:
            low = low_squash(low, 1.06, 0.92)       # 落地压扁
    elif state == "failed":
        low = close_eyes(low_tint(low, (210, 50, 50), 0.22), palette)
        ox = [-2, 2, -1, 2, -2, 1, -1, 2, 0][i] * (scale // 4 or 1)
        oy = 2 * scale // 3                         # 下垂
    elif state == "review":
        ox = round(0.9 * s * scale)                 # 缓慢左右看
        if i in (2, 6):
            low = close_eyes(low, palette)
    elif state == "jump":
        h = math.sin(math.pi * t)
        oy = -round(2.4 * h * scale)
        if i == 0 or i == n - 1:
            low = low_squash(low, 1.1, 0.86)        # 起跳/落地压扁
        elif 0.3 < t < 0.7:
            low = low_squash(low, 0.94, 1.08)       # 空中拉伸
    elif state == "extra1":
        sx = max(0.14, abs(math.cos(2 * math.pi * t)))
        low = low_squash(low, sx, 1.0)              # 横向压扁=转身
    elif state == "extra2":
        oy = -round(1.0 * abs(s) * scale)           # 开心蹦 + 爱心上浮
        hy = 1 - int(round(3 * t))
        low = draw_heart(low, palette, W - 4, hy)

    scaled = low.resize((W * scale, H * scale), Image.NEAREST)
    cell = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    x = (frame_w - scaled.width) // 2 + int(ox)
    y = (frame_h - scaled.height) - 8 + int(oy)     # 底部锚定，留 8px 地面
    cell.alpha_composite(scaled, (x, y))
    return cell


# ---------- 拼 Petdex 8×9 雪碧图 ----------
FRAME_W, FRAME_H, COLS = 192, 208, 9


def build_sheet(base_low, palette, scale=7):
    sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * len(STATES)), (0, 0, 0, 0))
    for row, state in enumerate(STATES):
        for col in range(COLS):
            fr = anim_frame(state, base_low, palette, col, COLS, scale, FRAME_W, FRAME_H)
            sheet.alpha_composite(fr, (col * FRAME_W, row * FRAME_H))
    return sheet


PREVIEW_HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>像素桌宠预览</title><style>
:root{--fw:192px;--fh:208px;--scale:1.6}*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;
justify-content:center;gap:24px;font-family:-apple-system,"PingFang SC",system-ui,sans-serif;
background:#1e2030;color:#cdd6f4}h1{font-size:18px;margin:0;opacity:.9}
.stage{width:calc(var(--fw)*var(--scale));height:calc(var(--fh)*var(--scale));
background-image:linear-gradient(45deg,#2a2c3f 25%,transparent 25%),
linear-gradient(-45deg,#2a2c3f 25%,transparent 25%),
linear-gradient(45deg,transparent 75%,#2a2c3f 75%),
linear-gradient(-45deg,transparent 75%,#2a2c3f 75%);background-size:24px 24px;
background-position:0 0,0 12px,12px -12px,-12px 0;border-radius:16px;
box-shadow:0 12px 40px rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;overflow:hidden}
.sprite{width:var(--fw);height:var(--fh);transform:scale(var(--scale));transform-origin:center;
background-repeat:no-repeat;image-rendering:pixelated}
.controls{display:flex;flex-wrap:wrap;gap:8px;max-width:540px;justify-content:center}
button{background:#313244;color:#cdd6f4;border:1px solid #45475a;padding:8px 14px;
border-radius:8px;cursor:pointer;font-size:13px}
button.active{background:#89b4fa;color:#1e1e2e;border-color:#89b4fa;font-weight:600}
.hint{font-size:12px;opacity:.6}</style></head><body>
<h1 id="title">🐾 像素桌宠预览</h1>
<div class="stage"><div class="sprite" id="sprite"></div></div>
<div class="controls" id="controls"></div>
<div class="hint">每行=一个状态，对应 Codex 的 AI 活动。点按钮切换。</div>
<script>
const FW=192,FH=208,COLS=9,SHEET="spritesheet.webp";
const STATES=[["idle","待机·呼吸"],["wave","打招呼"],["run","奔跑"],["failed","出错"],
["review","复核"],["jump","跳跃"],["extra1","转身"],["extra2","爱心"]];
const sprite=document.getElementById("sprite");
sprite.style.backgroundImage=`url("${SHEET}")`;let row=0,col=0;
function draw(){sprite.style.backgroundPosition=`${-col*FW}px ${-row*FH}px`}
setInterval(()=>{col=(col+1)%COLS;draw()},120);
const controls=document.getElementById("controls");
STATES.forEach(([id,label],i)=>{const b=document.createElement("button");
b.textContent=label;if(i===0)b.classList.add("active");
b.onclick=()=>{row=i;col=0;draw();[...controls.children].forEach(c=>c.classList.remove("active"));
b.classList.add("active");document.getElementById("title").textContent="🐾 "+label};
controls.appendChild(b)});draw();
</script></body></html>"""


def main():
    import argparse
    import json
    import re
    from pathlib import Path

    ap = argparse.ArgumentParser(description="模板换肤：单图 → 像素桌宠雪碧图")
    ap.add_argument("--image", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--slug")
    ap.add_argument("--desc", default="")
    ap.add_argument("--out", default=str(Path.home() / ".codex" / "pets"))
    ap.add_argument("--scale", type=int, default=7)
    args = ap.parse_args()

    slug = re.sub(r"[^a-z0-9]+", "-", (args.slug or args.name).lower()).strip("-") or "pet"
    out_dir = Path(args.out).expanduser() / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    pal = extract_palette(Image.open(Path(args.image).expanduser()))
    base_low = render_lowres(pal)
    sheet = build_sheet(base_low, pal, scale=args.scale)
    sheet.save(out_dir / "spritesheet.webp", "WEBP", lossless=True, quality=100)

    (out_dir / "pet.json").write_text(json.dumps({
        "id": slug, "displayName": args.name,
        "description": args.desc or f"{args.name}，一只像素小宠物。",
        "spritesheetPath": "spritesheet.webp",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "preview.html").write_text(PREVIEW_HTML, encoding="utf-8")

    print(f"✅ 像素桌宠生成: {out_dir}  主毛色 {pal['F']}")
    print(f"   雪碧图 {sheet.size}  (8×9=72 帧)")
    print(f"   预览: 浏览器打开 {out_dir / 'preview.html'}")
    print(f"   装进 Codex: 把整个 {slug}/ 目录放到 ~/.codex/pets/ 下")


if __name__ == "__main__":
    main()
