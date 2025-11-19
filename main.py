import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Doctor, Facility, Patient, Appointment, EMR, Prescription, Metric

app = FastAPI(title="Doctor App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")


def serialize(doc: Dict[str, Any]):
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetime to isoformat
    for k, v in list(d.items()):
        try:
            import datetime as _dt
            if isinstance(v, (_dt.datetime,)):
                d[k] = v.isoformat()
        except Exception:
            pass
    return d


@app.get("/")
def root():
    return {"message": "Doctor App Backend running"}


@app.get("/test")
def test_database():
    resp = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            resp["database"] = "✅ Available"
            resp["database_url"] = "✅ Set"
            resp["database_name"] = db.name
            resp["connection_status"] = "Connected"
            try:
                resp["collections"] = db.list_collection_names()
                resp["database"] = "✅ Connected & Working"
            except Exception as e:
                resp["database"] = f"⚠️ Connected but error: {str(e)[:60]}"
    except Exception as e:
        resp["database"] = f"❌ Error: {str(e)[:60]}"
    import os as _os
    resp["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    resp["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return resp


# Schema exposure for the Flames database viewer
@app.get("/schema")
def get_schema():
    return {
        "doctor": Doctor.model_json_schema(),
        "facility": Facility.model_json_schema(),
        "patient": Patient.model_json_schema(),
        "appointment": Appointment.model_json_schema(),
        "emr": EMR.model_json_schema(),
        "prescription": Prescription.model_json_schema(),
        "metric": Metric.model_json_schema(),
    }


# CRUD Endpoints (minimal for MVP)

# Create entities
@app.post("/doctors")
def create_doctor(payload: Doctor):
    new_id = create_document("doctor", payload)
    return {"id": new_id}


@app.post("/facilities")
def create_facility(payload: Facility):
    new_id = create_document("facility", payload)
    return {"id": new_id}


@app.post("/patients")
def create_patient(payload: Patient):
    new_id = create_document("patient", payload)
    return {"id": new_id}


@app.post("/appointments")
def create_appointment(payload: Appointment):
    new_id = create_document("appointment", payload)
    return {"id": new_id}


@app.post("/emrs")
def create_emr(payload: EMR):
    new_id = create_document("emr", payload)
    return {"id": new_id}


@app.post("/prescriptions")
def create_prescription(payload: Prescription):
    new_id = create_document("prescription", payload)
    return {"id": new_id}


# Lists and details
@app.get("/doctors")
def list_doctors(tenant_id: Optional[str] = None):
    q = {"tenant_id": tenant_id} if tenant_id else {}
    docs = get_documents("doctor", q)
    return [serialize(d) for d in docs]


@app.get("/patients")
def list_patients(tenant_id: Optional[str] = None, search: Optional[str] = None):
    q: Dict[str, Any] = {"tenant_id": tenant_id} if tenant_id else {}
    if search:
        q["full_name"] = {"$regex": search, "$options": "i"}
    docs = get_documents("patient", q, limit=None)
    return [serialize(d) for d in docs]


@app.get("/appointments")
def list_appointments(doctor_id: Optional[str] = None, tenant_id: Optional[str] = None, status: Optional[str] = None):
    q: Dict[str, Any] = {}
    if doctor_id:
        q["doctor_id"] = doctor_id
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    docs = get_documents("appointment", q)
    return [serialize(d) for d in docs]


@app.get("/emrs/{patient_id}")
def list_emrs_for_patient(patient_id: str):
    docs = get_documents("emr", {"patient_id": patient_id})
    return [serialize(d) for d in docs]


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    doc = db["patient"].find_one({"_id": oid(patient_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")
    return serialize(doc)


@app.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: str):
    doc = db["appointment"].find_one({"_id": oid(appointment_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return serialize(doc)


# Update simple profile for doctor
class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    facility_ids: Optional[List[str]] = None


@app.patch("/doctors/{doctor_id}")
def update_doctor(doctor_id: str, payload: DoctorUpdate):
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return {"updated": False}
    res = db["doctor"].update_one({"_id": oid(doctor_id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doc = db["doctor"].find_one({"_id": oid(doctor_id)})
    return serialize(doc)


# Simple metrics for dashboard
@app.get("/metrics")
def get_metrics(doctor_id: Optional[str] = None, tenant_id: Optional[str] = None):
    # Compute minimal metrics from collections
    q_appt: Dict[str, Any] = {}
    if doctor_id:
        q_appt["doctor_id"] = doctor_id
    if tenant_id:
        q_appt["tenant_id"] = tenant_id

    total_appts = db["appointment"].count_documents(q_appt)
    completed = db["appointment"].count_documents({**q_appt, "status": "completed"})
    scheduled = db["appointment"].count_documents({**q_appt, "status": "scheduled"})
    cancelled = db["appointment"].count_documents({**q_appt, "status": "cancelled"})

    return {
        "cards": [
            {"label": "Total Appointments", "value": total_appts},
            {"label": "Scheduled", "value": scheduled},
            {"label": "Completed", "value": completed},
            {"label": "Cancelled", "value": cancelled},
        ]
    }


# Conversational EMR generation (mock placeholder algorithm)
class ConversationInput(BaseModel):
    transcript: str
    style: Optional[str] = "concise"


@app.post("/emr/generate")
def generate_emr(conv: ConversationInput):
    # Lightweight heuristic stub; replace with real LLM later
    text = conv.transcript.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    # Naive extraction
    import re
    def find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    emr = {
        "chief_complaint": find(r"chief complaint[:\-]\s*(.*)") or find(r"cc[:\-]\s*(.*)"),
        "history_of_present_illness": find(r"hpi[:\-]\s*(.*)"),
        "review_of_systems": find(r"ros[:\-]\s*(.*)"),
        "physical_exam": find(r"exam[:\-]\s*(.*)"),
        "assessment": find(r"assessment[:\-]\s*(.*)"),
        "plan": find(r"plan[:\-]\s*(.*)"),
        "summary": text[:500]
    }
    # Clean None values
    emr = {k: v for k, v in emr.items() if v}
    return emr


# Prescription utility
class PrescriptionInput(BaseModel):
    medications: List[Dict[str, Any]]
    notes: Optional[str] = None


@app.post("/prescription/preview")
def prescription_preview(payload: PrescriptionInput):
    lines = []
    for m in payload.medications:
        name = m.get("name", "Medicine")
        dose = m.get("dose", "")
        route = m.get("route", "")
        freq = m.get("frequency", "")
        duration = m.get("duration", "")
        note = m.get("notes", "")
        line = ", ".join([x for x in [name, dose, route, freq, duration] if x])
        if note:
            line += f" — {note}"
        lines.append(line)
    return {"preview": "\n".join(lines), "count": len(lines)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
