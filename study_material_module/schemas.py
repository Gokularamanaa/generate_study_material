from pydantic import BaseModel, Field
from typing import List, Optional

class TopicRequestItem(BaseModel):
    topic_name: str = Field(..., description="The name of the topic, e.g. TCP")
    duration: int = Field(..., description="The duration of the topic in hours")



class TopicStudyMaterialRequest(BaseModel):
    subject_name: str = Field(..., description="The subject name, e.g. Computer Networks")
    course_code: str = Field(..., description="The course code, e.g. CS3591")
    unit_number: int = Field(..., description="The unit number")
    unit_title: str = Field(..., description="The title of the unit")
    topics: List[TopicRequestItem] = Field(..., description="The list of topics to generate")

class TopicResultItem(BaseModel):
    topic_name: str = Field(..., description="The name of the topic")
    status: str = Field("success", description="Status of topic generation ('success' or 'failed')")
    reason: Optional[str] = Field(None, description="Reason for failure if status is failed")

class TopicStudyMaterialResponse(BaseModel):
    success: bool = Field(..., description="Overall status of the request")
    subject_name: str = Field(..., description="The subject name")
    course_code: str = Field(..., description="The course code")
    unit_number: int = Field(..., description="The unit number")
    unit_title: str = Field(..., description="The title of the unit")
    pdf_path: Optional[str] = Field(None, description="Path to the generated PDF document containing successfully generated topics")
    topic_results: List[TopicResultItem] = Field(..., description="List of topic generation results and statuses")

# Aliases for backward compatibility
StudyMaterialRequest = TopicStudyMaterialRequest
StudyMaterialResponse = TopicStudyMaterialResponse
GeneratedPDFItem = TopicResultItem
