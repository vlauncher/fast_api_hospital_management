# FastAPI Hospital Management System - Modern Backend Architecture

## Executive Summary

This document outlines a **production-grade Hospital Management System (HMS)** backend built with **FastAPI**, designed for real-world healthcare workflows with enterprise-level security, scalability, and compliance.

**Target Scale**: 500-bed hospital, 200+ concurrent users, 5000+ daily transactions

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Domain Models & Database Schema](#3-domain-models--database-schema)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [API Endpoints by Module](#5-api-endpoints-by-module)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Security & Compliance](#8-security--compliance)
9. [Background Processing](#9-background-processing)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Project Structure](#11-project-structure)
12. [Implementation Roadmap](#12-implementation-roadmap)

---

## 1. System Architecture

### 1.1 Architecture Pattern

**Modular Monolith with Event-Driven Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway / Load Balancer             │
│                    (NGINX / AWS ALB / Traefik)               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │   Auth &    │   Patient   │     EMR     │  Pharmacy   │ │
│  │     IAM     │  Management │   Module    │   Module    │ │
│  ├─────────────┼─────────────┼─────────────┼─────────────┤ │
│  │ Appointment │     Lab     │   Billing   │  Inpatient  │ │
│  │   Module    │   Module    │   Module    │   Module    │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           Domain Services & Business Logic              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Event Bus (Internal Events)                ││
│  └─────────────────────────────────────────────────────────┘│
└────────────┬──────────────┬──────────────┬──────────────────┘
             │              │              │
             ▼              ▼              ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ PostgreSQL │  │   Redis    │  │  RabbitMQ  │
    │  (Primary) │  │  (Cache &  │  │  (Message  │
    │            │  │  Sessions) │  │   Broker)  │
    └────────────┘  └────────────┘  └────────────┘
             │
             ▼
    ┌────────────┐
    │ PostgreSQL │
    │  (Read     │
    │  Replica)  │
    └────────────┘
```

### 1.2 Design Principles

- **Domain-Driven Design (DDD)**: Each module represents a bounded context
- **SOLID Principles**: Maintainable, testable code
- **Event Sourcing**: Critical operations emit events for audit trails
- **CQRS Pattern**: Separate read and write models for complex queries
- **API-First Design**: OpenAPI 3.0 specification-driven development

---

## 2. Technology Stack

### 2.1 Core Framework

```yaml
Backend Framework: FastAPI 0.109+
Python Version: 3.11+
ASGI Server: Uvicorn with Gunicorn workers
API Documentation: Swagger UI + ReDoc
```

### 2.2 Database & Caching

```yaml
Primary Database: PostgreSQL 15+
ORM: SQLAlchemy 2.0+ (async)
Migrations: Alembic
Cache Layer: Redis 7+
Search Engine: Elasticsearch (optional, for full-text search)
```

### 2.3 Message Queue & Background Tasks

```yaml
Message Broker: RabbitMQ / Apache Kafka
Task Queue: Celery / ARQ
Scheduler: Celery Beat / APScheduler
```

### 2.4 Security & Authentication

```yaml
Authentication: JWT (Access + Refresh Tokens)
Password Hashing: bcrypt / Argon2
Encryption: Fernet (PII), AES-256 (at rest)
API Security: OAuth2, API Keys for integrations
Rate Limiting: slowapi / Redis-based
```

### 2.5 Monitoring & Observability

```yaml
Logging: Structlog / Python logging
APM: Sentry / New Relic
Metrics: Prometheus + Grafana
Tracing: OpenTelemetry / Jaeger
Health Checks: Custom /health endpoints
```

### 2.6 File Storage

```yaml
File Storage: AWS S3 / MinIO / Azure Blob Storage
Document Processing: pdf2image, Pillow, python-docx
DICOM Support: pydicom (for medical imaging)
```

### 2.7 DevOps & CI/CD

```yaml
Containerization: Docker + Docker Compose
Orchestration: Kubernetes / Docker Swarm
CI/CD: GitHub Actions / GitLab CI / Jenkins
IaC: Terraform / Pulumi
```


---

## 3. Domain Models & Database Schema

### 3.1 Core Entities Overview

This section provides comprehensive database schema for all domain entities in the Hospital Management System.

#### 3.1.1 Identity & Access Management

**User Table**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    staff_id VARCHAR(20) UNIQUE,
    department_id UUID REFERENCES departments(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_staff_id ON users(staff_id);
CREATE INDEX idx_users_department ON users(department_id);
```

**Role Table**
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Session Table**
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

#### 3.1.2 Patient Management

**Patient Table**
```sql
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_number VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL, -- encrypted
    last_name VARCHAR(100) NOT NULL,  -- encrypted
    middle_name VARCHAR(100),         -- encrypted
    date_of_birth DATE NOT NULL,      -- encrypted
    gender VARCHAR(30) NOT NULL,
    blood_type VARCHAR(10),
    phone_primary VARCHAR(20) NOT NULL, -- encrypted
    phone_secondary VARCHAR(20),        -- encrypted
    email VARCHAR(255),                 -- encrypted
    address JSONB,                      -- encrypted
    national_id VARCHAR(50) UNIQUE,     -- encrypted
    marital_status VARCHAR(20),
    occupation VARCHAR(100),
    photo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_patients_number ON patients(patient_number);
CREATE INDEX idx_patients_dob ON patients(date_of_birth);
CREATE INDEX idx_patients_created_by ON patients(created_by);
```

**Emergency Contact Table**
```sql
CREATE TABLE emergency_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    address TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_emergency_contacts_patient ON emergency_contacts(patient_id);
```

**Insurance Table**
```sql
CREATE TABLE insurance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    provider_name VARCHAR(200) NOT NULL,
    policy_number VARCHAR(100) UNIQUE NOT NULL,
    group_number VARCHAR(100),
    policy_holder_name VARCHAR(200),
    relationship_to_patient VARCHAR(50),
    coverage_start_date DATE NOT NULL,
    coverage_end_date DATE,
    copay_amount DECIMAL(10,2),
    coverage_percentage DECIMAL(5,2),
    max_coverage DECIMAL(12,2),
    is_active BOOLEAN DEFAULT TRUE,
    verification_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_insurance_patient ON insurance(patient_id);
CREATE INDEX idx_insurance_policy ON insurance(policy_number);
```

**Allergy Table**
```sql
CREATE TABLE allergies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    allergen VARCHAR(200) NOT NULL,
    allergen_type VARCHAR(50) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    reaction TEXT,
    onset_date DATE,
    notes TEXT,
    recorded_by UUID REFERENCES users(id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_allergies_patient ON allergies(patient_id);
CREATE INDEX idx_allergies_severity ON allergies(severity);
```

**Medical History Table**
```sql
CREATE TABLE medical_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    condition VARCHAR(200) NOT NULL,
    icd_10_code VARCHAR(20),
    diagnosed_date DATE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    notes TEXT,
    recorded_by UUID REFERENCES users(id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medical_history_patient ON medical_history(patient_id);
CREATE INDEX idx_medical_history_status ON medical_history(status);
```

#### 3.1.3 Electronic Medical Records (EMR)

**Encounter Table**
```sql
CREATE TABLE encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES users(id),
    encounter_type VARCHAR(30) NOT NULL,
    appointment_id UUID REFERENCES appointments(id),
    admission_id UUID REFERENCES admissions(id),
    chief_complaint TEXT,
    symptoms JSONB,
    vital_signs JSONB,
    encounter_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'IN_PROGRESS',
    department_id UUID REFERENCES departments(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signed_at TIMESTAMP,
    signed_by UUID REFERENCES users(id)
);

CREATE INDEX idx_encounters_patient ON encounters(patient_id);
CREATE INDEX idx_encounters_doctor ON encounters(doctor_id);
CREATE INDEX idx_encounters_date ON encounters(encounter_date);
CREATE INDEX idx_encounters_status ON encounters(status);
```

**Diagnosis Table**
```sql
CREATE TABLE diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID REFERENCES encounters(id) ON DELETE CASCADE,
    icd_10_code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    diagnosis_type VARCHAR(20) NOT NULL,
    certainty VARCHAR(20) NOT NULL,
    notes TEXT,
    diagnosed_by UUID REFERENCES users(id),
    diagnosed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diagnoses_encounter ON diagnoses(encounter_id);
CREATE INDEX idx_diagnoses_icd ON diagnoses(icd_10_code);
```

**Procedure Table**
```sql
CREATE TABLE procedures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID REFERENCES encounters(id) ON DELETE CASCADE,
    cpt_code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    procedure_date TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    notes TEXT,
    performed_by UUID REFERENCES users(id),
    assisted_by JSONB,
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    complications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_procedures_encounter ON procedures(encounter_id);
CREATE INDEX idx_procedures_date ON procedures(procedure_date);
```

**Clinical Note Table**
```sql
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID REFERENCES encounters(id) ON DELETE CASCADE,
    note_type VARCHAR(30) NOT NULL,
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,
    content TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signed BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMP,
    is_locked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_clinical_notes_encounter ON clinical_notes(encounter_id);
CREATE INDEX idx_clinical_notes_type ON clinical_notes(note_type);
```

**Prescription Table**
```sql
CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_number VARCHAR(50) UNIQUE NOT NULL,
    encounter_id UUID REFERENCES encounters(id),
    patient_id UUID REFERENCES patients(id),
    prescribed_by UUID REFERENCES users(id),
    prescription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PENDING',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX idx_prescriptions_encounter ON prescriptions(encounter_id);
CREATE INDEX idx_prescriptions_status ON prescriptions(status);
```

**Prescription Item Table**
```sql
CREATE TABLE prescription_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID REFERENCES prescriptions(id) ON DELETE CASCADE,
    drug_id UUID REFERENCES drugs(id),
    quantity INTEGER NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    duration_days INTEGER NOT NULL,
    route VARCHAR(50) NOT NULL,
    instructions TEXT,
    refills_allowed INTEGER DEFAULT 0,
    dispensed BOOLEAN DEFAULT FALSE,
    dispensed_at TIMESTAMP,
    dispensed_by UUID REFERENCES users(id)
);

CREATE INDEX idx_prescription_items_prescription ON prescription_items(prescription_id);
CREATE INDEX idx_prescription_items_drug ON prescription_items(drug_id);
```



#### 3.1.4 Appointments & Scheduling

**Doctor Schedule Table**
```sql
CREATE TABLE doctor_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INTEGER DEFAULT 30,
    max_patients_per_slot INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_until DATE,
    CONSTRAINT check_time_order CHECK (start_time < end_time)
);

CREATE INDEX idx_doctor_schedules_doctor ON doctor_schedules(doctor_id);
CREATE INDEX idx_doctor_schedules_dow ON doctor_schedules(day_of_week);
```

**Doctor Leave Table**
```sql
CREATE TABLE doctor_leaves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID REFERENCES users(id) ON DELETE CASCADE,
    leave_type VARCHAR(30) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    approved_by UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_leave_dates CHECK (start_date <= end_date)
);

CREATE INDEX idx_doctor_leaves_doctor ON doctor_leaves(doctor_id);
CREATE INDEX idx_doctor_leaves_dates ON doctor_leaves(start_date, end_date);
```

**Appointment Table**
```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES users(id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    slot_duration INTEGER DEFAULT 30,
    appointment_type VARCHAR(30) NOT NULL,
    department_id UUID REFERENCES departments(id),
    reason TEXT,
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    is_emergency BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 3,
    notes TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cancelled_reason TEXT,
    cancelled_by UUID REFERENCES users(id)
);

CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_appointments_date ON appointments(appointment_date, appointment_time);
CREATE INDEX idx_appointments_status ON appointments(status);
```

**Queue Table**
```sql
CREATE TABLE queues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID REFERENCES appointments(id),
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES users(id),
    department_id UUID REFERENCES departments(id),
    queue_number INTEGER NOT NULL,
    queue_date DATE NOT NULL,
    queue_type VARCHAR(20) NOT NULL,
    checked_in_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    called_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'WAITING'
);

CREATE INDEX idx_queues_doctor_date ON queues(doctor_id, queue_date);
CREATE INDEX idx_queues_status ON queues(status);
```

#### 3.1.5 Pharmacy Management

**Drug Table**
```sql
CREATE TABLE drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_code VARCHAR(50) UNIQUE NOT NULL,
    generic_name VARCHAR(200) NOT NULL,
    brand_name VARCHAR(200),
    drug_category VARCHAR(100),
    drug_class VARCHAR(100),
    dosage_form VARCHAR(50) NOT NULL,
    strength VARCHAR(50),
    unit_of_measure VARCHAR(20),
    manufacturer VARCHAR(200),
    is_prescription_required BOOLEAN DEFAULT TRUE,
    is_controlled_substance BOOLEAN DEFAULT FALSE,
    storage_conditions TEXT,
    side_effects TEXT,
    contraindications TEXT,
    reorder_level INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_drugs_code ON drugs(drug_code);
CREATE INDEX idx_drugs_generic ON drugs(generic_name);
CREATE INDEX idx_drugs_category ON drugs(drug_category);
```

**Drug Batch Table**
```sql
CREATE TABLE drug_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_id UUID REFERENCES drugs(id) ON DELETE CASCADE,
    batch_number VARCHAR(100) UNIQUE NOT NULL,
    manufacture_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    purchase_date DATE NOT NULL,
    quantity_received INTEGER NOT NULL,
    quantity_available INTEGER NOT NULL,
    cost_per_unit DECIMAL(10,2) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    supplier_id UUID REFERENCES suppliers(id),
    location VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_quantity CHECK (quantity_available <= quantity_received)
);

CREATE INDEX idx_drug_batches_drug ON drug_batches(drug_id);
CREATE INDEX idx_drug_batches_expiry ON drug_batches(expiry_date);
CREATE INDEX idx_drug_batches_batch ON drug_batches(batch_number);
```

**Pharmacy Dispensing Table**
```sql
CREATE TABLE pharmacy_dispensing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispensing_number VARCHAR(50) UNIQUE NOT NULL,
    prescription_id UUID REFERENCES prescriptions(id),
    patient_id UUID REFERENCES patients(id),
    dispensed_by UUID REFERENCES users(id),
    dispensing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    notes TEXT
);

CREATE INDEX idx_dispensing_prescription ON pharmacy_dispensing(prescription_id);
CREATE INDEX idx_dispensing_patient ON pharmacy_dispensing(patient_id);
CREATE INDEX idx_dispensing_date ON pharmacy_dispensing(dispensing_date);
```

**Dispensing Item Table**
```sql
CREATE TABLE dispensing_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispensing_id UUID REFERENCES pharmacy_dispensing(id) ON DELETE CASCADE,
    drug_batch_id UUID REFERENCES drug_batches(id),
    quantity_dispensed INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    instructions TEXT
);

CREATE INDEX idx_dispensing_items_dispensing ON dispensing_items(dispensing_id);
CREATE INDEX idx_dispensing_items_batch ON dispensing_items(drug_batch_id);
```

**Drug Stock Movement Table**
```sql
CREATE TABLE drug_stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_batch_id UUID REFERENCES drug_batches(id),
    movement_type VARCHAR(30) NOT NULL,
    quantity INTEGER NOT NULL,
    reference_id UUID,
    reason TEXT,
    performed_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_movements_batch ON drug_stock_movements(drug_batch_id);
CREATE INDEX idx_stock_movements_date ON drug_stock_movements(created_at);
```

#### 3.1.6 Laboratory Management (LIMS)

**Lab Test Catalog Table**
```sql
CREATE TABLE lab_test_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_code VARCHAR(50) UNIQUE NOT NULL,
    test_name VARCHAR(200) NOT NULL,
    test_category VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    sample_type VARCHAR(50) NOT NULL,
    tat_hours INTEGER DEFAULT 24,
    cost DECIMAL(10,2) NOT NULL,
    normal_range JSONB,
    method TEXT,
    preparation_instructions TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lab_catalog_code ON lab_test_catalog(test_code);
CREATE INDEX idx_lab_catalog_category ON lab_test_catalog(test_category);
```

**Lab Order Table**
```sql
CREATE TABLE lab_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    encounter_id UUID REFERENCES encounters(id),
    patient_id UUID REFERENCES patients(id),
    ordered_by UUID REFERENCES users(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority VARCHAR(20) DEFAULT 'ROUTINE',
    clinical_notes TEXT,
    specimen_collected BOOLEAN DEFAULT FALSE,
    specimen_collected_at TIMESTAMP,
    collected_by UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'PENDING'
);

CREATE INDEX idx_lab_orders_patient ON lab_orders(patient_id);
CREATE INDEX idx_lab_orders_encounter ON lab_orders(encounter_id);
CREATE INDEX idx_lab_orders_status ON lab_orders(status);
CREATE INDEX idx_lab_orders_date ON lab_orders(order_date);
```

**Lab Order Item Table**
```sql
CREATE TABLE lab_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lab_order_id UUID REFERENCES lab_orders(id) ON DELETE CASCADE,
    test_id UUID REFERENCES lab_test_catalog(id),
    specimen_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PENDING',
    rejection_reason TEXT,
    performed_by UUID REFERENCES users(id),
    verified_by UUID REFERENCES users(id)
);

CREATE INDEX idx_lab_order_items_order ON lab_order_items(lab_order_id);
CREATE INDEX idx_lab_order_items_test ON lab_order_items(test_id);
CREATE INDEX idx_lab_order_items_specimen ON lab_order_items(specimen_id);
```

**Lab Result Table**
```sql
CREATE TABLE lab_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_item_id UUID REFERENCES lab_order_items(id) ON DELETE CASCADE,
    parameter VARCHAR(100) NOT NULL,
    value VARCHAR(200) NOT NULL,
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    is_abnormal BOOLEAN DEFAULT FALSE,
    abnormal_flag VARCHAR(20),
    notes TEXT,
    result_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    report_url VARCHAR(500),
    is_locked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_lab_results_order_item ON lab_results(order_item_id);
CREATE INDEX idx_lab_results_abnormal ON lab_results(is_abnormal);
```

#### 3.1.7 Billing & Invoicing

**Invoice Table**
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    encounter_id UUID REFERENCES encounters(id),
    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    discount_amount DECIMAL(12,2) DEFAULT 0,
    net_amount DECIMAL(12,2) NOT NULL,
    paid_amount DECIMAL(12,2) DEFAULT 0,
    balance DECIMAL(12,2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'UNPAID',
    payment_method VARCHAR(30),
    insurance_claim_id UUID REFERENCES insurance_claims(id),
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_patient ON invoices(patient_id);
CREATE INDEX idx_invoices_encounter ON invoices(encounter_id);
CREATE INDEX idx_invoices_status ON invoices(payment_status);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
```

**Invoice Line Item Table**
```sql
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    item_type VARCHAR(30) NOT NULL,
    item_id UUID,
    description TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    tax_percentage DECIMAL(5,2) DEFAULT 0,
    line_total DECIMAL(12,2) NOT NULL
);

CREATE INDEX idx_invoice_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX idx_invoice_items_type ON invoice_line_items(item_type);
```

**Payment Table**
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_id UUID REFERENCES invoices(id),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    transaction_reference VARCHAR(200),
    received_by UUID REFERENCES users(id),
    notes TEXT,
    receipt_url VARCHAR(500)
);

CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
```

**Insurance Claim Table**
```sql
CREATE TABLE insurance_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    insurance_id UUID REFERENCES insurance(id),
    encounter_id UUID REFERENCES encounters(id),
    invoice_id UUID REFERENCES invoices(id),
    claim_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    claim_amount DECIMAL(12,2) NOT NULL,
    approved_amount DECIMAL(12,2),
    rejected_amount DECIMAL(12,2),
    status VARCHAR(30) DEFAULT 'SUBMITTED',
    submission_date TIMESTAMP,
    response_date TIMESTAMP,
    rejection_reason TEXT,
    documents JSONB
);

CREATE INDEX idx_claims_patient ON insurance_claims(patient_id);
CREATE INDEX idx_claims_insurance ON insurance_claims(insurance_id);
CREATE INDEX idx_claims_status ON insurance_claims(status);
```

#### 3.1.8 Inpatient Management

**Ward Table**
```sql
CREATE TABLE wards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ward_code VARCHAR(50) UNIQUE NOT NULL,
    ward_name VARCHAR(200) NOT NULL,
    ward_type VARCHAR(50) NOT NULL,
    floor INTEGER,
    department_id UUID REFERENCES departments(id),
    total_beds INTEGER NOT NULL,
    available_beds INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_wards_code ON wards(ward_code);
CREATE INDEX idx_wards_type ON wards(ward_type);
```

**Bed Table**
```sql
CREATE TABLE beds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bed_number VARCHAR(50) NOT NULL,
    ward_id UUID REFERENCES wards(id) ON DELETE CASCADE,
    bed_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE',
    daily_charge DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(ward_id, bed_number)
);

CREATE INDEX idx_beds_ward ON beds(ward_id);
CREATE INDEX idx_beds_status ON beds(status);
```

**Admission Table**
```sql
CREATE TABLE admissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    encounter_id UUID REFERENCES encounters(id),
    admitting_doctor_id UUID REFERENCES users(id),
    admission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admission_type VARCHAR(30) NOT NULL,
    admission_diagnosis TEXT,
    current_ward_id UUID REFERENCES wards(id),
    current_bed_id UUID REFERENCES beds(id),
    status VARCHAR(20) DEFAULT 'ADMITTED',
    discharge_date TIMESTAMP,
    discharge_type VARCHAR(30),
    discharge_summary TEXT,
    discharge_instructions TEXT,
    discharge_medications JSONB,
    follow_up_date DATE
);

CREATE INDEX idx_admissions_patient ON admissions(patient_id);
CREATE INDEX idx_admissions_bed ON admissions(current_bed_id);
CREATE INDEX idx_admissions_status ON admissions(status);
CREATE INDEX idx_admissions_date ON admissions(admission_date);
```

**Bed Transfer Table**
```sql
CREATE TABLE bed_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID REFERENCES admissions(id) ON DELETE CASCADE,
    from_bed_id UUID REFERENCES beds(id),
    to_bed_id UUID REFERENCES beds(id),
    transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    ordered_by UUID REFERENCES users(id),
    executed_by UUID REFERENCES users(id)
);

CREATE INDEX idx_bed_transfers_admission ON bed_transfers(admission_id);
```

#### 3.1.9 Audit & Supporting Tables

**Audit Log Table**
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    changes JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id UUID
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

**Document Attachment Table**
```sql
CREATE TABLE document_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(100),
    file_url VARCHAR(1000) NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE INDEX idx_documents_entity ON document_attachments(entity_type, entity_id);
CREATE INDEX idx_documents_type ON document_attachments(document_type);
```

**Department Table**
```sql
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(200) NOT NULL,
    department_type VARCHAR(50),
    head_of_department UUID REFERENCES users(id),
    phone VARCHAR(20),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_departments_code ON departments(department_code);
```

**Supplier Table**
```sql
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_code VARCHAR(50) UNIQUE NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    contact_person VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(255),
    address JSONB,
    payment_terms TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_suppliers_code ON suppliers(supplier_code);
```

**Notification Table**
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID REFERENCES users(id),
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created ON notifications(created_at);
```

---

## 4. Authentication & Authorization

### 4.1 Authentication Flow

**JWT Token Strategy**

The system uses a dual-token approach for security and user experience:

1. **Access Token**: 
   - Short-lived (15-30 minutes)
   - Contains user claims and permissions
   - Used for API authentication
   - Signed with HS256 algorithm

2. **Refresh Token**:
   - Long-lived (7-30 days)
   - Stored in Redis with device information
   - Used to obtain new access tokens
   - Supports device-specific revocation

**Token Payload Structure**
```json
{
  "sub": "user_uuid",
  "username": "dr.smith",
  "email": "dr.smith@hospital.com",
  "role": "DOCTOR",
  "permissions": [
    "patients:read",
    "patients:read:department",
    "emr:write",
    "prescriptions:create",
    "appointments:read:own"
  ],
  "department_id": "dept_uuid",
  "iat": 1702630800,
  "exp": 1702632600,
  "jti": "token_uuid",
  "token_type": "access"
}
```

### 4.2 Authorization Strategy

**Three-Layer Authorization Model**

**Layer 1: Role-Based Access Control (RBAC)**
- Coarse-grained permissions assigned to roles
- Example: `DOCTOR` role automatically gets `emr:write` permission

**Layer 2: Resource-Based Authorization**
- Fine-grained checks on specific resources
- Example: Doctors can only view patients assigned to their department

**Layer 3: Attribute-Based Access Control (ABAC)**
- Context-aware permissions based on attributes
- Example: EMR records can only be edited within 24 hours of creation

### 4.3 Permission Format

**Pattern**: `resource:action[:scope]`

**Examples**:
- `patients:read:own` - Read only own patients
- `patients:read:department` - Read patients in same department
- `patients:read:all` - Read all patients
- `patients:write:own` - Update only own patients
- `emr:write` - Write EMR entries
- `emr:sign` - Sign and lock EMR entries
- `pharmacy:dispense` - Dispense medications
- `billing:payment` - Process payments
- `reports:financial` - View financial reports

### 4.4 Standard Role Definitions

**SUPER_ADMIN**
```python
permissions = ["*:*:*"]  # All permissions
```

**HOSPITAL_ADMIN**
```python
permissions = [
    "users:*",
    "roles:*",
    "departments:*",
    "suppliers:*",
    "reports:*",
    "system:*"
]
```

**DOCTOR**
```python
permissions = [
    "patients:read:department",
    "patients:read:own",
    "appointments:read:own",
    "appointments:update:own",
    "emr:*",
    "prescriptions:*",
    "lab:order",
    "diagnoses:*",
    "procedures:*",
    "clinical_notes:*",
    "billing:read"
]
```

**NURSE**
```python
permissions = [
    "patients:read:department",
    "appointments:read:department",
    "appointments:update:department",
    "emr:read:department",
    "emr:update_vitals",
    "prescriptions:read",
    "prescriptions:administer",
    "lab:collect_specimen",
    "queue:manage"
]
```

**PHARMACIST**
```python
permissions = [
    "patients:read",
    "prescriptions:read",
    "prescriptions:verify",
    "pharmacy:*",
    "drugs:*",
    "inventory:*"
]
```

**LAB_TECHNICIAN**
```python
permissions = [
    "patients:read",
    "lab:*",
    "specimens:*",
    "results:enter"
]
```

**RECEPTIONIST**
```python
permissions = [
    "patients:*",
    "appointments:*",
    "queue:manage",
    "billing:read"
]
```

**ACCOUNTANT**
```python
permissions = [
    "patients:read",
    "billing:*",
    "invoices:*",
    "payments:*",
    "insurance_claims:*",
    "reports:financial"
]
```

**PATIENT** (Portal Access)
```python
permissions = [
    "patients:read:own",
    "appointments:read:own",
    "appointments:create:own",
    "appointments:cancel:own",
    "emr:read:own",
    "prescriptions:read:own",
    "lab_results:read:own",
    "invoices:read:own",
    "payments:read:own"
]
```

### 4.5 Authentication Endpoints

**POST** `/api/v1/auth/login`
```json
Request:
{
  "username": "dr.smith",
  "password": "SecureP@ssw0rd!"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "username": "dr.smith",
    "email": "dr.smith@hospital.com",
    "role": "DOCTOR",
    "department": "Cardiology"
  }
}
```

**POST** `/api/v1/auth/refresh`
```json
Request:
{
  "refresh_token": "eyJhbGc..."
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 5. API Endpoints by Module

### 5.1 Authentication & User Management

**Base Path**: `/api/v1/auth`

| Method | Endpoint | Description | Auth Required | Permissions |
|--------|----------|-------------|---------------|-------------|
| POST | `/register` | Register new user account | No | Public |
| POST | `/login` | Login and get tokens | No | Public |
| POST | `/refresh` | Refresh access token | Yes | Refresh Token |
| POST | `/logout` | Logout and revoke tokens | Yes | Authenticated |
| POST | `/logout-all` | Logout from all devices | Yes | Authenticated |
| POST | `/forgot-password` | Request password reset | No | Public |
| POST | `/reset-password` | Reset password with token | No | Public |
| POST | `/verify-email` | Verify email address | No | Public |
| GET | `/me` | Get current user profile | Yes | Authenticated |
| PATCH | `/me` | Update current user profile | Yes | Authenticated |
| GET | `/sessions` | Get active sessions | Yes | Authenticated |
| DELETE | `/sessions/{id}` | Revoke specific session | Yes | Authenticated |

**User Management** - `/api/v1/users`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Create new user | `users:create` |
| GET | `/` | List users (paginated, filtered) | `users:read` |
| GET | `/{id}` | Get user by ID | `users:read` |
| PATCH | `/{id}` | Update user | `users:update` |
| DELETE | `/{id}` | Deactivate user | `users:delete` |
| POST | `/{id}/activate` | Activate user | `users:update` |
| POST | `/{id}/reset-password` | Admin reset password | `users:update` |
| GET | `/{id}/permissions` | Get user permissions | `users:read` |
| PUT | `/{id}/permissions` | Update user permissions | `users:update` |

---

### 5.2 Patient Management

**Base Path**: `/api/v1/patients`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Register new patient | `patients:create` |
| GET | `/` | List patients (paginated, searchable) | `patients:read` |
| GET | `/{id}` | Get patient by ID | `patients:read` |
| PATCH | `/{id}` | Update patient details | `patients:update` |
| DELETE | `/{id}` | Soft delete patient | `patients:delete` |
| GET | `/{id}/summary` | Patient summary dashboard | `patients:read` |
| POST | `/{id}/photo` | Upload patient photo | `patients:update` |
| GET | `/search` | Advanced patient search | `patients:read` |

**Query Parameters for List/Search**:
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20, max: 100)
- `search` (string): Search by name, ID, phone
- `gender` (enum): Filter by gender
- `blood_type` (string): Filter by blood type
- `is_active` (bool): Filter active/inactive
- `created_after` (date): Filter by registration date
- `sort_by` (string): Sort field (default: created_at)
- `sort_order` (enum): asc/desc (default: desc)

**Emergency Contacts** - `/api/v1/patients/{patient_id}/emergency-contacts`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| GET | `/` | List emergency contacts | `patients:read` |
| POST | `/` | Add emergency contact | `patients:update` |
| PATCH | `/{id}` | Update emergency contact | `patients:update` |
| DELETE | `/{id}` | Remove emergency contact | `patients:update` |

**Insurance** - `/api/v1/patients/{patient_id}/insurance`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| GET | `/` | List insurance policies | `patients:read` |
| POST | `/` | Add insurance | `patients:update` |
| PATCH | `/{id}` | Update insurance | `patients:update` |
| DELETE | `/{id}` | Deactivate insurance | `patients:update` |
| POST | `/{id}/verify` | Verify insurance eligibility | `insurance:verify` |

---

### 5.3 Appointments & Scheduling

**Appointments** - `/api/v1/appointments`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Book appointment | `appointments:create` |
| GET | `/` | List appointments | `appointments:read` |
| GET | `/{id}` | Get appointment details | `appointments:read` |
| PATCH | `/{id}` | Update appointment | `appointments:update` |
| DELETE | `/{id}` | Cancel appointment | `appointments:delete` |
| POST | `/{id}/confirm` | Confirm appointment | `appointments:update` |
| POST | `/{id}/check-in` | Check-in patient | `appointments:update` |
| POST | `/{id}/reschedule` | Reschedule appointment | `appointments:update` |
| GET | `/available-slots` | Get available time slots | Public |
| GET | `/today` | Today's appointments | `appointments:read` |

---

### 5.4 Electronic Medical Records (EMR)

**Encounters** - `/api/v1/emr/encounters`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Create encounter | `emr:create` |
| GET | `/` | List encounters | `emr:read` |
| GET | `/{id}` | Get encounter details | `emr:read` |
| PATCH | `/{id}` | Update encounter | `emr:update` |
| POST | `/{id}/sign` | Sign and lock encounter | `emr:sign` |
| GET | `/patient/{patient_id}` | Patient encounter history | `emr:read` |
| POST | `/{id}/vitals` | Record vital signs | `emr:update` |

**Prescriptions** - `/api/v1/emr/prescriptions`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Create prescription | `prescriptions:create` |
| GET | `/` | List prescriptions | `prescriptions:read` |
| GET | `/{id}` | Get prescription details | `prescriptions:read` |
| PATCH | `/{id}` | Update prescription | `prescriptions:update` |
| POST | `/{id}/cancel` | Cancel prescription | `prescriptions:update` |
| GET | `/{id}/print` | Generate printable prescription | `prescriptions:read` |

---

### 5.5 Pharmacy Management

**Drugs** - `/api/v1/pharmacy/drugs`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Add new drug | `pharmacy:manage` |
| GET | `/` | List drugs | `pharmacy:read` |
| GET | `/{id}` | Get drug details | `pharmacy:read` |
| PATCH | `/{id}` | Update drug | `pharmacy:manage` |
| GET | `/search` | Search drugs | `pharmacy:read` |
| GET | `/low-stock` | Drugs below reorder level | `pharmacy:read` |
| GET | `/expiring` | Drugs expiring within 90 days | `pharmacy:read` |

**Dispensing** - `/api/v1/pharmacy/dispensing`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Dispense medication | `pharmacy:dispense` |
| GET | `/` | List dispensing records | `pharmacy:read` |
| GET | `/{id}` | Get dispensing details | `pharmacy:read` |
| GET | `/pending` | Pending prescriptions | `pharmacy:read` |
| GET | `/{id}/receipt` | Generate receipt | `pharmacy:read` |

---

### 5.6 Laboratory Management (LIMS)

**Lab Orders** - `/api/v1/lab/orders`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Create lab order | `lab:order` |
| GET | `/` | List lab orders | `lab:read` |
| GET | `/{id}` | Get order details | `lab:read` |
| POST | `/{id}/cancel` | Cancel order | `lab:update` |
| GET | `/patient/{patient_id}` | Patient lab history | `lab:read` |
| GET | `/pending` | Pending orders | `lab:read` |

**Results** - `/api/v1/lab/results`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Enter test result | `lab:process` |
| GET | `/order/{order_id}` | Get results for order | `lab:read` |
| PATCH | `/{id}` | Update result | `lab:process` |
| POST | `/{id}/verify` | Verify result | `lab:verify` |
| GET | `/{id}/report` | Generate PDF report | `lab:read` |

---

### 5.7 Billing & Invoicing

**Invoices** - `/api/v1/billing/invoices`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Create invoice | `billing:create` |
| GET | `/` | List invoices | `billing:read` |
| GET | `/{id}` | Get invoice details | `billing:read` |
| PATCH | `/{id}` | Update invoice | `billing:update` |
| POST | `/{id}/finalize` | Finalize draft invoice | `billing:update` |
| GET | `/{id}/pdf` | Generate PDF invoice | `billing:read` |
| GET | `/outstanding` | Outstanding invoices | `billing:read` |

**Payments** - `/api/v1/billing/payments`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Record payment | `billing:payment` |
| GET | `/` | List payments | `billing:read` |
| GET | `/{id}` | Get payment details | `billing:read` |
| POST | `/{id}/refund` | Process refund | `billing:refund` |
| GET | `/{id}/receipt` | Generate receipt | `billing:read` |

---

### 5.8 Inpatient Management

**Admissions** - `/api/v1/inpatient/admissions`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| POST | `/` | Admit patient | `admissions:create` |
| GET | `/` | List admissions | `admissions:read` |
| GET | `/{id}` | Get admission details | `admissions:read` |
| POST | `/{id}/discharge` | Discharge patient | `admissions:discharge` |
| POST | `/{id}/transfer` | Transfer to another bed | `admissions:transfer` |
| GET | `/active` | Currently admitted patients | `admissions:read` |

---

### 5.9 Reports & Analytics

**Base Path**: `/api/v1/reports`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|------------|
| GET | `/dashboard` | Dashboard statistics | `reports:read` |
| GET | `/revenue` | Revenue report | `reports:financial` |
| GET | `/appointments` | Appointment statistics | `reports:read` |
| GET | `/bed-occupancy` | Bed occupancy report | `reports:read` |
| GET | `/lab-utilization` | Lab utilization report | `reports:read` |

---

## 6. Functional Requirements

### 6.1 Patient Management

**FR-PM-001: Patient Registration**
- System SHALL generate unique patient ID automatically (format: PT-YYYYMMDD-XXXX)
- System SHALL encrypt all PII fields (name, DOB, address, phone, email, national ID)
- System SHALL validate national ID uniqueness
- System SHALL support bulk import via CSV with validation
- System SHALL maintain complete audit trail of patient data changes

**FR-PM-002: Patient Search**
- System SHALL support fuzzy search on patient names
- System SHALL search by: name, patient ID, phone, DOB, national ID
- System SHALL implement field-level access control (role-based data masking)
- System SHALL return paginated results (default 20, max 100 per page)
- System SHALL return search results within 2 seconds for 100K+ patients

**FR-PM-003: Allergy Management**
- System SHALL display prominent allergy alerts during prescribing
- System SHALL check drug-allergy interactions before prescription approval
- System SHALL support allergy severity grading (MILD, MODERATE, SEVERE, LIFE_THREATENING)
- System SHALL require acknowledgment of critical allergy alerts

---

### 6.2 Appointment & Scheduling

**FR-AS-001: Schedule Management**
- System SHALL prevent double-booking of time slots (optimistic locking)
- System SHALL support recurring schedule patterns
- System SHALL handle doctor leave/unavailability with appointment rescheduling
- System SHALL reserve 20% slots for emergency appointments

**FR-AS-002: Appointment Booking**
- System SHALL display only available slots
- System SHALL implement race condition prevention (database-level locks)
- System SHALL support same-day appointments
- System SHALL allow rescheduling up to 24 hours before appointment
- System SHALL track no-show patterns (auto-flag after 3 consecutive no-shows)

**FR-AS-003: Appointment Reminders**
- System SHALL send SMS reminder 24 hours before appointment
- System SHALL send email reminder 24 hours before appointment
- System SHALL retry failed notifications up to 3 times
- System SHALL log all notification attempts with delivery status

---

### 6.3 Electronic Medical Records (EMR)

**FR-EMR-001: Encounter Management**
- System SHALL link encounters to appointments or admissions
- System SHALL auto-populate patient demographics
- System SHALL require doctor signature for completion
- System SHALL make signed encounters immutable (append-only)
- System SHALL support encounter amendments within 24 hours (with audit trail)

**FR-EMR-002: Clinical Notes**
- System SHALL support SOAP, Progress, Discharge note types
- System SHALL auto-save notes every 30 seconds (draft state)
- System SHALL support collaborative editing with conflict resolution
- System SHALL make signed notes immutable
- System SHALL track all note revisions

**FR-EMR-003: Prescription Generation**
- System SHALL check drug-allergy interactions
- System SHALL check drug-drug interactions
- System SHALL validate dosage against standard ranges (by age/weight)
- System SHALL alert for duplicate active prescriptions
- System SHALL support electronic signature

**FR-EMR-004: Vital Signs**
- System SHALL record: BP, HR, Temp, RR, SpO2, Weight, Height
- System SHALL auto-calculate BMI
- System SHALL flag abnormal vitals (color-coded alerts)
- System SHALL maintain vital sign trends (graphical display)

---

### 6.4 Pharmacy Management

**FR-PH-001: Drug Inventory**
- System SHALL track drug batches with FIFO dispensing
- System SHALL alert when stock reaches reorder level
- System SHALL alert 90 days before expiry
- System SHALL auto-deactivate expired batches
- System SHALL maintain complete stock movement history

**FR-PH-002: Prescription Dispensing**
- System SHALL verify prescription validity (not expired, not dispensed)
- System SHALL auto-select batches using FIFO + nearest expiry
- System SHALL update stock atomically (transaction-safe)
- System SHALL generate dispensing receipt
- System SHALL support partial dispensing

**FR-PH-003: Drug Interaction Checks**
- System SHALL check against patient allergies
- System SHALL check drug-drug interactions
- System SHALL display interaction severity (MINOR, MODERATE, SEVERE)
- System SHALL require pharmacist override for critical warnings

---

### 6.5 Laboratory Management

**FR-LAB-001: Lab Order Management**
- System SHALL support individual tests and test panels
- System SHALL generate unique specimen barcodes
- System SHALL track specimen collection status
- System SHALL prioritize STAT orders in queue

**FR-LAB-002: Result Entry & Verification**
- System SHALL validate results against reference ranges
- System SHALL auto-flag abnormal results
- System SHALL require dual verification (technician + pathologist)
- System SHALL make verified results immutable
- System SHALL trigger critical result notifications immediately

**FR-LAB-003: Result Reporting**
- System SHALL generate PDF reports with hospital branding
- System SHALL include historical result comparison
- System SHALL notify ordering doctor upon verification
- System SHALL support result export to EMR

---

### 6.6 Billing Requirements

**FR-BL-001: Invoice Generation**
- System SHALL auto-generate invoices from encounters
- System SHALL itemize charges by category
- System SHALL calculate taxes per jurisdiction
- System SHALL support discount application (with approval workflow)

**FR-BL-002: Payment Processing**
- System SHALL support multiple payment methods
- System SHALL support partial payments
- System SHALL auto-calculate outstanding balance
- System SHALL generate receipts immediately

**FR-BL-003: Insurance Claims**
- System SHALL validate insurance eligibility
- System SHALL auto-generate claim forms
- System SHALL track claim status
- System SHALL handle partial approvals

---

### 6.7 Inpatient Requirements

**FR-IP-001: Bed Management**
- System SHALL track bed status in real-time
- System SHALL prevent double-allocation (database locks)
- System SHALL calculate occupancy rates
- System SHALL predict bed availability

**FR-IP-002: Admission Process**
- System SHALL allocate bed atomically
- System SHALL link admission to encounter
- System SHALL trigger automatic billing

**FR-IP-003: Discharge Process**
- System SHALL require discharge summary
- System SHALL create discharge medication list
- System SHALL schedule follow-up appointments
- System SHALL release bed upon discharge
- System SHALL generate final billing

---

## 7. Non-Functional Requirements

### 7.1 Performance Requirements

**NFR-PERF-001: Response Time**
- 95% of API requests SHALL respond within 500ms
- 99% of API requests SHALL respond within 2 seconds
- Search queries SHALL return results within 1 second for 100K+ records

**NFR-PERF-002: Throughput**
- System SHALL handle 500 concurrent users
- System SHALL process 10,000 transactions per hour
- System SHALL support 100 requests per second sustained load

**NFR-PERF-003: Scalability**
- System SHALL scale horizontally (stateless application design)
- System SHALL use Redis for distributed session storage
- System SHALL use read replicas for reporting queries

---

### 7.2 Reliability Requirements

**NFR-REL-001: Availability**
- System SHALL maintain 99.9% uptime (max 8.76 hours downtime/year)
- System SHALL support zero-downtime deployments
- System SHALL implement automated failover

**NFR-REL-002: Data Integrity**
- System SHALL use database transactions for multi-step operations
- System SHALL implement optimistic locking for concurrent updates
- System SHALL perform automated daily backups
- System SHALL maintain 30-day backup retention

**NFR-REL-003: Fault Tolerance**
- System SHALL retry failed API calls with exponential backoff
- System SHALL queue background jobs persistently
- System SHALL handle database connection pool exhaustion gracefully

---

### 7.3 Security Requirements

**NFR-SEC-001: Authentication**
- System SHALL enforce password complexity (min 12 chars, mixed case, numbers, symbols)
- System SHALL lock accounts after 5 failed login attempts
- System SHALL support MFA for privileged accounts
- System SHALL expire passwords every 90 days

**NFR-SEC-002: Data Protection**
- System SHALL encrypt PII at rest (AES-256)
- System SHALL encrypt data in transit (TLS 1.3)
- System SHALL mask sensitive data in logs
- System SHALL support data export requests (GDPR)

---

### 7.4 Compliance Requirements

**NFR-COMP-001: HIPAA Compliance**
- System SHALL encrypt PHI at rest and in transit
- System SHALL implement access controls per minimum necessary rule
- System SHALL maintain audit logs for all PHI access
- System SHALL support breach notification

**NFR-COMP-002: Data Retention**
- System SHALL retain medical records for minimum 7 years
- System SHALL archive inactive records after 3 years
- System SHALL support legal hold on records

---

## 8. Security & Compliance

### 8.1 Security Layers

**Layer 1: Network Security**
- TLS 1.3 for all API communications
- API Gateway with DDoS protection
- IP whitelisting for admin endpoints
- VPN access for internal systems

**Layer 2: Application Security**
- JWT with short expiration (30 min)
- Refresh token rotation
- Rate limiting per user/IP (100 req/min)
- Input validation and sanitization
- SQL injection prevention (ORM usage)
- XSS prevention (output encoding)
- CSRF protection

**Layer 3: Data Security**
- AES-256 encryption for PII at rest
- TLS 1.3 for data in transit
- Database-level encryption
- Encrypted backups
- Secure key management (AWS KMS / HashiCorp Vault)

**Layer 4: Access Control**
- Role-Based Access Control (RBAC)
- Resource-Based Access Control
- Attribute-Based Access Control (ABAC)
- Multi-Factor Authentication (MFA)

### 8.2 Compliance Standards

**HIPAA (Health Insurance Portability and Accountability Act)**
- Privacy Rule: Protect PHI
- Security Rule: Safeguards for ePHI
- Breach Notification Rule: Notify within 60 days

**GDPR (General Data Protection Regulation)**
- Right to access (data export)
- Right to erasure (data deletion)
- Right to portability
- Breach notification (72 hours)

---

## 9. Background Processing

### 9.1 Celery Tasks

**Task Categories**:

1. **Notifications**
   - `send_email_notification(user_id, template, context)`
   - `send_sms_notification(phone, message)`
   - `send_appointment_reminders()` - Cron: hourly

2. **Billing**
   - `generate_invoice(encounter_id)`
   - `send_payment_reminder(invoice_id)`
   - `process_insurance_claim(claim_id)`

3. **Pharmacy**
   - `check_expiring_drugs()` - Cron: daily
   - `check_low_stock()` - Cron: daily
   - `generate_purchase_orders()` - Cron: weekly

4. **Reports**
   - `generate_monthly_statistics()` - Cron: 1st of month
   - `export_audit_logs(start_date, end_date)`

5. **Maintenance**
   - `cleanup_expired_sessions()` - Cron: daily
   - `archive_old_records()` - Cron: weekly
   - `backup_database()` - Cron: daily at 2 AM

### 9.2 Event-Driven Workflows

```python
# Encounter completed → Trigger billing
on_event('encounter.completed') -> [
    generate_invoice(encounter_id),
    notify_patient(patient_id)
]

# Lab result verified → Notify doctor
on_event('lab_result.verified') -> [
    notify_doctor(doctor_id),
    notify_patient(patient_id) if not_critical
]

# Prescription created → Send to pharmacy
on_event('prescription.created') -> [
    notify_pharmacist(prescription_id),
    send_to_pharmacy_system(prescription_id)
]
```

---

## 10. Deployment Architecture

### 10.1 Docker Compose (Development)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/hospital
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      
  celery-worker:
    build: .
    command: celery -A app.workers worker
    depends_on:
      - postgres
      - redis
      - rabbitmq
      
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=hospital
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    
  rabbitmq:
    image: rabbitmq:3-management
```

### 10.2 Kubernetes (Production)

Key manifests:
- Deployment: hospital-api (3 replicas)
- Service: hospital-api-service
- Ingress: HTTPS with cert-manager
- StatefulSet: PostgreSQL, Redis
- HorizontalPodAutoscaler: CPU > 70%
- PersistentVolumeClaim: database storage

---

## 11. Project Structure

```
hospital-management-system/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── permissions.py
│   │   └── events.py
│   ├── api/v1/
│   │   ├── auth/
│   │   ├── patients/
│   │   ├── appointments/
│   │   ├── emr/
│   │   ├── pharmacy/
│   │   ├── lab/
│   │   ├── billing/
│   │   └── inpatient/
│   ├── domain/
│   │   ├── patients/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   └── service.py
│   │   └── [other domains...]
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── storage.py
│   │   └── email.py
│   └── workers/
│       ├── celery_app.py
│       └── tasks.py
├── migrations/
├── tests/
├── docker/
├── docs/
└── scripts/
```

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- Project setup
- Authentication & authorization
- Patient management
- Audit logging

### Phase 2: Clinical Modules (Weeks 5-10)
- Appointments
- EMR core
- Prescriptions

### Phase 3: Support Services (Weeks 11-15)
- Pharmacy
- Laboratory
- Notifications

### Phase 4: Billing & Inpatient (Weeks 16-19)
- Billing
- Inpatient management

### Phase 5: Reporting & Analytics (Weeks 20-22)
- Reports
- Analytics
- Export features

### Phase 6: Testing & Deployment (Weeks 23-26)
- Testing
- Performance optimization
- DevOps
- Production launch

---

## Appendix: Sample API Request/Response

### Create Patient

**Request**:
```http
POST /api/v1/patients
Authorization: Bearer <token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-05-15",
  "gender": "MALE",
  "blood_type": "O+",
  "phone_primary": "+1234567890",
  "email": "john.doe@example.com",
  "national_id": "123-45-6789"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "patient_number": "PT-20241215-0001",
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-05-15",
  "gender": "MALE",
  "blood_type": "O+",
  "phone_primary": "+1234567890",
  "email": "john.doe@example.com",
  "national_id": "***-**-6789",
  "is_active": true,
  "registered_date": "2024-12-15T10:30:00Z",
  "created_at": "2024-12-15T10:30:00Z"
}
```

---

## Conclusion

This FastAPI Hospital Management System provides a comprehensive, production-ready backend architecture designed for real-world healthcare operations. The system emphasizes:

- **Security & Compliance**: HIPAA, GDPR compliance with encryption and audit trails
- **Scalability**: Horizontal scaling, caching, async processing
- **Maintainability**: Clean architecture, comprehensive testing, documentation
- **Real-world Workflows**: Based on actual hospital operations

The modular design allows for incremental implementation while maintaining flexibility for future enhancements.

---

**Document Version**: 1.0  
**Last Updated**: December 2024  
**Author**: Hospital Management System Architecture Team
