"""Part 1.3: structured output from a plain model call. Run: python -m part1.p1_structured"""
from typing import Literal

from pydantic import BaseModel, Field

from nimbus.model import get_model


class LeaveRequest(BaseModel):
    """A leave request extracted from free text."""
    start_date: str = Field(description="YYYY-MM-DD")
    end_date: str = Field(description="YYYY-MM-DD, inclusive")
    leave_type: Literal["annual", "sick", "parental"]
    reason: str | None = None


extractor = get_model().with_structured_output(LeaveRequest)
req = extractor.invoke("Today is 2026-11-04. I'd like annual leave from next Monday to Wednesday "
                       "for my sister's wedding.")
print(req)                    # a LeaveRequest object, not text
print(req.model_dump())
