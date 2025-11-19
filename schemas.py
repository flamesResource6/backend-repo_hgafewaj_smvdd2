"""
Database Schemas

Doctor App domain models.
Each Pydantic model corresponds to a MongoDB collection named after the class in lowercase.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Core domain schemas

class Doctor(BaseModel):
    full_name: str = Field(..., description="Doctor's full name")
    email: str = Field(..., description="Work email")
    phone: Optional[str] = Field(None, description="Contact number")
    specialty: Optional[str] = Field(None, description="Primary specialty")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    facility_ids: List[str] = Field(default_factory=list, description="Facilities the doctor works at")
    bio: Optional[str] = Field(None, description="Short bio")
    tenant_id: Optional[str] = Field(None, description="Single-tenant identifier")

class Facility(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    tenant_id: Optional[str] = None

class Patient(BaseModel):
    full_name: str
    dob: Optional[str] = Field(None, description="Date of Birth YYYY-MM-DD")
    gender: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tenant_id: Optional[str] = None

class Appointment(BaseModel):
    doctor_id: str
    patient_id: str
    facility_id: Optional[str] = None
    start_time: str = Field(..., description="ISO datetime start")
    end_time: Optional[str] = Field(None, description="ISO datetime end")
    status: str = Field("scheduled", description="scheduled|completed|cancelled|no_show")
    reason: Optional[str] = None
    notes: Optional[str] = None
    tenant_id: Optional[str] = None

class EMR(BaseModel):
    doctor_id: str
    patient_id: str
    appointment_id: Optional[str] = None
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    review_of_systems: Optional[str] = None
    physical_exam: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    summary: Optional[str] = None
    tenant_id: Optional[str] = None

class Prescription(BaseModel):
    doctor_id: str
    patient_id: str
    medications: List[dict] = Field(default_factory=list, description="List of {name, dose, route, frequency, duration, notes}")
    notes: Optional[str] = None
    appointment_id: Optional[str] = None
    tenant_id: Optional[str] = None

# For metrics and dashboard visuals
class Metric(BaseModel):
    label: str
    value: float
    trend: Optional[float] = None
    updated_at: Optional[datetime] = None
