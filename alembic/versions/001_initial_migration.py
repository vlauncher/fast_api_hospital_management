"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create crypto extension for encryption functions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), nullable=False, default=sa.text("'[]'::json")),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], )
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)
    
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('patient_number', sa.String(length=20), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', 'OTHER', name='gender'), nullable=False),
        sa.Column('blood_type', sa.Enum('A_POSITIVE', 'A_NEGATIVE', 'B_POSITIVE', 'B_NEGATIVE', 'AB_POSITIVE', 'AB_NEGATIVE', 'O_POSITIVE', 'O_NEGATIVE', name='bloodtype'), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('national_id', sa.Text(), nullable=True),
        sa.Column('passport_number', sa.Text(), nullable=True),
        sa.Column('driver_license', sa.Text(), nullable=True),
        sa.Column('ssn', sa.Text(), nullable=True),
        sa.Column('marital_status', sa.Enum('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', name='maritalstatus'), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=200), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
        sa.Column('emergency_contact_relationship', sa.String(length=100), nullable=True),
        sa.Column('primary_care_physician', sa.String(length=200), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('medical_conditions', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('insurance_provider', sa.String(length=200), nullable=True),
        sa.Column('insurance_policy_number', sa.String(length=100), nullable=True),
        sa.Column('insurance_group_number', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_number')
    )
    op.create_index('ix_patients_id', 'patients', ['id'], unique=False)
    op.create_index('ix_patients_patient_number', 'patients', ['patient_number'], unique=True)
    op.create_index('ix_patients_last_name', 'patients', ['last_name'], unique=False)
    op.create_index('ix_patients_date_of_birth', 'patients', ['date_of_birth'], unique=False)
    
    # Create emergency_contacts table
    op.create_table(
        'emergency_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('relationship', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], )
    )
    op.create_index('ix_emergency_contacts_id', 'emergency_contacts', ['id'], unique=False)
    op.create_index('ix_emergency_contacts_patient_id', 'emergency_contacts', ['patient_id'], unique=False)
    
    # Create insurance table
    op.create_table(
        'insurance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_name', sa.String(length=200), nullable=False),
        sa.Column('policy_number', sa.String(length=100), nullable=False),
        sa.Column('group_number', sa.String(length=100), nullable=True),
        sa.Column('subscriber_name', sa.String(length=200), nullable=True),
        sa.Column('subscriber_relationship', sa.String(length=100), nullable=True),
        sa.Column('coverage_type', sa.String(length=100), nullable=True),
        sa.Column('copay_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('deductible_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], )
    )
    op.create_index('ix_insurance_id', 'insurance', ['id'], unique=False)
    op.create_index('ix_insurance_patient_id', 'insurance', ['patient_id'], unique=False)
    op.create_index('ix_insurance_policy_number', 'insurance', ['policy_number'], unique=False)
    
    # Create patient_visits table
    op.create_table(
        'patient_visits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('visit_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('visit_type', sa.String(length=100), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('physician', sa.String(length=200), nullable=True),
        sa.Column('chief_complaint', sa.Text(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('treatment', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='scheduled'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], )
    )
    op.create_index('ix_patient_visits_id', 'patient_visits', ['id'], unique=False)
    op.create_index('ix_patient_visits_patient_id', 'patient_visits', ['patient_id'], unique=False)
    op.create_index('ix_patient_visits_visit_date', 'patient_visits', ['visit_date'], unique=False)
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('action', sa.Enum('CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'ACCESS_DENIED', 'SYSTEM', name='auditaction'), nullable=False),
        sa.Column('resource_type', sa.Enum('USER', 'PATIENT', 'EMERGENCY_CONTACT', 'INSURANCE', 'PATIENT_VISIT', 'DEPARTMENT', 'SYSTEM', 'AUDIT_LOG', name='auditresource'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    
    # Create system_events table
    op.create_table(
        'system_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_service', sa.String(length=100), nullable=True),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_system_events_id', 'system_events', ['id'], unique=False)
    op.create_index('ix_system_events_event_type', 'system_events', ['event_type'], unique=False)
    op.create_index('ix_system_events_severity', 'system_events', ['severity'], unique=False)
    op.create_index('ix_system_events_created_at', 'system_events', ['created_at'], unique=False)
    
    # Create compliance_reports table
    op.create_table(
        'compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('report_type', sa.String(length=100), nullable=False),
        sa.Column('report_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('report_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('report_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_compliance_reports_id', 'compliance_reports', ['id'], unique=False)
    op.create_index('ix_compliance_reports_report_type', 'compliance_reports', ['report_type'], unique=False)
    op.create_index('ix_compliance_reports_period', 'compliance_reports', ['report_period_start', 'report_period_end'], unique=False)
    
    # Create data_access_logs table
    op.create_table(
        'data_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('resource_type', sa.Enum('USER', 'PATIENT', 'EMERGENCY_CONTACT', 'INSURANCE', 'PATIENT_VISIT', 'DEPARTMENT', 'SYSTEM', 'AUDIT_LOG', name='auditresource'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('field_value_hash', sa.String(length=255), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('access_purpose', sa.String(length=200), nullable=True),
        sa.Column('legal_basis', sa.String(length=200), nullable=True),
        sa.Column('data_sensitivity', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_data_access_logs_id', 'data_access_logs', ['id'], unique=False)
    op.create_index('ix_data_access_logs_resource_id', 'data_access_logs', ['resource_id'], unique=False)
    op.create_index('ix_data_access_logs_user_id', 'data_access_logs', ['user_id'], unique=False)
    op.create_index('ix_data_access_logs_created_at', 'data_access_logs', ['created_at'], unique=False)
    
    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), nullable=False),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_username', sa.String(length=100), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_security_events_id', 'security_events', ['id'], unique=False)
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'], unique=False)
    op.create_index('ix_security_events_severity', 'security_events', ['severity'], unique=False)
    op.create_index('ix_security_events_source_ip', 'security_events', ['source_ip'], unique=False)
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order of creation
    op.drop_table('security_events')
    op.drop_table('data_access_logs')
    op.drop_table('compliance_reports')
    op.drop_table('system_events')
    op.drop_table('audit_logs')
    op.drop_table('patient_visits')
    op.drop_table('insurance')
    op.drop_table('emergency_contacts')
    op.drop_table('patients')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS auditseverity')
    op.execute('DROP TYPE IF EXISTS auditresource')
    op.execute('DROP TYPE IF EXISTS auditaction')
    op.execute('DROP TYPE IF EXISTS maritalstatus')
    op.execute('DROP TYPE IF EXISTS bloodtype')
    op.execute('DROP TYPE IF EXISTS gender')
