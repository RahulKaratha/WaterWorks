from fastapi import FastAPI, HTTPException, Depends, Request, Form,status,Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel,Field
from typing import List, Annotated, Optional
from fastapi.middleware.cors import CORSMiddleware
from datetime import date,datetime
from enum import Enum
from sqlalchemy.sql import func
from pydanticModels import *


import models
from models import Household,Waterboard,WaterCutoff,Fine,ServiceRequest,Location,Contacts
from database import engine, SessionLocal



''' QUERY DEBUGGING

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("SQL Query: %s", str(query))

'''

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve HTML templates
templates = Jinja2Templates(directory="templates")

# Create DB tables
#models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@app.get("/", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/update", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("updatebill.html", {"request": request})


@app.get("/households/", response_model=List[HouseholdOut])
def get_all_households(db: Session = Depends(get_db)):
    households = db.query(Household).all()  # Retrieve all household records
    return households

@app.get("/households/{location_name}", response_model=List[HouseholdOut])
def get_households_by_location(location_name: str, db: Session = Depends(get_db)):
    households = db.query(models.Household).filter(models.Household.location_name == location_name).all()
    
    if not households:
        raise HTTPException(status_code=404, detail="No households found for the specified location")
    
    return households



@app.get("/household/", response_model=HouseholdOut)
def get_household_by_meter_no(meter_no: int, db: Session = Depends(get_db)):
    household = db.query(models.Household).filter(models.Household.meter_no == meter_no).first()

    if not household:
        raise HTTPException(status_code=404, detail="Household not found with the given meter number")

    return household


@app.post("/households/", status_code=201)
def create_household(household: HouseholdCreate, db: Session = Depends(get_db)):
    # Check for existing household with same meter_no
    existing = db.query(Household).filter_by(meter_no=household.meter_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Household with this meter number already exists")
    
    # Ensure that the location exists
    location = db.query(Location).filter_by(location_name=household.location_name).first()
    if not location:
        raise HTTPException(status_code=400, detail="Location does not exist")
    
    try:
        # Create the household
        new_household = Household(
            meter_no=household.meter_no,
            owner_name=household.owner_name,
            address=household.address,
            members_count=household.members_count,
            water_allowed=household.water_allowed,
            supply_status=household.supply_status,
            location_name=household.location_name,
            
        )

        # Add contacts
        for contact in household.contacts:
            new_contact = Contacts(
                meter_no=household.meter_no,
                contact_number=contact.contact_number
            )
            new_household.contacts.append(new_contact)

        # Add the new household to the session
        db.add(new_household)
        db.commit()  # Commit the transaction
        db.refresh(new_household)  # Refresh the object to get the updated state from the DB

        return {"message": "Household created successfully"}

    except SQLAlchemyError as e:
        db.rollback()  # Rollback in case of error
        raise HTTPException(status_code=500, detail="Database error occurred during insert: " + str(e))


@app.patch("/households/{meter_no}", response_model=HouseholdUpdate)
def update_household(meter_no: int, update_data: HouseholdUpdate, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.meter_no == meter_no).first()

    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle contacts separately
    if "contacts" in update_dict and update_data.contacts is not None:
        db.query(Contacts).filter(Contacts.meter_no == meter_no).delete()
        db.flush()

        for contact in update_data.contacts:
            contact_number = contact.get("contact_number") if isinstance(contact, dict) else contact.contact_number

            new_contact = Contacts(
                meter_no=meter_no,
                contact_number=contact_number
            )
            db.add(new_contact)

    # Update only non-None values
    for field, value in update_dict.items():
        if field == "contacts" or value is None:
            continue
        setattr(household, field, value)

    db.commit()
    db.refresh(household)

    return household

@app.delete("/households/{meter_no}", status_code=204)
def delete_household(meter_no: int, db: Session = Depends(get_db)):
    # Fetch the household object from the database
    household = db.query(Household).filter(Household.meter_no == meter_no).first()

    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    # Delete the household (cascade delete will handle related entries like contacts)
    db.delete(household)
    db.commit()

    return {"detail": "Household deleted successfully"}


@app.get("/servicerequest/{meter_no}")
def get_requests_by_meter_no(meter_no: int, db: Session = Depends(get_db)):
    requests = db.query(ServiceRequest).filter(ServiceRequest.meter_no == meter_no).all()
    
    if not requests:
        raise HTTPException(status_code=404, detail="No service requests found for this meter number")
    
    return requests




@app.post("/requests/raise", response_model=ServiceRequestCreate)
async def raise_service_request(request: ServiceRequestCreate, db: Session = Depends(get_db)):
    # Logic for raising or updating a service request (no auth yet)
    household = db.query(Household).filter_by(meter_no=request.meter_no).first()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")
    
    # Check if request already exists for this meter_no and request_type
    existing_request = db.query(ServiceRequest).filter_by(meter_no=request.meter_no, request_type=request.request_type).first()
    if existing_request:
        # Update request_date if exists
        existing_request.request_date = func.now()
        db.commit()
        return existing_request
    else:
        # Create a new request
        new_request = ServiceRequest(
            meter_no=request.meter_no,
            request_type=request.request_type,
            
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request
    

@app.patch("/servicerequest/{meter_no}/{request_type}")
def update_status(
    meter_no: int,
    request_type: str,
    status: str
    , db: Session = Depends(get_db)
):
    if status not in ["Pending", "Resolved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    req = db.query(ServiceRequest).filter_by(
        meter_no=meter_no,
        request_type=request_type
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Service request not found")

    req.request_status = status
    db.commit()
    return {"message": "Status updated", "status": req.request_status}

    
@app.get("/location/status",response_model=List[LocationResponse])
async def current_location_status(db: Session = Depends(get_db)):
    regions=db.query(models.Location).join(models.Waterboard,models.Waterboard.supply_id==models.Location.supply_id).all()
    return regions

@app.get("/requests/view",response_model=List[ServiceRequestOut])
async def view_requests(db: Session = Depends(get_db)):
    requests=db.query(ServiceRequest).all()
    return requests

@app.get("/fines/{meterno}",response_model=FineOut)
async def view_fine(meterno:int, db: Session = Depends(get_db)):
    fineInfo=db.query(models.Fine).filter_by(meter_no=meterno).first()
    return fineInfo

@app.patch("/fines/{meter_no}/mark-paid", status_code=200)
def mark_fine_as_paid(meter_no: int, db: Session = Depends(get_db)):
    fine = db.query(Fine).filter(Fine.meter_no == meter_no, Fine.payment_status == 'Pending').first()
    
    if not fine:
        raise HTTPException(status_code=404, detail="Pending fine not found for this meter number")
    
    if fine.payment_status == 'Paid':
        return {"message": "Fine already Paid"}
    
    fine.payment_status = 'Paid'
    db.commit()
    db.refresh(fine)

    
    return {
        "message": "Fine payment status updated to Paid",
        "fine_id": fine.id,
        "meter_no": fine.meter_no,
        "status": fine.payment_status
    }

@app.get("/watercutoff", response_model=List[WaterCutoffOut])
def get_all_water_cutoffs(db: Session = Depends(get_db)):
    return db.query(WaterCutoff).all()

@app.get("/watercutoff/{meter_no}", response_model=List[WaterCutoffOut])
def get_cutoff_by_meter_no(meter_no: int, db: Session = Depends(get_db)):
    records = db.query(WaterCutoff).filter(WaterCutoff.meter_no == meter_no).all()
    if not records:
        raise HTTPException(status_code=404, detail="No water cutoff record found for this meter number")
    return records

@app.patch("/watercutoff/{cutoff_id}/restore", status_code=200)
def update_restoration_date(cutoff_id: int, restoration_date: date, db: Session = Depends(get_db)):
    record = db.query(WaterCutoff).filter(WaterCutoff.id == cutoff_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Cutoff record not found")

    record.restoration_date = restoration_date
    db.commit()
    db.refresh(record)
    return {"message": "Restoration date updated", "id": record.id, "restoration_date": record.restoration_date}


