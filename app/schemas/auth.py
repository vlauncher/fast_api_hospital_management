from pydantic import BaseModel, EmailStr

class OTPVerify(BaseModel):
    otp_code: str

class ResendOTP(BaseModel):
    email: EmailStr
    purpose: str = "login"

class AuthResponse(BaseModel):
    message: str
    otp_expires_at: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    user_id: str
    otp_code: str
    new_password: str

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
