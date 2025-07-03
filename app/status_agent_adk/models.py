from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime

class Relocation(BaseModel):
    id: int
    given_name: str
    surname: str
    complete_name: str
    email: str
    relocation_status: str
    relocation_end_date: Optional[str]
    relocation_last_update: str