# Hospital Management System - Backend REST API Plan

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: Google Gemini API
- **Authentication**: JWT + OTP (Email-based)
- **Cache**: Redis
- **Task Queue**: Celery
- **Email Service**: Gmail SMTP with Resend Logic
- **File Storage**: AWS S3 / MinIO
- **API Documentation**: OpenAPI (Swagger UI)
- **Rate Limiting**: Redis-based sliding window
- **Logging**: Loguru + ELK Stack
- **Task Queue**: Celery + Redis

---

## System Architecture Overview

```
┌─────────────────┐
│   Client Apps   │
│ (Web/Mobile)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Gateway   │
│   (FastAPI)     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│Database│ │Redis │ │Gemini  │ │S3 Storage│
│(Postgres)│(Cache)│ │  AI    │ │  (Files) │
└────────┘ └──────┘ └────────┘ └──────────┘
```

---

## Database Schema Design

### Core Tables

#### 1. Users Table
```sql
users:
  - id: UUID (PK)
  - first_name: VARCHAR(100)
  - last_name: VARCHAR(100)
  - email: VARCHAR(255) UNIQUE
  - password_hash: VARCHAR(255)
  - phone: VARCHAR(20)
  - role: ENUM (admin, doctor, nurse, receptionist, patient)
  - is_active: BOOLEAN
  - is_verified: BOOLEAN
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

### Redis Schema (Caching & OTP)

#### 1. OTP Storage
**Key**: `otp:{otp_code}`  
**Value**: `{ "user_id": "uuid", "email": "email", "purpose": "registration" }`  
**TTL**: 600 seconds (10 minutes)

*Note: OTP codes are 6-digit numeric codes. To prevent collisions when verifying with ONLY the code, the system ensures each active OTP code in Redis is unique before sending. If a collision is detected during generation, a new code is generated.*

#### 2. User Sessions
**Key**: `session:{user_id}`  
**Value**: `{ "access_token": "...", "refresh_token": "..." }`  
**TTL**: 3600 seconds

#### 3. Patients Table
```sql
patients:
  - id: UUID (PK)
  - user_id: UUID (FK -> users)
  - date_of_birth: DATE
  - gender: ENUM (male, female, other)
  - blood_group: VARCHAR(5)
  - address: TEXT
  - emergency_contact_name: VARCHAR(100)
  - emergency_contact_phone: VARCHAR(20)
  - medical_history: JSONB
  - allergies: JSONB
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 4. Doctors Table
```sql
doctors:
  - id: UUID (PK)
  - user_id: UUID (FK -> users)
  - specialization: VARCHAR(100)
  - license_number: VARCHAR(50) UNIQUE
  - qualification: VARCHAR(255)
  - experience_years: INTEGER
  - consultation_fee: DECIMAL
  - available_days: JSONB
  - available_time_slots: JSONB
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 5. Appointments Table
```sql
appointments:
  - id: UUID (PK)
  - patient_id: UUID (FK -> patients)
  - doctor_id: UUID (FK -> doctors)
  - appointment_date: DATE
  - appointment_time: TIME
  - duration_minutes: INTEGER
  - status: ENUM (scheduled, confirmed, completed, cancelled, no_show)
  - reason: TEXT
  - symptoms: TEXT
  - ai_preliminary_analysis: JSONB
  - notes: TEXT
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 6. Medical Records Table
```sql
medical_records:
  - id: UUID (PK)
  - patient_id: UUID (FK -> patients)
  - doctor_id: UUID (FK -> doctors)
  - appointment_id: UUID (FK -> appointments)
  - diagnosis: TEXT
  - prescription: JSONB
  - lab_results: JSONB
  - vitals: JSONB (blood_pressure, temperature, pulse, weight, height)
  - ai_insights: JSONB
  - follow_up_date: DATE
  - record_date: TIMESTAMP
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 7. Prescriptions Table
```sql
prescriptions:
  - id: UUID (PK)
  - medical_record_id: UUID (FK -> medical_records)
  - patient_id: UUID (FK -> patients)
  - doctor_id: UUID (FK -> doctors)
  - medications: JSONB
  - dosage_instructions: TEXT
  - duration_days: INTEGER
  - special_instructions: TEXT
  - ai_drug_interaction_check: JSONB
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 8. Lab Tests Table
```sql
lab_tests:
  - id: UUID (PK)
  - patient_id: UUID (FK -> patients)
  - doctor_id: UUID (FK -> doctors)
  - test_name: VARCHAR(255)
  - test_type: VARCHAR(100)
  - test_date: DATE
  - results: JSONB
  - ai_interpretation: TEXT
  - status: ENUM (pending, in_progress, completed)
  - file_url: VARCHAR(500)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 9. Departments Table
```sql
departments:
  - id: UUID (PK)
  - name: VARCHAR(100)
  - description: TEXT
  - head_doctor_id: UUID (FK -> doctors)
  - floor_number: INTEGER
  - contact_extension: VARCHAR(20)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 10. Hospital Beds Table
```sql
hospital_beds:
  - id: UUID (PK)
  - bed_number: VARCHAR(20) UNIQUE
  - department_id: UUID (FK -> departments)
  - bed_type: ENUM (general, icu, private, semi_private)
  - status: ENUM (available, occupied, maintenance, reserved)
  - patient_id: UUID (FK -> patients, nullable)
  - assigned_date: TIMESTAMP
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 11. Billing Table
```sql
billing:
  - id: UUID (PK)
  - patient_id: UUID (FK -> patients)
  - appointment_id: UUID (FK -> appointments)
  - total_amount: DECIMAL
  - paid_amount: DECIMAL
  - pending_amount: DECIMAL
  - payment_status: ENUM (pending, partial, paid, refunded)
  - payment_method: VARCHAR(50)
  - bill_items: JSONB
  - generated_date: TIMESTAMP
  - payment_date: TIMESTAMP
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 12. Inventory Table
```sql
inventory:
  - id: UUID (PK)
  - item_name: VARCHAR(255)
  - item_type: ENUM (medicine, equipment, supplies)
  - quantity: INTEGER
  - unit: VARCHAR(50)
  - expiry_date: DATE
  - supplier: VARCHAR(255)
  - reorder_level: INTEGER
  - ai_demand_forecast: JSONB
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

#### 13. Notifications Table
```sql
notifications:
  - id: UUID (PK)
  - user_id: UUID (FK -> users)
  - title: VARCHAR(255)
  - message: TEXT
  - type: ENUM (appointment, reminder, alert, info)
  - is_read: BOOLEAN
  - created_at: TIMESTAMP
```

#### 14. Audit Logs Table
```sql
audit_logs:
  - id: UUID (PK)
  - user_id: UUID (FK -> users)
  - action: VARCHAR(100)
  - resource: VARCHAR(100)
  - resource_id: UUID
  - changes: JSONB
  - ip_address: VARCHAR(45)
  - created_at: TIMESTAMP
```

---

## API Endpoints Structure

### 1. Authentication & Authorization

#### POST /api/v1/auth/register
**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "phone": "+1234567890",
  "role": "patient"
}
```
**Response:** Sends OTP to Gmail
```json
{
  "message": "OTP sent to your Gmail. Please verify to complete registration.",
  "otp_expires_at": "2024-12-20T10:30:00Z"
}
```

#### POST /api/v1/auth/verify-otp
**Request Body:**
```json
{
  "otp_code": "123456"
}
```
**Response:**
```json
{
  "access_token": "jwt_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "role": "patient"
  }
}
```

#### POST /api/v1/auth/login
**Request Body:**
```json
{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```
**Response:** Sends OTP to registered Gmail for 2FA
```json
{
  "message": "OTP sent to your registered Gmail",
  "otp_expires_at": "2024-12-20T10:30:00Z"
}
```

#### POST /api/v1/auth/resend-otp
**Request Body:**
```json
{
  "email": "john.doe@example.com",
  "purpose": "login" 
}
```
**Response:**
```json
{
  "message": "A new OTP has been sent to your Gmail",
  "otp_expires_at": "2024-12-20T10:40:00Z"
}
```

#### POST /api/v1/auth/forgot-password
**Request Body:**
```json
{
  "email": "john.doe@example.com"
}
```

#### POST /api/v1/auth/reset-password
**Request Body:**
```json
{
  "user_id": "uuid",
  "otp_code": "123456",
  "new_password": "NewSecurePass123!"
}
```

#### POST /api/v1/auth/refresh
**Request Body:**
```json
{
  "refresh_token": "jwt_refresh_token"
}
```

#### POST /api/v1/auth/logout
**Headers:** Authorization: Bearer {token}

---

### 2. User Management

#### GET /api/v1/users/profile
**Headers:** Authorization: Bearer {token}
**Response:**
```json
{
  "id": "uuid",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "role": "patient",
  "is_verified": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### PUT /api/v1/users/profile
**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

#### GET /api/v1/users/list
**Query Params:** ?role=doctor&page=1&limit=10&search=john
**Role:** Admin only

#### POST /api/v1/admin/staff/onboard
**Description:** Admin can onboard doctors, nurses, and receptionists.
**Request Body:**
```json
{
  "email": "staff@hospital.com",
  "role": "doctor",
  "department_id": "uuid"
}
```
**Response:** Sends invitation email to staff member.

#### GET /api/v1/admin/system/health
**Description:** Check status of DB, Redis, Celery, and Gemini API.
**Role:** Admin only.

#### GET /api/v1/admin/audit-logs
**Query Params:** ?user_id=uuid&action=delete&from_date=2024-12-01
**Role:** Admin only.

---

### 3. Patient Management

#### POST /api/v1/patients
**Request Body:**
```json
{
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_group": "O+",
  "address": "123 Main St, City",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567891",
  "allergies": ["penicillin", "peanuts"],
  "medical_history": {
    "chronic_conditions": ["diabetes"],
    "surgeries": ["appendectomy 2010"]
  }
}
```

#### GET /api/v1/patients/{patient_id}
**Response:**
```json
{
  "id": "uuid",
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com"
  },
  "date_of_birth": "1990-05-15",
  "age": 34,
  "gender": "male",
  "blood_group": "O+",
  "allergies": ["penicillin"],
  "medical_history": {}
}
```

#### PUT /api/v1/patients/{patient_id}

#### GET /api/v1/patients/search
**Query Params:** ?q=john&blood_group=O+

---

### 4. Doctor Management

#### POST /api/v1/doctors
**Request Body:**
```json
{
  "user_id": "uuid",
  "specialization": "Cardiology",
  "license_number": "MD123456",
  "qualification": "MBBS, MD",
  "experience_years": 10,
  "consultation_fee": 100.00,
  "available_days": ["monday", "tuesday", "wednesday"],
  "available_time_slots": {
    "monday": ["09:00-12:00", "14:00-17:00"],
    "tuesday": ["09:00-12:00"]
  }
}
```

#### GET /api/v1/doctors/{doctor_id}

#### PUT /api/v1/doctors/{doctor_id}

#### GET /api/v1/doctors/search
**Query Params:** ?specialization=cardiology&available_date=2024-12-20

#### GET /api/v1/doctors/{doctor_id}/availability
**Query Params:** ?date=2024-12-20
**Response:**
```json
{
  "doctor_id": "uuid",
  "date": "2024-12-20",
  "available_slots": [
    {
      "start_time": "09:00",
      "end_time": "09:30",
      "is_available": true
    },
    {
      "start_time": "09:30",
      "end_time": "10:00",
      "is_available": false
    }
  ]
}
```

---

### 5. Appointment Management

#### POST /api/v1/appointments
**Request Body:**
```json
{
  "doctor_id": "uuid",
  "appointment_date": "2024-12-20",
  "appointment_time": "10:00",
  "reason": "Regular checkup",
  "symptoms": "Fever, headache for 3 days"
}
```
**Response:** Includes AI preliminary analysis
```json
{
  "id": "uuid",
  "appointment_date": "2024-12-20",
  "appointment_time": "10:00",
  "status": "scheduled",
  "ai_preliminary_analysis": {
    "severity": "moderate",
    "suggested_tests": ["blood test", "temperature monitoring"],
    "precautions": ["stay hydrated", "rest"]
  }
}
```

#### GET /api/v1/appointments/{appointment_id}

#### PUT /api/v1/appointments/{appointment_id}
**Request Body:**
```json
{
  "status": "confirmed",
  "notes": "Patient confirmed attendance"
}
```

#### DELETE /api/v1/appointments/{appointment_id}
**Note:** Soft delete, changes status to "cancelled"

#### GET /api/v1/appointments/my-appointments
**Query Params:** ?status=scheduled&date_from=2024-12-01&date_to=2024-12-31

#### GET /api/v1/appointments/doctor/{doctor_id}
**Query Params:** ?date=2024-12-20&status=confirmed

---

### 6. Medical Records

#### POST /api/v1/medical-records
**Request Body:**
```json
{
  "patient_id": "uuid",
  "appointment_id": "uuid",
  "diagnosis": "Viral fever",
  "prescription": {
    "medications": [
      {
        "name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3 times daily",
        "duration": "5 days"
      }
    ]
  },
  "vitals": {
    "blood_pressure": "120/80",
    "temperature": "99.5",
    "pulse": "78",
    "weight": "70"
  },
  "follow_up_date": "2024-12-27"
}
```
**Response:** Includes AI insights
```json
{
  "id": "uuid",
  "ai_insights": {
    "diagnosis_confidence": "high",
    "treatment_recommendations": ["rest", "hydration"],
    "risk_factors": [],
    "follow_up_priority": "routine"
  }
}
```

#### GET /api/v1/medical-records/{record_id}

#### GET /api/v1/medical-records/patient/{patient_id}
**Query Params:** ?from_date=2024-01-01&to_date=2024-12-31

#### PUT /api/v1/medical-records/{record_id}

---

### 7. AI-Powered Features (Gemini Integration)

#### POST /api/v1/ai/symptom-analysis
**Request Body:**
```json
{
  "symptoms": ["fever", "headache", "body ache"],
  "duration_days": 3,
  "severity": "moderate",
  "patient_history": {
    "age": 34,
    "gender": "male",
    "chronic_conditions": ["diabetes"]
  }
}
```
**Response:**
```json
{
  "analysis": {
    "possible_conditions": [
      {
        "condition": "Viral Fever",
        "probability": "high",
        "description": "Common viral infection..."
      },
      {
        "condition": "Flu",
        "probability": "moderate",
        "description": "Influenza infection..."
      }
    ],
    "severity_assessment": "moderate",
    "recommended_actions": [
      "Schedule doctor appointment",
      "Monitor temperature",
      "Stay hydrated"
    ],
    "red_flags": [],
    "disclaimer": "This is AI-generated preliminary analysis. Please consult a doctor."
  }
}
```

#### POST /api/v1/ai/drug-interaction-check
**Request Body:**
```json
{
  "medications": [
    {
      "name": "Aspirin",
      "dosage": "100mg"
    },
    {
      "name": "Warfarin",
      "dosage": "5mg"
    }
  ],
  "patient_conditions": ["diabetes", "hypertension"]
}
```
**Response:**
```json
{
  "interactions": [
    {
      "severity": "high",
      "drugs": ["Aspirin", "Warfarin"],
      "description": "Increased risk of bleeding",
      "recommendation": "Consult doctor immediately"
    }
  ],
  "safe": false
}
```

#### POST /api/v1/ai/medical-report-summary
**Request Body:**
```json
{
  "report_text": "Full lab report text...",
  "report_type": "blood_test"
}
```
**Response:**
```json
{
  "summary": "Blood test results show normal hemoglobin...",
  "key_findings": [
    "Hemoglobin: 14.5 g/dL (Normal)",
    "WBC: 7,500/µL (Normal)"
  ],
  "abnormalities": [],
  "recommendations": "Results are within normal range"
}
```

#### POST /api/v1/ai/diagnosis-assistant
**Request Body:**
```json
{
  "symptoms": ["chest pain", "shortness of breath"],
  "vitals": {
    "blood_pressure": "150/95",
    "pulse": "95"
  },
  "patient_history": {
    "age": 55,
    "smoker": true,
    "family_history": ["heart disease"]
  }
}
```
**Response:**
```json
{
  "urgency": "high",
  "suggested_diagnosis": [
    {
      "condition": "Angina",
      "confidence": "moderate",
      "reasoning": "Chest pain with risk factors..."
    }
  ],
  "recommended_tests": [
    "ECG",
    "Cardiac enzymes",
    "Chest X-ray"
  ],
  "immediate_actions": [
    "Seek emergency care",
    "Avoid physical exertion"
  ]
}
```

#### POST /api/v1/ai/treatment-recommendations
**Request Body:**
```json
{
  "diagnosis": "Type 2 Diabetes",
  "patient_profile": {
    "age": 45,
    "weight": 85,
    "height": 170,
    "activity_level": "sedentary"
  },
  "current_medications": ["Metformin 500mg"]
}
```
**Response:**
```json
{
  "lifestyle_recommendations": [
    "30 minutes daily exercise",
    "Low carb diet",
    "Weight loss goal: 5-10% body weight"
  ],
  "medication_adjustments": [
    "Continue Metformin",
    "Consider adding..."
  ],
  "monitoring_schedule": {
    "blood_glucose": "daily",
    "HbA1c": "every 3 months"
  }
}
```

#### POST /api/v1/ai/chat-assistant
**Request Body:**
```json
{
  "message": "What should I do for a persistent cough?",
  "context": {
    "user_role": "patient",
    "patient_id": "uuid"
  }
}
```
**Response:**
```json
{
  "response": "A persistent cough can have various causes...",
  "suggestions": [
    "Book appointment with doctor",
    "Try home remedies"
  ],
  "related_articles": []
}
```

#### POST /api/v1/ai/predict-bed-occupancy
**Request Body:**
```json
{
  "department_id": "uuid",
  "forecast_days": 7
}
```
**Response:**
```json
{
  "predictions": [
    {
      "date": "2024-12-20",
      "predicted_occupancy": 85,
      "confidence": 0.87
    }
  ]
}
```

#### POST /api/v1/ai/inventory-demand-forecast
**Request Body:**
```json
{
  "item_id": "uuid",
  "forecast_months": 3
}
```

---

### 8. Prescription Management

#### POST /api/v1/prescriptions
**Request Body:**
```json
{
  "patient_id": "uuid",
  "medical_record_id": "uuid",
  "medications": [
    {
      "name": "Amoxicillin",
      "dosage": "500mg",
      "frequency": "3 times daily",
      "duration_days": 7,
      "instructions": "Take after meals"
    }
  ],
  "special_instructions": "Avoid alcohol"
}
```

#### GET /api/v1/prescriptions/{prescription_id}

#### GET /api/v1/prescriptions/patient/{patient_id}

#### POST /api/v1/prescriptions/{prescription_id}/check-interactions
**Note:** Uses AI to check drug interactions

---

### 9. Lab Tests

#### POST /api/v1/lab-tests
**Request Body:**
```json
{
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "test_name": "Complete Blood Count",
  "test_type": "blood_test",
  "test_date": "2024-12-20"
}
```

#### GET /api/v1/lab-tests/{test_id}

#### PUT /api/v1/lab-tests/{test_id}/results
**Request Body:**
```json
{
  "results": {
    "hemoglobin": "14.5",
    "wbc": "7500",
    "platelets": "250000"
  },
  "status": "completed"
}
```
**Response:** Includes AI interpretation

#### GET /api/v1/lab-tests/patient/{patient_id}

#### POST /api/v1/lab-tests/{test_id}/upload-report
**Content-Type:** multipart/form-data
**Body:** file

---

### 10. Department Management

#### POST /api/v1/departments
**Request Body:**
```json
{
  "name": "Cardiology",
  "description": "Heart and cardiovascular care",
  "head_doctor_id": "uuid",
  "floor_number": 3,
  "contact_extension": "301"
}
```

#### GET /api/v1/departments

#### GET /api/v1/departments/{department_id}

#### PUT /api/v1/departments/{department_id}

#### DELETE /api/v1/departments/{department_id}

---

### 11. Bed Management

#### POST /api/v1/beds
**Request Body:**
```json
{
  "bed_number": "ICU-101",
  "department_id": "uuid",
  "bed_type": "icu"
}
```

#### GET /api/v1/beds
**Query Params:** ?status=available&department_id=uuid&bed_type=icu

#### PUT /api/v1/beds/{bed_id}/assign
**Request Body:**
```json
{
  "patient_id": "uuid"
}
```

#### PUT /api/v1/beds/{bed_id}/release

#### GET /api/v1/beds/availability-report

---

### 12. Billing

#### POST /api/v1/billing
**Request Body:**
```json
{
  "patient_id": "uuid",
  "appointment_id": "uuid",
  "bill_items": [
    {
      "description": "Consultation fee",
      "amount": 100.00
    },
    {
      "description": "Lab test",
      "amount": 50.00
    }
  ]
}
```
**Response:**
```json
{
  "id": "uuid",
  "total_amount": 150.00,
  "pending_amount": 150.00,
  "payment_status": "pending"
}
```

#### GET /api/v1/billing/{billing_id}

#### POST /api/v1/billing/{billing_id}/payment
**Request Body:**
```json
{
  "amount": 150.00,
  "payment_method": "card"
}
```

#### GET /api/v1/billing/patient/{patient_id}

#### GET /api/v1/billing/reports
**Query Params:** ?from_date=2024-12-01&to_date=2024-12-31

---

### 13. Inventory Management

#### POST /api/v1/inventory
**Request Body:**
```json
{
  "item_name": "Paracetamol 500mg",
  "item_type": "medicine",
  "quantity": 1000,
  "unit": "tablets",
  "expiry_date": "2025-12-31",
  "supplier": "PharmaCorp",
  "reorder_level": 200
}
```

#### GET /api/v1/inventory

#### PUT /api/v1/inventory/{item_id}

#### GET /api/v1/inventory/low-stock
**Note:** Returns items below reorder level

#### GET /api/v1/inventory/expiring-soon
**Query Params:** ?days=30

#### POST /api/v1/inventory/{item_id}/forecast
**Note:** Uses AI to predict demand

---

### 14. Notifications

#### GET /api/v1/notifications
**Query Params:** ?is_read=false&page=1&limit=20

#### PUT /api/v1/notifications/{notification_id}/read

#### PUT /api/v1/notifications/mark-all-read

#### POST /api/v1/notifications/settings
**Request Body:**
```json
{
  "email_notifications": true,
  "sms_notifications": false,
  "appointment_reminders": true
}
```

---

### 15. Analytics & Reports

#### GET /api/v1/analytics/dashboard
**Role:** Admin, Doctor
**Response:**
```json
{
  "total_patients": 1500,
  "appointments_today": 45,
  "appointments_this_week": 230,
  "revenue_this_month": 125000,
  "bed_occupancy_rate": 78.5,
  "department_statistics": []
}
```

#### GET /api/v1/analytics/patient-statistics
**Query Params:** ?from_date=2024-01-01&to_date=2024-12-31

#### GET /api/v1/analytics/doctor-performance
**Query Params:** ?doctor_id=uuid&period=month

#### GET /api/v1/analytics/revenue-report
**Query Params:** ?from_date=2024-01-01&to_date=2024-12-31

#### GET /api/v1/analytics/appointment-trends
**Note:** Uses AI to predict appointment patterns

---

## Authentication Flow (Redis & Gmail Powered)

### Registration Flow
1. User submits registration form.
2. System validates input and checks if email already exists.
3. System generates a unique 6-digit OTP.
4. System stores OTP in **Redis** with the code as key and user data as value (10 min TTL).
5. System sends OTP via **Gmail SMTP**.
6. User enters OTP code.
7. System checks Redis for the code:
   - If found: Retrieves user data, creates user in DB, and issues JWT.
   - If not found/expired: Returns error.
8. User account activated and logged in.

### Login Flow
1. User submits email + password.
2. System validates credentials.
3. System generates a unique 6-digit OTP.
4. System stores OTP in **Redis** mapping the code to the `user_id` (10 min TTL).
5. System sends OTP via **Gmail SMTP**.
6. User enters OTP code.
7. System verifies code against Redis:
   - If valid: Issues JWT access token (1h) and refresh token (7d).
   - If invalid: Increments failure count or returns error.

### Resend OTP Flow
1. User requests resend by providing their email.
2. System checks if a recent OTP was sent (rate limiting).
3. System generates a new unique OTP.
4. System updates/replaces the OTP in **Redis**.
5. System sends the new OTP via **Gmail SMTP**.

### Password Reset Flow
1. User requests password reset with email.
2. System generates OTP and stores in **Redis** with `purpose: password_reset`.
3. System sends OTP via **Gmail SMTP**.
4. User submits OTP + new password.
5. System verifies OTP from Redis and updates password in PostgreSQL.

---

## Robustness & Scalability Features

### 1. Advanced Error Handling Middleware
- Global Exception Handler to capture all unhandled errors.
- Structured JSON error responses for all status codes.
- Integration with Sentry for real-time error tracking and alerting.

### 2. Request Validation & Sanitization
- Strict Pydantic models for all incoming request bodies and query parameters.
- NoSQL injection and XSS prevention via input sanitization.
- Auto-generation of detailed validation error messages for clients.

### 3. Rate Limiting & DoS Protection
- Redis-based sliding window rate limiter.
- Different tiers for rate limiting (Public vs. Auth vs. Admin).
- Exponential backoff for sensitive endpoints like Login and OTP verify.

### 4. Database Robustness
- Read/Write splitting (Primary for writes, Replicas for reads).
- Connection pooling with SQLAlchemy (using `AsyncSession`).
- Automated database migrations using Alembic.
- Periodic health checks for DB and Redis connections.

### 5. Background Processing (Celery + Redis)
- Offloading long-running tasks:
  - Sending emails (OTP, Reminders).
  - AI analysis (Gemini API calls).
  - Generating PDF reports/bills.
  - Image processing for medical scans.

### 6. Logging & Observability
- Centralized logging using `loguru`.
- Correlation IDs to track requests across multiple services.
- Metrics collection for Prometheus (request latency, error rates, system health).
- Grafana dashboards for real-time monitoring.

### 7. Security Hardening
- Secure Cookie management (HttpOnly, Secure, SameSite).
- Password hashing with Argon2 (more secure than bcrypt).
- Regular security audits and automated dependency scanning (e.g., Dependabot).
- Audit logs for every state-changing operation.

### 2. Password Security
- Minimum 8 characters
- Must include: uppercase, lowercase, number, special character
- Hashed using bcrypt (cost factor: 12)
- Password history: last 5 passwords cannot be reused

### 3. API Security
- CORS configuration
- Request rate limiting
- Input validation with Pydantic
- SQL injection prevention (ORM)
- XSS protection
- CSRF tokens for state-changing operations

### 4. Data Protection
- Encryption at rest (database)
- Encryption in transit (TLS 1.3)
- HIPAA compliance measures
- PII data masking in logs
- Audit logging for sensitive operations

### 5. File Upload Security
- File type validation
- File size limits (10MB for documents, 50MB for images)
- Virus scanning
- Secure file storage with signed URLs

---

## Gemini AI Integration Details

### Configuration
```python
# Environment variables
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-pro
GEMINI_MAX_TOKENS=2048
```

### Use Cases

#### 1. Symptom Analysis
- Model: gemini-pro
- Temperature: 0.3 (for consistent medical advice)
- Input: Patient symptoms, duration, severity
- Output: Possible conditions, severity assessment, recommendations

#### 2. Drug Interaction Check
- Model: gemini-pro
- Temperature: 0.1 (for accuracy)
- Input: List of medications, patient conditions
- Output: Interactions, severity, recommendations

#### 3. Medical Report Summarization
- Model: gemini-pro
- Temperature: 0.2
- Input: Lab report text/OCR from uploaded image
- Output: Structured summary, key findings, abnormalities

#### 4. Diagnosis Assistant
- Model: gemini-pro
- Temperature: 0.3
- Input: Symptoms, vitals, patient history
- Output: Differential diagnosis, recommended tests, urgency level

#### 5. Treatment Recommendations
- Model: gemini-pro
- Temperature: 0.3
- Input: Diagnosis, patient profile, current medications
- Output: Treatment plan, lifestyle changes, monitoring schedule

#### 6. Chatbot Assistant
- Model: gemini-pro
- Temperature: 0.5 (for natural conversation)
- Input: User question, context
- Output: Helpful response with suggestions

#### 7. Demand Forecasting
- Model: gemini-pro
- Temperature: 0.2
- Input: Historical data (appointments, inventory usage)
- Output: Predictions with confidence scores

### Safety & Disclaimers
- All AI responses include medical disclaimer
- AI suggestions require doctor validation
- Critical decisions never fully automated
- Audit trail for all AI recommendations
- Fallback to human review for low-confidence predictions

---

## Background Tasks (Celery)

### Scheduled Tasks

#### 1. Appointment Reminders
- Run: Every hour
- Action: Send email/SMS reminders 24 hours before appointment

#### 2. OTP Cleanup
- Run: Every 15 minutes
- Action: Delete expired OTPs

#### 3. Inventory Alerts
- Run: Daily at 8 AM
- Action: Alert admin about low stock and expiring items

#### 4. Bed Occupancy Report
- Run: Daily at 6 AM
- Action: Generate bed occupancy report for admin

#### 5. AI Model Updates
- Run: Weekly
- Action: Retrain demand forecasting models

#### 6. Backup
- Run: Daily at 2 AM
- Action: Database backup to S3

---

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    },
    "timestamp": "2024-12-19T10:30:00Z"
  }
}
```

### Error Codes
- `VALIDATION_ERROR` - 400
- `UNAUTHORIZED` - 401
- `FORBIDDEN` - 403
- `NOT_FOUND` - 404
- `CONFLICT` - 409
- `RATE_LIMIT_EXCEEDED` - 429
- `INTERNAL_SERVER_ERROR` - 500
- `SERVICE_UNAVAILABLE` - 503

---

## Performance Optimization

### 1. Caching Strategy (Redis)
- User sessions: 1 hour TTL
- Doctor availability: 15 minutes TTL
- Department list: 1 day TTL
- Frequently accessed medical records: 30 minutes TTL

### 2. Database Optimization
- Indexes on frequently queried fields (email, patient_id, doctor_id, dates)
- Connection pooling
- Query optimization with EXPLAIN ANALYZE
- Pagination for large datasets

### 3. API Optimization
- Response compression (gzip)
- Async operations where possible
- Batch endpoints for bulk operations
- Lazy loading for related entities

---

## Monitoring & Logging

### Metrics to Track
- API response times
- Error rates by endpoint
- Authentication success/failure rates
- Database query performance
- AI model response times
- Appointment booking conversion rates
- System uptime

### Logging Levels
- DEBUG: Development only
- INFO: Important business events
- WARNING: Potential issues
- ERROR: Errors requiring attention
- CRITICAL: System failures

### Log Format
```json
{
  "timestamp": "2024-12-19T10:30:00Z",
  "level": "INFO",
  "service": "appointment-service",
  "user_id": "uuid",
  "action": "create_appointment",
  "resource_id": "uuid",
  "duration_ms": 245,
  "status": "success"
}
```

---

## Deployment Architecture

### Recommended Stack
- **Container**: Docker
- **Orchestration**: Kubernetes
- **Load Balancer**: Nginx/AWS ALB
- **CI/CD**: GitHub Actions/GitLab CI
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Secrets Management**: HashiCorp Vault/AWS Secrets Manager

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/hospital_db
DB_POOL_SIZE=20

# Redis
REDIS_URL=redis://host:6379/0

# JWT
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-hospital-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
MAIL_FROM=your-hospital-email@gmail.com
MAIL_FROM_NAME="LifeLine Hospital"

# Gemini AI
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-pro

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=hospital-files

# Application
ENVIRONMENT=production
API_VERSION=v1
CORS_ORIGINS=https://hospital.com,https://app.hospital.com
```

---

## Testing Strategy

### Unit Tests
- Models and schemas
- Business logic
- Utility functions
- AI prompt engineering

### Integration Tests
- API endpoints
- Database operations
- External service integrations (Gemini, email)

### Load Tests
- Concurrent users: 1000
- Appointments per second: 50
- API response time: <200ms (p95)

### Security Tests
- Penetration testing
- OWASP Top 10 compliance
- SQL injection tests
- XSS vulnerability tests

---

## API Rate Limits

### Public Endpoints
- Registration: 5 per hour per IP
- Login: 10 per hour per user
- OTP requests: 5 per hour per user

### Authenticated Endpoints
- Standard users: 1000 requests/hour
- Premium users: 5000 requests/hour
- Admin users: No limit

### AI Endpoints
- Symptom analysis: 20 per day per user
- Chatbot: 100 messages per day per user

---

## Future Enhancements

### Phase 2
- Telemedicine video consultations
- Mobile app (React Native)
- Patient portal for self-service
- Integration with wearable devices
- Pharmacy management module
- Insurance claim processing

### Phase 3
- Multi-tenant support (multiple hospitals)
- Advanced AI diagnostics with medical imaging
- Predictive analytics for disease outbreaks
- Integration with national health databases
- Blockchain for medical records
- IoT device integration (heart monitors, glucose meters)

---

## Compliance & Standards

### Healthcare Standards
- HL7 FHIR for interoperability
- HIPAA compliance (US)
- GDPR compliance (EU)
- DICOM for medical imaging

### API Standards
- RESTful principles
- OpenAPI 3.0 specification
- OAuth 2.0 authorization
- JSON:API specification

---

## Documentation

### API Documentation
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- Postman collection available

### Developer Documentation
- Setup guide
- Architecture diagrams
- Database schema
- Deployment guide
- Contributing guidelines

---

## Support & Maintenance

### Backup Strategy
- Daily automated backups
- Point-in-time recovery capability
- 30-day retention policy
- Disaster recovery plan

### Update Schedule
- Security patches: Immediate
- Minor updates: Monthly
- Major updates: Quarterly

### Support Channels
- Technical support: support@hospital.com
- Bug reports: GitHub Issues
- Feature requests: Product roadmap

---

## Conclusion

This Hospital Management System backend provides a comprehensive, modern, and AI-powered solution for healthcare facilities. The integration of Gemini AI enhances clinical decision-making while maintaining security, scalability, and compliance with healthcare regulations.

### Key Features Summary
✅ Secure authentication with OTP-based 2FA
✅ Comprehensive patient and doctor management
✅ AI-powered symptom analysis and diagnosis assistance
✅ Drug interaction checking
✅ Smart appointment scheduling
✅ Electronic medical records
✅ Billing and inventory management
✅ Real-time notifications
✅ Analytics and reporting
✅ HIPAA-compliant architecture

### Next Steps
1. Set up development environment
2. Initialize FastAPI project structure
3. Implement authentication module
4. Integrate Gemini AI
5. Build core modules incrementally
6. Deploy to staging environment
7. Conduct security audit
8. Launch production system

---

**Document Version:** 1.0  
**Last Updated:** December 19, 2024  
**Author:** Backend Architecture Team
