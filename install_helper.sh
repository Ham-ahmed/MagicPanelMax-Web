#!/bin/bash
# تثبيت مساعد MagicPanelMax + صفحة الويب على الرسيفر
# شغّل مرة واحدة عبر Telnet أو Terminal

set -e
HELPER_DIR="/usr/script"
WEB_DIR="/usr/script/mpm_web"
HELPER_FILE="$HELPER_DIR/mpm_helper.py"
PORT=8765

echo "========================================"
echo "  تثبيت MagicPanelMax Helper + Web"
echo "========================================"

mkdir -p "$HELPER_DIR" "$WEB_DIR"

# البحث عن الملفات
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
  echo "    ضع الملفات في /tmp ثم أعد التشغيل"
  exit 1
fi

echo "[*] المصدر: $SRC"
cp -f "$SRC/mpm_helper.py" "$HELPER_FILE"
chmod 755 "$HELPER_FILE"
echo "[OK] mpm_helper.py → $HELPER_FILE"

if [ -f "$SRC/index.html" ]; then
  cp -f "$SRC/index.html" "$WEB_DIR/index.html"
  echo "[OK] index.html → $WEB_DIR/"
else
  echo "[!] index.html غير موجود — ضعها في $WEB_DIR لاحقاً"
fi

# إيقاف النسخة القديمة
pkill -f "mpm_helper.py" 2>/dev/null || true
sleep 1

# تشغيل
nohup python "$HELPER_FILE" $PORT > /tmp/mpm_helper.log 2>&1 &
sleep 1

if pgrep -f "mpm_helper.py" >/dev/null; then
  IP=$(ip route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
  [ -z "$IP" ] && IP=$(ifconfig eth0 2>/dev/null | awk '/inet /{print $2}' | head -1)
  [ -z "$IP" ] && IP=$(ifconfig wlan0 2>/dev/null | awk '/inet /{print $2}' | head -1)
  [ -z "$IP" ] && IP="<IP_الرسيفر>"

  echo ""
  echo "========================================"
  echo "  المساعد يعمل بنجاح"
  echo "========================================"
  echo ""
  echo "  من الموبايل (نفس الواي فاي):"
  echo "    http://$IP:$PORT/"
  echo ""
  echo "  الحالة:"
  echo "    http://$IP:$PORT/status"
  echo ""
  echo "  للتشغيل عند الإقلاع — أضف في /etc/rc.local:"
  echo "    python $HELPER_FILE $PORT &"
  echo ""
else
  echo "[ERROR] فشل التشغيل — /tmp/mpm_helper.log:"
  cat /tmp/mpm_helper.log 2>/dev/null || true
  exit 1
fi
