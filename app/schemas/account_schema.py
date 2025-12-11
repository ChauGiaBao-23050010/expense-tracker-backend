from pydantic import BaseModel, Field
from typing import Optional
import datetime

class AccountBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: Optional[str] = Field(None, max_length=50)

class AccountCreate(AccountBase):
    current_balance: float = 0.0

class AccountUpdate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    user_id: int
    current_balance: float
    created_at: datetime.datetime

    class Config:
        from_attributes = True