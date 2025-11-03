from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class FollowUpQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for the follow-up question")
    question: str = Field(..., description="The follow-up question text")
    answer_options: List[str] = Field(..., description="List of possible answers for the follow-up question")
    multiple_selection: bool = Field(False, description="Indicates if multiple answers can be selected")
    answers: Optional[List[str]] = Field(None, description="The answers selected by the user")







