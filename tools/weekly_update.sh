#!/bin/bash
# 每週六 08:00（澳門時間）整站更新：同步 → 建站 → 檢查 → 提交推送 → 等 GitHub Pages → 核對線上
# 用法：bash tools/weekly_update.sh            （在 badminton 儲存庫根目錄）
#       bash tools/weekly_update.sh --dry-run  （只建站和檢查，不提交、不推送）
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
DATE="$(TZ=Asia/Macau date +%F)"
SITE="https://winglao.github.io/badminton"
LOGDIR="${BADMINTON_SRC:-$HOME/Desktop/Badminton/網站資料}/網站維護/自動更新紀錄"   # 紀錄留在本機資料夾，不進網站
mkdir -p "$LOGDIR"
LOG="$LOGDIR/更新_${DATE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== $(TZ=Asia/Macau date '+%F %T') 開始每週更新 =="

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "停止：儲存庫有尚未提交的修改，為免覆蓋別人的工作，先不自動更新。"
  git status --short
  exit 2
fi

echo "-- 1. 同步遠端"
git pull --rebase origin main

echo "-- 2. 建站"
python3 tools/build_site.py --date "$DATE"

echo "-- 3. 檢查連結"
python3 tools/check_site.py
git diff --check

if [ "${1:-}" = "--dry-run" ]; then
  echo "試跑完成（沒有提交）。"; git status --short; exit 0
fi

echo "-- 4. 提交與推送"
git add index.html news learn technology research skills updates tools assets
if git diff --cached --quiet; then
  echo "沒有任何變動，不需要發佈。"; exit 0
fi
git commit -q -m "Weekly site update ${DATE}"
git push origin main
HEAD_SHA="$(git rev-parse HEAD)"

echo "-- 5. 等待 GitHub Pages（最多 15 分鐘）"
STATUS=""
for i in $(seq 1 60); do
  read -r STATUS COMMIT < <(gh api repos/WingLao/badminton/pages/builds/latest --jq '.status + " " + .commit' 2>/dev/null || echo "unknown none")
  if [ "$COMMIT" = "$HEAD_SHA" ] && [ "$STATUS" = "built" ]; then break; fi
  if [ "$COMMIT" = "$HEAD_SHA" ] && [ "$STATUS" = "errored" ]; then echo "GitHub Pages 發佈失敗"; exit 3; fi
  sleep 15
done
[ "$STATUS" = "built" ] || { echo "等待逾時：GitHub Pages 狀態 $STATUS"; exit 4; }

echo "-- 6. 核對線上版本"
sleep 20
for p in "" "updates/" "learn/" "technology/" "research/" "skills/"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "$SITE/$p?v=$HEAD_SHA")"
  echo "$code $SITE/$p"; [ "$code" = "200" ] || { echo "線上網址異常"; exit 5; }
done
curl -s "$SITE/updates/?v=$HEAD_SHA" | grep -q "$(TZ=Asia/Macau date '+%Y 年 %-m 月 %-d 日')" \
  && echo "線上更新紀錄已顯示 ${DATE}" || { echo "線上更新紀錄還沒顯示今天日期"; exit 6; }
echo "== 完成：$SITE/ =="
