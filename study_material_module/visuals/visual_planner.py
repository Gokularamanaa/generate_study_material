import os
import json
import re
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any
import httpx

from .image_generator import generate_topic_image, generate_fallback_svg_image
from ..prompt_builder import build_visual_plan_prompt
from ..llm_client import generate_study_material_for_topic_async

logger = logging.getLogger(__name__)

async def generate_visual_plan(topic_name: str, content_markdown: str) -> Dict[str, Any]:
    """
    Calls LLM text model to analyze topic content and return a visual plan dictionary.
    """
    prompt = build_visual_plan_prompt(topic_name, content_markdown)
    try:
        response_text = await generate_study_material_for_topic_async(prompt)
        
        # Clean response string to parse raw JSON
        clean_json = response_text.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.MULTILINE)
            clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE)
            
        data = json.loads(clean_json.strip())
        if isinstance(data, dict) and "visuals" in data:
            return data
    except Exception as e:
        logger.warning(f"Failed to generate visual plan via LLM for topic '{topic_name}': {str(e)}. Using default visual plan.")
        
    # Default visual plan if LLM call or JSON parsing fails
    return {
        "visuals": [
            {
                "id": f"{topic_name.lower().replace(' ', '_')}_flowchart",
                "type": "flowchart",
                "generator": "mermaid",
                "priority": "required",
                "purpose": f"Process flowchart for {topic_name}",
                "prompt_or_code": f"graph TD\n    A[Start {topic_name}] --> B[Initialization]\n    B --> C[Process & Verification]\n    C --> D[Completion]"
            },
            {
                "id": f"{topic_name.lower().replace(' ', '_')}_concept",
                "type": "conceptual_illustration",
                "generator": "openai_image",
                "priority": "optional",
                "purpose": f"Conceptual diagram of {topic_name}",
                "prompt_or_code": f"Educational vector diagram illustrating {topic_name} on clean white background"
            }
        ]
    }


async def generate_topic_visual_assets(
    visual_plan: Dict[str, Any],
    topic_name: str,
    assets_dir: Path
) -> List[Dict[str, Any]]:
    """
    Generates and saves visual assets to disk (assets_dir) based on visual_plan.
    Returns list of generated visual asset items containing local file paths and captions.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    generated_assets = []
    visuals = visual_plan.get("visuals", [])[:2]
    
    for idx, item in enumerate(visuals):
        vis_id = item.get("id", f"visual_{idx+1}")
        vis_type = item.get("type", "diagram")
        generator = item.get("generator", "mermaid").lower()
        purpose = item.get("purpose", f"{topic_name} Visual")
        code_or_prompt = item.get("prompt_or_code", "")
        
        asset_file = None
        
        if generator == "mermaid":
            asset_file = await render_and_save_mermaid(code_or_prompt, assets_dir / f"{vis_id}.svg", topic_name, purpose)
        elif generator == "openai_image":
            asset_file = await generate_topic_image(code_or_prompt or purpose, assets_dir / f"{vis_id}.png", topic_name=topic_name)
        elif generator == "svg":
            asset_file = generate_fallback_svg_image(assets_dir / f"{vis_id}.svg", topic_name=topic_name, prompt=purpose)
        else:
            asset_file = generate_fallback_svg_image(assets_dir / f"{vis_id}.svg", topic_name=topic_name, prompt=purpose)
            
        if asset_file and asset_file.exists():
            sec_target = item.get("section_target") or item.get("target_section") or item.get("section_id") or vis_type
            generated_assets.append({
                "id": vis_id,
                "type": vis_type,
                "path": asset_file,
                "caption": f"Figure {len(generated_assets) + 1}: {purpose}",
                "section_target": sec_target
            })
            logger.info(f"✓ Saved visual asset [{vis_id}] ({vis_type}, section: '{sec_target}') -> {asset_file}")
            
    return generated_assets


from .diagram_generator import get_default_topic_flowchart_model, render_structured_flowchart_svg

async def render_and_save_mermaid(mermaid_code: str, output_path: Path, topic_name: str, title: str) -> Path:
    """
    Renders a complete, validated structured flowchart SVG for topic_name and saves to output_path.
    Guarantees every box contains step title and readable description with zero empty boxes.
    """
    try:
        model = get_default_topic_flowchart_model(topic_name)
        svg_content = render_structured_flowchart_svg(model)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(svg_content, encoding="utf-8")
        logger.info(f"✓ Saved validated structured flowchart SVG [{output_path.name}] -> {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"Structured flowchart rendering failed for '{title}': {str(e)}. Using vector SVG fallback.")
        return generate_fallback_svg_image(output_path, topic_name=topic_name, prompt=title)
