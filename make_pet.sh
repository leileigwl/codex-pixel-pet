#!/usr/bin/env bash
# 一键把图片变成 Codex 像素桌宠
# 用法: ./make_pet.sh <图片> <名字> [slug]
#   例: ./make_pet.sh mycat.png 小灰 kitty
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"

IMG="$1"; NAME="$2"; SLUG="${3:-pet}"
if [ -z "$IMG" ] || [ -z "$NAME" ]; then
  echo "用法: ./make_pet.sh <图片路径> <宠物名> [slug]"
  echo "例:   ./make_pet.sh mycat.png 小灰 kitty"
  exit 1
fi

# 依赖检查
command -v python3 >/dev/null || { echo "需要 python3"; exit 1; }
python3 -c "import PIL" 2>/dev/null || { echo "安装 Pillow..."; python3 -m pip install --quiet pillow; }

# 生成（先输出到本地 ./out 预览）
python3 "$HERE/pixel_pet.py" --image "$IMG" --name "$NAME" --slug "$SLUG" --out "$HERE/out"

echo
echo "▶ 预览: 浏览器打开 $HERE/out/$SLUG/preview.html"
echo "▶ 装进 Codex: cp -r \"$HERE/out/$SLUG\" ~/.codex/pets/ 然后重启 Codex"
# macOS 自动打开预览
command -v open >/dev/null && open "$HERE/out/$SLUG/preview.html" 2>/dev/null || true
