# PDF Analyzer - Backend

سيرفر الواجهة الخلفية (FastAPI Backend) لمحلل ومستكشف الأوراق العلمية واستخراج المراجع الأكاديمية وإثرائها.

---

## 📁 هيكل المجلد

```
backend/
├── main.py             # نقطة دخول السيرفر وتوفير الـ Endpoints مع دعم CORS الكامل
├── run.py              # سكربت تشغيل السيرفر بأمر واحد
├── requirements.txt    # قائمة المكتبات والحزم المطلوبة
├── enrichment/         # محركات البحث والإثراء والمطابقة (OpenAlex, Google Scholar, DOI, Crossref)
├── data/               # قاعدة البيانات ومجلدات التخزين المؤقت والمشاريع المستخرجة
├── tests/              # جميع اختبارات الوحدة والتكامل
└── README.md           # هذا الدليل
```

---

## 🚀 كيفية تشغيل الباك إند

### 1. تثبيت الحزم المطلوبة (في بيئة افتراضية virtualenv):
```bash
pip install -r requirements.txt
```

### 2. تشغيل السيرفر:
```bash
python run.py
```
أو عبر `uvicorn` مباشرة:
```bash
uvicorn main:app --reload --port 8080
```

### 3. توثيق الـ API (Swagger UI):
- بعد تشغيل السيرفر، يمكنك استعراض كافة الـ APIs وتجربتها مباشرة عبر الرابط:
  [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

### 4. تشغيل الاختبارات:
```bash
pytest tests/
```
