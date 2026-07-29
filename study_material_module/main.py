import logging
import asyncio
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from .schemas import (
    TopicStudyMaterialRequest,
    TopicStudyMaterialResponse,
    TopicResultItem,
    StudyMaterialRequest,
    StudyMaterialResponse
)
from .utils import setup_logging, slugify
from .config import OUTPUT_DIR
from .prompt_builder import build_topic_prompt
from .llm_client import generate_study_material_for_topic_async
from .pdf_generator import generate_topic_pdf

# Setup logging configuration on application startup
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Study Material Generation Module",
    description="Topic-level study material generation service driven by pedagogy recommendations.",
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

@app.get("/", summary="API Root Status")
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
    summary="Generate detailed study material PDFs for specific topics based on pedagogy recommendations"
)
async def generate_study_material(request: TopicStudyMaterialRequest):
    """
    Consumes topic details and pedagogy recommendations, generates detailed academic study material,
    and returns the path to the output PDF containing generated topics.
    """
    logger.info("Received Topic-Level Request")
    
    if not request.topics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The request must contain at least one topic."
        )
        
    course_folder_name = slugify(request.course_code)
    subject_output_dir = OUTPUT_DIR / course_folder_name
    subject_output_dir.mkdir(parents=True, exist_ok=True)
    
    topic_results = []
    successful_topics = []
    
    for index, topic in enumerate(request.topics):
        logger.info(f"Processing Topic {index + 1}/{len(request.topics)}: {topic.topic_name} (Pedagogy: {topic.pedagogy})")
        
        try:
            topic_prompt = build_topic_prompt(
                subject_name=request.subject_name,
                course_code=request.course_code,
                unit_number=request.unit_number,
                unit_title=request.unit_title,
                topic_name=topic.topic_name,
                duration=topic.duration,
                pedagogy=topic.pedagogy
            )
            
            # Generate topic content via LLM
            content = await generate_study_material_for_topic_async(topic_prompt)
            if not content or not str(content).strip():
                raise ValueError(f"Generated content for topic '{topic.topic_name}' is empty.")
                
            successful_topics.append((topic, content))
            topic_results.append(TopicResultItem(
                topic_name=topic.topic_name,
                status="success"
            ))
            logger.info(f"✓ Topic '{topic.topic_name}' Content Generated Successfully.")
            
        except Exception as e:
            logger.error(f"✗ Topic '{topic.topic_name}' Generation Failed: {type(e).__name__}: {str(e)}")
            topic_results.append(TopicResultItem(
                topic_name=topic.topic_name,
                status="failed",
                reason=str(e)
            ))
            
        if index < len(request.topics) - 1:
            await asyncio.sleep(2)
            
    pdf_path = None
    has_success = len(successful_topics) > 0
    
    if has_success:
        try:
            pdf_info = generate_topic_pdf(
                request=request,
                successful_topics=successful_topics,
                output_dir=subject_output_dir
            )
            pdf_path = pdf_info["pdf_path"]
        except Exception as e:
            logger.error(f"Failed to generate combined PDF: {type(e).__name__}: {str(e)}")
            has_success = False

    logger.info("Returning Response")
    return TopicStudyMaterialResponse(
        success=has_success,
        subject_name=request.subject_name,
        course_code=request.course_code,
        unit_number=request.unit_number,
        unit_title=request.unit_title,
        pdf_path=pdf_path,
        topic_results=topic_results
    )
