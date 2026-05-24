import os
import base64
import httpx
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class GenerateRequest(BaseModel):
    pose_description: str
    style_reference_base64: Optional[str] = None

def build_prompt(pose_description: str) -> str:
    return f"A mascot character {pose_description}, cartoon illustration style, clean white background, high quality, cute and friendly"

async def generate_image_openai(prompt: str, style_reference_base64: Optional[str]) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY ยังไม่ได้ตั้งค่า")

    async with httpx.AsyncClient(timeout=60) as client:
        if style_reference_base64:
            # ใช้ edits endpoint เมื่อมีภาพต้นฉบับ
            image_bytes = base64.b64decode(style_reference_base64)
            resp = await client.post(
                "https://api.openai.com/v1/images/edits",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={
                    "image": ("mascot.png", image_bytes, "image/png"),
                },
                data={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "n": "1",
                    "size": "1024x1024",
                    "response_format": "b64_json",
                }
            )
        else:
            # ใช้ generations endpoint เมื่อไม่มีภาพ
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json",
                }
            )

        if not resp.is_success:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        b64 = data["data"][0]["b64_json"]
        return f"data:image/png;base64,{b64}"

@app.get("/health")
async def health():
    return {"status": "ok", "openai_key_set": bool(OPENAI_API_KEY)}

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    eng_prompt = build_prompt(req.pose_description)
    image_url = await generate_image_openai(eng_prompt, req.style_reference_base64)
    return {
        "prompt_used": eng_prompt,
        "images": [{"url": image_url}],
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
