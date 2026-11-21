from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    nom: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 caractères (BR05)")
    hauteurCm: Optional[int] = None
    poidsKg: Optional[float] = None
    genre: Optional[str] = None

class AuthStepResponse(BaseModel):
    otp_required: bool = True
    email: str
    purpose: str  # "REGISTER" ou "LOGIN"
    message: str
    dev_otp: Optional[str] = None

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    purpose: str = Field(..., description="'REGISTER' ou 'LOGIN'")

class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    nom: str
    email: str
    is_verified: bool = True
    genre: Optional[str] = None
    hauteurCm: Optional[int] = None
    poidsKg: Optional[float] = None
    is_profile_completed: bool = False
