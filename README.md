# 🎨 Mascot Pose Generator

AI Agent สำหรับเจนภาพ mascot ท่าทางต่างๆ จากภาพต้นฉบับ
ใช้ Freepik Mystic API + Claude สำหรับแปล prompt

---

## 📁 โครงสร้างไฟล์

```
mascot-agent/
├── main.py            ← FastAPI backend
├── static/
│   └── index.html     ← หน้า Chat UI
├── requirements.txt
├── Procfile           ← สำหรับ Railway
└── README.md
```

---

## 🚀 วิธี Deploy บน Railway (ง่ายมาก!)

### ขั้นตอนที่ 1 — อัปโหลดโค้ดขึ้น GitHub
1. ไปที่ [github.com](https://github.com) → สร้าง repo ใหม่ ชื่อ `mascot-agent`
2. อัปโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้ขึ้น repo

### ขั้นตอนที่ 2 — สร้าง Project บน Railway
1. ไปที่ [railway.app](https://railway.app) → Login ด้วย GitHub
2. กด **"New Project"** → **"Deploy from GitHub repo"**
3. เลือก repo `mascot-agent`
4. Railway จะ detect Python อัตโนมัติและ deploy ให้เลย

### ขั้นตอนที่ 3 — ตั้งค่า Environment Variables
ใน Railway Dashboard → Settings → Variables → เพิ่ม:

| Variable | Value |
|----------|-------|
| `FREEPIK_API_KEY` | API Key จาก freepik.com/developers |
| `ANTHROPIC_API_KEY` | API Key จาก console.anthropic.com (optional) |

### ขั้นตอนที่ 4 — รับ URL
- Railway จะให้ URL เช่น `https://mascot-agent-production.up.railway.app`
- แชร์ URL นี้ให้ทุกคนในบริษัทใช้ได้เลย! 🎉

---

## 💻 รันบนเครื่องตัวเอง (สำหรับ dev)

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# ตั้งค่า env
export FREEPIK_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here  # optional

# รัน server
uvicorn main:app --reload --port 8000
```

เปิด browser ไปที่ http://localhost:8000

---

## 🔧 API Endpoints

| Method | Path | คำอธิบาย |
|--------|------|---------|
| GET | `/` | หน้า Chat UI |
| GET | `/health` | ตรวจสอบสถานะ server |
| POST | `/api/generate` | เจนภาพจากคำอธิบายท่าทาง |

### POST /api/generate

Request body:
```json
{
  "pose_description": "กำลังวิ่ง",
  "style_reference_base64": "base64_string_ของภาพต้นฉบับ"
}
```

Response:
```json
{
  "prompt_used": "A mascot character running at full speed...",
  "images": [{ "url": "https://..." }]
}
```
