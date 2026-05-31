# 🐾 Codex 像素桌宠生成器

把**任意一张动物/角色图片**，变成一只**复古像素风的桌面小宠物**，直接装进
**Codex / Claude Code**（Petdex 格式），会随 AI 工作状态切换动作。

> 原理：从你的图里**提取主配色**，刷到一套**标准像素宠物模板**上，
> 再套上一套**固定动作**（待机/招呼/奔跑/出错/复核/跳跃/转身/爱心），
> 拼成符合 Codex 规范的 `spritesheet.webp`。换任何图都能用同一套动作。

---

## 快速开始

```bash
# 只需要 Python3 + Pillow，无需联网、无需 AI
./make_pet.sh 你的图片.png 小灰 kitty
```

跑完会：
1. 在 `out/kitty/` 生成 `spritesheet.webp` + `pet.json` + `preview.html`
2. 自动打开浏览器预览（点按钮看 8 种动作）

手动调用：
```bash
python3 pixel_pet.py --image 你的图.png --name "小灰" --slug kitty --out out
```

| 参数 | 说明 |
|------|------|
| `--image` | 输入图片（任意格式；纯色/透明背景效果最好） |
| `--name`  | 宠物显示名 |
| `--slug`  | 目录名（英文） |
| `--desc`  | 描述（可选） |
| `--out`   | 输出父目录；**省略则直接装到 `~/.codex/pets/`** |
| `--scale` | 像素放大倍数（默认 7，越大越精细） |

---

## 装进 Codex

```bash
cp -r out/kitty ~/.codex/pets/      # 复制整个宠物目录
# 重启 Codex → Settings → Appearance → Pets → 选「小灰」
# 或在 Codex 输入框输入 /pet
```

生成的就是标准 **Petdex** 格式（`8×9=72 帧，192×208/帧`），
Codex / Claude Code / OpenCode / Gemini CLI 都认。

---

## 状态 → 动作对照（行=状态）

| 行 | 状态 | 动作 | Codex 何时触发 |
|----|------|------|----------------|
| 1 | idle | 呼吸·眨眼 | 待机 |
| 2 | wave | 摇摆招呼 | 等待输入 |
| 3 | run | 快速弹跳 | 正在生成代码 |
| 4 | failed | 泛红·难过 | 任务失败 |
| 5 | review | 左右张望 | 结果可复核 |
| 6 | jump | 跳跃 | 进度推进 |
| 7 | extra1 | 转身 | 备用 |
| 8 | extra2 | 蹦跶·爱心 | 备用 |

---

## 说明 / 限制

- **配色像、身形是模板**：出来的是「配色跟你的图一样的标准像素宠物」，
  不是原图的精确像素画像。换猫换狗换人，**身形目前都是同一套**（只换颜色）。
- 想要不同身形（狗/鸟/圆滚滚）→ 在 `pixel_pet.py` 里加新的像素模板（`CAT` 那种字符画）。
- 想要「就是这只动物本体」的像素版 → 需要接 AI 图像生成，本工具不含。

## 依赖

- Python 3.8+
- Pillow（`pip install pillow`）

MIT License · 格式参考 [crafter-station/petdex](https://github.com/crafter-station/petdex)
