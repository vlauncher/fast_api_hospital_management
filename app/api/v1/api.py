from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, patients, doctors, appointments, files, 
    inventory, insurance, medical_records, lab_tests, ai, prescriptions, analytics,
    departments, beds, billing
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["insurance"])
api_router.include_router(medical_records.router, prefix="/medical-records", tags=["medical-records"])
api_router.include_router(lab_tests.router, prefix="/lab-tests", tags=["lab-tests"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["prescriptions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(beds.router, prefix="/beds", tags=["beds"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
