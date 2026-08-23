from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserLogin(UserBase):
    password: str = Field(min_length=1, max_length=100)


class PasswordResetRequest(UserBase):
    pass


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=1000)
    password: str = Field(min_length=8, max_length=100)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
