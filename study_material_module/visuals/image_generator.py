import os
import logging
import base64
import httpx
from pathlib import Path
from typing import Optional
from ..config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

async def generate_topic_image(prompt: str, output_path: Path, topic_name: str = "") -> Optional[Path]:
    """
    Generates a conceptual illustration image using OpenAI DALL-E / Image Generation API.
    Saves the image to output_path (PNG/JPG).
    If OpenAI API fails or is unconfigured, gracefully generates a clean labeled SVG diagram as fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY).strip()
    
    # Check if valid OpenAI key exists
    if api_key and api_key not in {"", "your_openai_api_key_here", "DEVELOPMENT_FALLBACK_KEY", "YOUR_API_KEY"}:
        try:
            logger.info(f"Generating image via OpenAI Image API for prompt: '{prompt[:60]}...'")
            url = "https://api.openai.com/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "dall-e-3",
                "prompt": f"Academic textbook diagram or illustration: {prompt}. Clean white background, minimalist vector style, clear lighting, educational figure, no text clutter.",
                "n": 1,
                "size": "1024x1024"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    item = data["data"][0]
                    img_bytes = None
                    if "b64_json" in item:
                        img_bytes = base64.b64encode(item["b64_json"])
                    elif "url" in item:
                        img_resp = await client.get(item["url"])
                        if img_resp.status_code == 200:
                            img_bytes = img_resp.content
                    if img_bytes:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(img_bytes)
                        logger.info(f"✓ OpenAI Image saved successfully to {output_path}")
                        return output_path
                else:
                    logger.warning(f"OpenAI Image API returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"OpenAI Image API call failed: {type(e).__name__}: {str(e)}. Using clean SVG fallback.")

    # Fallback: Create clean labeled vector SVG
    return generate_fallback_svg_image(output_path, topic_name=topic_name, prompt=prompt)


def generate_fallback_svg_image(output_path: Path, topic_name: str = "", prompt: str = "") -> Path:
    """
    Generates a clean, topic-labeled vector SVG illustration on disk (solid colors compatible with ReportLab).
    Uses dynamic topic terminology and clean SVG layout.
    """
    display_title = (topic_name or "Academic Concept Architecture").upper()
    subtitle = (prompt[:55] + "...") if prompt else "Technical Diagram & Architecture Overview"
    
    clean_topic = topic_name or "System"

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
        <rect width="800" height="450" rx="12" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>
        <rect x="30" y="30" width="740" height="70" rx="8" fill="#0f172a"/>
        <text x="50" y="70" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="#ffffff">{display_title}</text>
        <text x="50" y="90" font-family="Arial, sans-serif" font-size="11" fill="#38bdf8">{subtitle}</text>
        
        <!-- Component 1 -->
        <rect x="60" y="140" width="190" height="150" rx="8" fill="#ffffff" stroke="#0d9488" stroke-width="2"/>
        <rect x="60" y="140" width="190" height="35" rx="8" fill="#0d9488"/>
        <text x="155" y="163" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">INPUT &amp; SETUP</text>
        <text x="155" y="210" font-family="Arial, sans-serif" font-size="12" fill="#334155" text-anchor="middle">Initial Configuration</text>
        <text x="155" y="235" font-family="Arial, sans-serif" font-size="11" fill="#64748b" text-anchor="middle">{clean_topic} Test Scope</text>
        <text x="155" y="260" font-family="Arial, sans-serif" font-size="11" fill="#0f766e" text-anchor="middle">Active Environment</text>
        
        <!-- Arrow 1 -->
        <path d="M 250 215 L 340 215" stroke="#0284c7" stroke-width="3"/>
        <text x="295" y="205" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#0284c7" text-anchor="middle">Execution Flow</text>

        <!-- Component 2 -->
        <rect x="340" y="140" width="190" height="150" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2"/>
        <rect x="340" y="140" width="190" height="35" rx="8" fill="#0284c7"/>
        <text x="435" y="163" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">CORE PROCESSOR</text>
        <text x="435" y="210" font-family="Arial, sans-serif" font-size="12" fill="#334155" text-anchor="middle">{clean_topic} Engine</text>
        <text x="435" y="235" font-family="Arial, sans-serif" font-size="11" fill="#64748b" text-anchor="middle">Verification &amp; Control</text>
        <text x="435" y="260" font-family="Arial, sans-serif" font-size="11" fill="#0369a1" text-anchor="middle">Processing Queue</text>

        <!-- Arrow 2 -->
        <path d="M 530 215 L 620 215" stroke="#0d9488" stroke-width="3"/>
        <text x="575" y="205" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#0d9488" text-anchor="middle">Result Stream</text>

        <!-- Component 3 -->
        <rect x="620" y="140" width="120" height="150" rx="8" fill="#ffffff" stroke="#475569" stroke-width="2"/>
        <rect x="620" y="140" width="120" height="35" rx="8" fill="#475569"/>
        <text x="680" y="163" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">TARGET</text>
        <text x="680" y="210" font-family="Arial, sans-serif" font-size="11" fill="#334155" text-anchor="middle">Verified Output</text>
        <text x="680" y="235" font-family="Arial, sans-serif" font-size="10" fill="#64748b" text-anchor="middle">Quality Metric</text>

        <!-- Bottom Banner -->
        <rect x="30" y="320" width="740" height="100" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>
        <text x="50" y="350" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="#1e293b">Academic Structural Model Analysis</text>
        <text x="50" y="375" font-family="Arial, sans-serif" font-size="11" fill="#475569">Key Mechanism: Verified execution with quality assurance and dynamic state transitions.</text>
        <text x="50" y="395" font-family="Arial, sans-serif" font-size="10" fill="#64748b">Topic Scope: {clean_topic}</text>
    </svg>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"✓ Created clean topic vector SVG for '{clean_topic}' -> {output_path}")
    return output_path
