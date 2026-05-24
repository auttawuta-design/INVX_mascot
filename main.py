import os
import base64
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

class GenerateRequest(BaseModel):
    pose_description: str
    style_reference_base64: Optional[str] = None
    style_reference_mime: Optional[str] = "image/png"

def build_prompt(pose_description: str) -> str:
    return pose_description

async def create_nano_banana_task(prompt: str, style_reference_base64: Optional[str], mime_type: str = "image/png") -> str:
    if not FREEPIK_API_KEY:
        raise HTTPException(status_code=500, detail="FREEPIK_API_KEY ยังไม่ได้ตั้งค่า")

    body = {
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "resolution": "1K",
    }

    if style_reference_base64:
        # API ต้องการ data URI format
        data_uri = f"data:{mime_type};base64,{style_reference_base64}"
        body["reference_images"] = [
            {
                "image": data_uri,
                "text": "This is the mascot character. Keep the same character design, colors, and style. Only change the pose/action.",
                "mime_type": mime_type,
            }
        ]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.freepik.com/v1/ai/text-to-image/nano-banana-pro",
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

async def poll_nano_banana_task(task_id: str, max_tries: int = 30) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        for _ in range(max_tries):
            await asyncio.sleep(3)
            resp = await client.get(
                f"https://api.freepik.com/v1/ai/text-to-image/nano-banana-pro/{task_id}",
                headers={"x-freepik-api-key": FREEPIK_API_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["data"]["status"]
            if status == "COMPLETED":
                return data["data"].get("generated", [])
            if status == "FAILED":
                raise HTTPException(status_code=500, detail="Task failed")
    raise HTTPException(status_code=504, detail="หมดเวลารอ กรุณาลองใหม่")

@app.get("/health")
async def health():
    return {"status": "ok", "freepik_key_set": bool(FREEPIK_API_KEY)}

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    eng_prompt = build_prompt(req.pose_description)
    task_id = await create_nano_banana_task(eng_prompt, req.style_reference_base64, req.style_reference_mime or "image/png")
    images = await poll_nano_banana_task(task_id)

    if not images:
        raise HTTPException(status_code=500, detail="ไม่ได้รับภาพจาก Freepik")

    normalized = []
    for img in images:
        if isinstance(img, str):
            normalized.append({"url": img})
        elif isinstance(img, dict):
            url = img.get("url") or img.get("base64") or img.get("src")
            if url:
                normalized.append({"url": url})

    return {
        "prompt_used": eng_prompt,
        "images": normalized if normalized else images,
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
