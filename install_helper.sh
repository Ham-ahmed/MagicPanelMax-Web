#!/bin/bash
# تثبيت مساعد MagicPanelMax في /usr/script (المسار الثابت)
# شغّل مرة واحدة عبر Telnet

set -e
HELPER_DIR="/usr/script"
WEB_DIR="/usr/script/mpm_web"
HELPER_FILE="$HELPER_DIR/mpm_helper.py"
PORT=8765

echo "========================================"
echo "  تثبيت MagicPanelMax Helper"
echo "  المسار: /usr/script/mpm_helper.py"
echo "========================================"

mkdir -p "$HELPER_DIR" "$WEB_DIR"

# البحث عن الملفات (ليس التشغيل من /tmp كمسار دائم)
SRC=""
for d in "$(cd "$(dirname "$0")" 2>/dev/null && pwd)" /tmp /home /media/hdd /media/usb; do
  [ -z "$d" ] && continue
  if [ -f "$d/mpm_helper.py" ]; then
    SRC="$d"
    break
  fi
done

if [ -z "$SRC" ]; then
  echo "[!] لم يُعثر على mpm_helper.py"
  echo "    ضع الملفات في /tmp مؤقتاً ثم أعد التشغيل"
  echo "    النهائي سيكون دائماً في /usr/script/"
  exit 1
fi

echo "[*] المصدر المؤقت: $SRC"
cp -f "$SRC/mpm_helper.py" "$HELPER_FILE"
chmod 755 "$HELPER_FILE"
echo "[OK] → $HELPER_FILE"

if [ -f "$SRC/index.html" ]; then
  cp -f "$SRC/index.html" "$WEB_DIR/index.html"
  echo "[OK] → $WEB_DIR/index.html"
fi

# إيقاف أي نسخة قديمة (من أي مسار)
pkill -f "mpm_helper.py" 2>/dev/null || true
sleep 1

# التشغيل من /usr/script فقط
nohup python "$HELPER_FILE" $PORT > /tmp/mpm_helper.log 2>&1 &
sleep 1

if pgrep -f "/usr/script/mpm_helper.py" >/dev/null || pgrep -f "mpm_helper.py" >/dev/null; then
  IP=$(ip route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
  [ -z "$IP" ] && IP=$(ifconfig eth0 2>/dev/null | awk '/inet /{print $2}' | head -1)
  [ -z "$IP" ] && IP="<IP_الرسيفر>"

  echo ""
  echo "========================================"
  echo "  المساعد يعمل من /usr/script"
  echo "========================================"
  echo "  الملف: $HELPER_FILE"
  echo "  من الموبايل: http://$IP:$PORT/"
  echo ""
  echo "  للإقلاع التلقائي أضف في /etc/rc.local:"
  echo "    python /usr/script/mpm_helper.py $PORT &"
  echo ""
else
  echo "[ERROR] فشل التشغيل — /tmp/mpm_helper.log:"
  cat /tmp/mpm_helper.log 2>/dev/null || true
  exit 1
fi
