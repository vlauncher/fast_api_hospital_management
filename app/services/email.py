from loguru import logger

async def send_otp_email(email: str, otp: str):
    # Stub for sending email
    # In production, use SMTP or Resend
    logger.info(f"Sending OTP {otp} to {email}")
    print(f"------------ OTP for {email}: {otp} ------------")
    return True
