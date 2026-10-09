# MagicPanelMax Web + Install Helper

نسخة ويب من MagicPanelMax مع مساعد تثبيت يعمل على الرسيفر (Enigma2).

## الملفات

| الملف | الوصف |
|--------|--------|
| `index.html` | صفحة الكتالوج (تعمل من المتصفح / الموبايل) |
| `mpm_helper.py` | مساعد التثبيت على الرسيفر (بورت 8765) |
| `install_helper.sh` | سكربت تثبيت المساعد تلقائياً |

## التثبيت السريع على الرسيفر

```bash
cd /tmp
wget -q https://raw.githubusercontent.com/USER/REPO/main/mpm_helper.py
wget -q https://raw.githubusercontent.com/USER/REPO/main/index.html
wget -q https://raw.githubusercontent.com/USER/REPO/main/install_helper.sh
chmod +x install_helper.sh
sh install_helper.sh
```

ثم من الموبايل (نفس الواي فاي):

```
http://IP_الرسيفر:8765/
```

## ملاحظة أمنية

- المساعد يعمل **بدون مصادقة** على الشبكة المحلية فقط.
- **لا** تفتح البورت 8765 على الإنترنت (Port Forward).
- استخدمه داخل شبكتك المنزلية فقط.

## الترخيص

للاستخدام الشخصي. الملفات مقدمة كما هي.
