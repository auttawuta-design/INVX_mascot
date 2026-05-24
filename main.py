import os
import httpx
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mascot Pose Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Models ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    pose_description: str
    style_reference_base64: Optional[str] = None

class TaskStatusRequest(BaseModel):
    task_id: str

# ── Helpers ─────────────────────────────────────────────────────────────────

async def build_prompt_with_claude(pose_description: str) -> str:
    """แปลงคำอธิบายท่าทาง (ไทย/อังกฤษ) เป็น prompt ภาษาอังกฤษสำหรับ Freepik"""
    if not ANTHROPIC_API_KEY:
        # fallback: ส่ง description ตรงๆ ถ้าไม่มี Anthropic key
        return f"A mascot character {pose_description}, cartoon illustration style, clean background, high quality"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages": [{
                    "role": "user",
                    "content": (
                        "You are a prompt engineer for AI image generation. "
                        "Convert this pose/action description into a concise English image generation prompt for a mascot character illustration. "
                        "Keep it under 60 words. Include: the pose/action, cartoon illustration style, clean white background, high quality. "
                        "Return only the prompt, nothing else.\n\n"
                        f"Description: {pose_description}"
                    )
                }]
            }
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


async def create_freepik_task(prompt: str, style_reference_base64: Optional[str]) -> str:
    """สร้าง image generation task บน Freepik Mystic API"""
    if not FREEPIK_API_KEY:
        raise HTTPException(status_code=500, detail="FREEPIK_API_KEY ยังไม่ได้ตั้งค่า")

    body = {
        "prompt": prompt,
        "filter_nsfw": True,
        "aspect_ratio": "square_1_1",
        "resolution": "2k",
    }
    if style_reference_base64:
        body["style_reference"] = style_reference_base64
        body["adherence"] = 60

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.freepik.com/v1/ai/mystic",
            headers={
                "x-freepik-api-key": FREEPIK_API_KEY,
                "content-type": "application/json",
            },
            json=body
        )
        if not resp.is_success:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return data["data"]["task_id"]


async def poll_freepik_task(task_id: str, max_tries: int = 30) -> list:
    """Poll จนกว่า task จะเสร็จ แล้วคืนรายการภาพ"""
    if not FREEPIK_API_KEY:
        raise HTTPException(status_code=500, detail="FREEPIK_API_KEY ยังไม่ได้ตั้งค่า")

    async with httpx.AsyncClient(timeout=10) as client:
        for _ in range(max_tries):
            await asyncio.sleep(3)
            resp = await client.get(
                f"https://api.freepik.com/v1/ai/mystic/{task_id}",
                headers={"x-freepik-api-key": FREEPIK_API_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["data"]["status"]
            if status == "COMPLETED":
                return data["data"].get("generated", [])
            if status == "FAILED":
                raise HTTPException(status_code=500, detail="Freepik task failed")

    raise HTTPException(status_code=504, detail="หมดเวลารอ กรุณาลองใหม่")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "freepik_key_set": bool(FREEPIK_API_KEY)}


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """รับคำอธิบายท่าทาง → แปลง prompt → เจนภาพ → คืน URL ภาพ"""
    eng_prompt = await build_prompt_with_claude(req.pose_description)
    task_id = await create_freepik_task(eng_prompt, req.style_reference_base64)
    images = await poll_freepik_task(task_id)

    if not images:
        raise HTTPException(status_code=500, detail="ไม่ได้รับภาพจาก Freepik")

    return {
        "prompt_used": eng_prompt,
        "images": images,
    }


# ── Serve frontend ────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
