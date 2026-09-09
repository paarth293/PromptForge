import uuid
from typing import List

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    __test__ = False
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    expected_answer: str
    category: str = "general"
    source: str = "generated"  # "user" or "generated"

class GeneratedTestSuite(BaseModel):
    suite_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    spec_id: str = ""
    gold_cases: List[TestCase] = Field(default_factory=list)
    edge_cases: List[TestCase] = Field(default_factory=list)
    total_cases: int = 0
    user_supplied_count: int = 0
    generated_count: int = 0
