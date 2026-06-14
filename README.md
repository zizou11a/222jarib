# وظيفتي | Wazifati
## منصة التوظيف الجزائرية

---

## 🚀 تشغيل المشروع محلياً

### 1. تثبيت Python
تأكد من وجود Python 3.10+ على جهازك.

### 2. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 3. تشغيل المشروع
```bash
python app.py
```

افتح المتصفح على: http://localhost:5000

**حساب المشرف:**
- البريد: admin@wazifati.dz
- كلمة المرور: admin2024

---

## ☁️ النشر على Render.com (مجاني)

### الخطوة 1 — إنشاء حساب
اذهب إلى https://render.com وسجّل حساباً مجانياً.

### الخطوة 2 — رفع الكود على GitHub
```bash
git init
git add .
git commit -m "وظيفتي - أول إصدار"
git remote add origin https://github.com/اسمك/wazifati.git
git push -u origin main
```

### الخطوة 3 — إنشاء قاعدة بيانات PostgreSQL
في Render Dashboard:
- New → PostgreSQL
- اختر الخطة المجانية (Free)
- انسخ رابط "Internal Database URL"

### الخطوة 4 — إنشاء Web Service
في Render Dashboard:
- New → Web Service
- اربطه بـ GitHub repo
- ضع هذه الإعدادات:
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`

### الخطوة 5 — متغيرات البيئة
في Environment Variables أضف:
```
SECRET_KEY = كلمة-سرية-طويلة-هنا
DATABASE_URL = (الرابط من الخطوة 3)
```

### الخطوة 6 — تهيئة قاعدة البيانات
في Render → Shell:
```bash
python -c "from app import create_tables; create_tables()"
```

✅ موقعك الآن يعمل!

---

## 📁 هيكل المشروع

```
wazifati/
├── app.py              ← الكود الرئيسي (Flask)
├── requirements.txt    ← المكتبات
├── Procfile            ← أمر التشغيل على Render
├── .env.example        ← مثال على المتغيرات
├── templates/          ← صفحات HTML
│   ├── base.html       ← القالب الأساسي (navbar, footer)
│   ├── index.html      ← الصفحة الرئيسية
│   ├── jobs.html       ← قائمة الوظائف
│   ├── job_detail.html ← تفاصيل الوظيفة
│   ├── login.html      ← تسجيل الدخول
│   ├── register.html   ← إنشاء حساب
│   ├── dashboard.html  ← لوحة الشركة
│   ├── applications.html ← الطلبات الواردة
│   ├── company_profile.html ← ملف الشركة
│   ├── admin.html      ← لوحة الإدارة
│   └── _job_card.html  ← بطاقة الوظيفة (مكوّن)
└── static/
    └── uploads/        ← ملفات CV المرفوعة
```

---

## 👥 أنواع المستخدمين

| الدور | ماذا يستطيع |
|-------|-------------|
| باحث عن عمل | البحث، التقديم، رفع CV |
| شركة | نشر وظائف، إدارة الطلبات، تعديل الملف |
| Admin | كل شيء + إدارة المستخدمين والوظائف |

---

## 🔒 الأمان
- كلمات المرور مشفرة بـ Werkzeug (bcrypt)
- حماية CSRF عبر Flask sessions
- التحقق من صلاحيات كل مستخدم
- تنظيف أسماء الملفات المرفوعة
