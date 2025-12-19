from pydantic import BaseModel, EmailStr

class OTPVerify(BaseModel):
    otp_code: str

class ResendOTP(BaseModel):
    email: EmailStr
    purpose: str = "login"

class AuthResponse(BaseModel):
    message: str
    otp_expires_at: str
