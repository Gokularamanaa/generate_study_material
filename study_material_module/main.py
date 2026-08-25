import logging
import asyncio
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .schemas import (
    TopicStudyMaterialRequest,
    TopicStudyMaterialResponse,
    TopicResultItem,
    StudyMaterialRequest,
    StudyMaterialResponse
)
from .utils import setup_logging, slugify
from .config import OUTPUT_DIR, BASE_DIR
from .prompt_builder import build_topic_prompt
from .llm_client import generate_study_material_for_topic_async
from .pdf_generator import generate_topic_pdf, generate_single_topic_pdf
from .visuals.visual_planner import generate_visual_plan, generate_topic_visual_assets

# Setup logging configuration on application startup
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Study Material Generation Module",
    description="Topic-level study material generation service.",
    version="2.0.0"
)

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status", summary="API Root Status")
def read_root():
    return {
        "message": "Topic-Based Study Material Generation Module API is active.",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "generate_endpoint": "/generate-study-material"
    }

@app.post(
    "/generate-study-material",
    response_model=TopicStudyMaterialResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Generate detailed academic study material PDFs for specific topics"
)
async def generate_study_material(request: TopicStudyMaterialRequest):
    """
    Consumes topic details, generates detailed academic study material and visuals
    for EACH topic independently, and returns paths to output PDFs per topic.
    """
    logger.info(f"Received Request for {len(request.topics)} Topic(s)")
    
    if not request.topics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The request must contain at least one topic."
        )
        
    course_folder_name = slugify(request.course_code)
    unit_folder_name = f"Unit_{request.unit_number}"
    unit_output_dir = OUTPUT_DIR / course_folder_name / unit_folder_name
    unit_output_dir.mkdir(parents=True, exist_ok=True)
    
    topic_results = []
    successful_pdf_paths = []
    
    for index, topic in enumerate(request.topics):
        logger.info(f"--- Processing Topic {index + 1}/{len(request.topics)}: {topic.topic_name} ---")
        topic_slug = slugify(topic.topic_name)
        topic_assets_dir = unit_output_dir / topic_slug / "assets"
        
        try:
            # Step 1: Generate Content
            topic_prompt = build_topic_prompt(
                subject_name=request.subject_name,
                course_code=request.course_code,
                unit_number=request.unit_number,
                unit_title=request.unit_title,
                topic_name=topic.topic_name,
                duration=topic.duration
            )
            content = await generate_study_material_for_topic_async(topic_prompt)
            if not content or not str(content).strip():
                raise ValueError(f"Generated content for topic '{topic.topic_name}' is empty.")
            logger.info(f"✓ Topic '{topic.topic_name}' Content Generated.")

            # Step 2: Generate Visual Plan
            logger.info(f"Planning visuals for topic '{topic.topic_name}'...")
            visual_plan = await generate_visual_plan(topic.topic_name, content)
            
            # Step 3: Generate Visual Assets
            logger.info(f"Generating visual assets for topic '{topic.topic_name}'...")
            visual_assets = await generate_topic_visual_assets(visual_plan, topic.topic_name, topic_assets_dir)
            
            # Step 4 & 5: Render Single Topic PDF & Validate
            logger.info(f"Rendering topic PDF for '{topic.topic_name}'...")
            pdf_info = generate_single_topic_pdf(
                request=request,
                topic_item=topic,
                raw_markdown=content,
                output_dir=unit_output_dir,
                visual_assets=visual_assets
            )
            
            topic_pdf_path = pdf_info["pdf_path"]
            successful_pdf_paths.append(topic_pdf_path)
            
            topic_results.append(TopicResultItem(
                topic_name=topic.topic_name,
                status="success",
                pdf_path=topic_pdf_path
            ))
            logger.info(f"✓ Topic '{topic.topic_name}' PDF Generated Successfully -> {topic_pdf_path}")

        except Exception as e:
            logger.error(f"✗ Topic '{topic.topic_name}' Pipeline Failed: {type(e).__name__}: {str(e)}")
            topic_results.append(TopicResultItem(
                topic_name=topic.topic_name,
                status="failed",
                reason=str(e)
            ))
            
        if index < len(request.topics) - 1:
            await asyncio.sleep(1)
            
    total_topics = len(request.topics)
    success_count = len(successful_pdf_paths)
    
    if success_count == total_topics:
        completion_status = f"Completed — {success_count}/{total_topics} topics generated"
        overall_success = True
    elif success_count > 0:
        completion_status = f"Partially Completed — {success_count}/{total_topics} topics generated"
        overall_success = True
    else:
        completion_status = f"Failed — 0/{total_topics} topics generated"
        overall_success = False

    primary_pdf_path = successful_pdf_paths[0] if success_count > 0 else None

    logger.info(f"Returning Response: {completion_status}")
    return TopicStudyMaterialResponse(
        success=overall_success,
        completion_status=completion_status,
        subject_name=request.subject_name,
        course_code=request.course_code,
        unit_number=request.unit_number,
        unit_title=request.unit_title,
        pdf_path=primary_pdf_path,
        topic_results=topic_results
    )

# Serve PDF outputs statically at /output
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# Serve frontend web UI statically at / (Must be mounted AFTER API endpoints)
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

