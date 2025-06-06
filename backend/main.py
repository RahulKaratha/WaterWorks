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
import random
import re
from sqlalchemy import asc
import models
from models import Household,Waterboard,WaterCutoff,Fine,ServiceRequest,Location,Contacts
from database import engine, SessionLocal
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import aliased
from sqlalchemy import or_



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

@app.get("/household/meter-reading", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("updatebill.html", {"request": request})


@app.get("/requests", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("requests.html", {"request": request})


@app.get("/user", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("user.html", {"request": request})

@app.get("/swap", response_class=HTMLResponse)
def serve_page(request: Request):
    return templates.TemplateResponse("swap.html", {"request": request})


@app.get("/household/update", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("update.html", {"request": request})


@app.get("/household/delete", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("delete.html", {"request": request})


@app.get("/household/add", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

@app.get("/cutoffs", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("watercutoff.html", {"request": request})





@app.get("/households/", response_model=List[HouseholdOut])
def get_all_households(db: Session = Depends(get_db)):
    households = db.query(Household).options(selectinload(Household.contacts)).all()
    return households


@app.get("/households/{location_name}", response_model=List[HouseholdOut])
def get_households_by_location(location_name: str, db: Session = Depends(get_db)):
    households = (
        db.query(Household)
        .filter(Household.location_name == location_name)
        .options(selectinload(Household.contacts))
        .all()
    )
    if not households:
        raise HTTPException(status_code=404, detail="No households found for the specified location")
    return households


@app.get("/household/", response_model=HouseholdOut)
def get_household_by_meter_no(meter_no: int, db: Session = Depends(get_db)):
    household = (
        db.query(Household)
        .filter(Household.meter_no == meter_no)
        .options(selectinload(Household.contacts))
        .first()
    )
    if not household:
        raise HTTPException(status_code=404, detail="Household not found with the given meter number")
    return household

@app.get("/households/delete-info/{meter_no}")
def get_household(meter_no: int, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.meter_no == meter_no).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")
    
    return {
        "meter_no": household.meter_no,
        "owner_name": household.owner_name,
        "address": household.address,
        "members_count": household.members_count,
        "location_name": household.location_name,
        "water_allowed": household.water_allowed,
        "supply_status": household.supply_status,
        "contacts": [c.contact_number for c in household.contacts],
    }

def is_valid_indian_mobile(number: str) -> bool:
    if not re.fullmatch(r"[6-9]\d{9}", number):
        return False
    
    if number == number[0] * 10:
        return False
    if number in {"9876543210", "9123456789"}:
        return False
    return True

def is_valid_name(name: str) -> bool:
    # Only letters, spaces, hyphens, and periods allowed
    if not re.fullmatch(r"[A-Za-z\s\.\-]{2,100}", name):
        return False
    return True


@app.post("/households/", status_code=201)
def create_household(household: HouseholdCreate, db: Session = Depends(get_db)):
    # Ensure location exists
    location = db.query(Location).filter_by(location_name=household.location_name).first()
    if not location:
        raise HTTPException(status_code=400, detail="Location does not exist")

    # Validate owner name
    if not is_valid_name(household.owner_name):
        raise HTTPException(status_code=400, detail=f"Invalid owner name: {household.owner_name}")

    # Generate unique meter number
    def generate_unique_meter_no():
        attempts = 0
        while attempts < 10_000:
            meter_no = str(random.randint(10**6, 10**7 - 1))  # 7-digit number
            exists = db.query(Household).filter_by(meter_no=meter_no).first()
            if not exists:
                return meter_no
            attempts += 1
        raise HTTPException(status_code=500, detail="Unable to generate unique meter number")

    meter_no = generate_unique_meter_no()

    try:
        new_household = Household(
            meter_no=meter_no,
            owner_name=household.owner_name,
            address=household.address,
            members_count=household.members_count,
            location_name=household.location_name,
            water_used=0
        )

        for contact in household.contacts:
            if not is_valid_indian_mobile(contact.contact_number):
                raise HTTPException(status_code=400, detail=f"Invalid contact number: {contact.contact_number}")

            new_contact = Contacts(
                meter_no=meter_no,
                contact_number=contact.contact_number
            )
            new_household.contacts.append(new_contact)

        db.add(new_household)
        db.commit()
        db.refresh(new_household)

        return {
            "message": "Household created successfully",
            "meter_no": new_household.meter_no,
            "water_allowed": new_household.water_allowed
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred: " + str(e))
    

@app.get("/check_meter/{meter_no}")
def check_meter_number(meter_no: int, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.meter_no == meter_no).first()

    if not household:
        raise HTTPException(status_code=404, detail="Meter number not found.")
    
    return {"message": "Meter number exists.", "meter_no": meter_no}

# Update household details
@app.patch("/households/", response_model=HouseholdUpdate)
def update_household(meter_no: int, update_data: HouseholdUpdate, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.meter_no == meter_no).first()

    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    update_dict = update_data.dict(exclude_unset=True)

    # Handle contacts separately
    if "contacts" in update_dict and update_data.contacts is not None:
        db.query(Contacts).filter(Contacts.meter_no == meter_no).delete()
        db.flush()

        for contact in update_data.contacts:
            contact_number = contact.contact_number

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


@app.patch("/household/update/water-used")
def update_water_used(update: WaterUsedUpdate, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.meter_no == update.meter_no).first()
    
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")
    
    household.water_used = update.water_used
    db.commit()
    db.refresh(household) 
    
    return {"meter_no": update.meter_no, "water_used": household.water_used}



@app.get("/servicerequest", response_model=List[ServiceRequestOut])
def get_all_service_requests(db: Session = Depends(get_db)):
    requests = (
        db.query(ServiceRequest)
        .order_by(asc(ServiceRequest.request_date))  # Oldest requests first
        .all()
    )

    if not requests:
        raise HTTPException(status_code=404, detail="No service requests found")

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
        # If the existing request is resolved or completed, update the status to "Pending" and the request date
        if existing_request.request_status != "Pending":
            existing_request.request_status = "Pending"  # Update to Pending if it's not already in pending status
            existing_request.request_date = func.now()  # Update the request date
            db.commit()
            db.refresh(existing_request)  # Refresh to get the updated record
            return existing_request
        else:
            # If the request is already pending, just update the request date
            existing_request.request_date = func.now()
            db.commit()
            db.refresh(existing_request)  # Refresh to get the updated record
            return existing_request
    else:
        # If no existing request, create a new one
        new_request = ServiceRequest(
            meter_no=request.meter_no,
            request_type=request.request_type,
            request_date=func.now(),  # Setting the request date as the current time
            request_status="Pending"  # Set the status to "Pending"
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)  # Refresh to get the newly created record
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

@app.get("/requests/view/{meterno}",response_model=List[ServiceRequestOut])
async def view_individual_requests(meterno:int,db: Session = Depends(get_db)):
    requests=db.query(ServiceRequest).filter_by(meter_no=meterno).all()
    return requests

@app.get("/fines/{meterno}",response_model=FineOut)
async def view_fine(meterno:int, db: Session = Depends(get_db)):
    fineInfo=db.query(models.Fine).filter_by(meter_no=meterno).first()
    return fineInfo

@app.get("/fines/",response_model=FineOut)
async def view_all_fine( db: Session = Depends(get_db)):
    fineInfo=db.query(models.Fine).all()
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
    # Subquery to check for pending fines
    subquery = db.query(Fine.meter_no).filter(Fine.payment_status == 'Pending')

    # Query WaterCutoff table and exclude records where there's a pending fine
    return db.query(WaterCutoff).filter(~WaterCutoff.meter_no.in_(subquery)).all()


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

@app.patch("/watercutoff/{cutoff_id}/restore", status_code=200)
def update_restoration_date(cutoff_id: int, payload: RestorationUpdate, db: Session = Depends(get_db)):
    record = db.query(WaterCutoff).filter(WaterCutoff.id == cutoff_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Cutoff record not found")

    # Date validation
    if payload.restoration_date < date.today():
        raise HTTPException(status_code=400, detail="Restoration date cannot be in the past.")
    
    if payload.restoration_date > date.today().replace(year=date.today().year + 1):
        raise HTTPException(status_code=400, detail="Restoration date cannot be more than 1 year in the future.")

    record.restoration_date = payload.restoration_date
    db.commit()
    db.refresh(record)
    return {
        "message": "Restoration date updated",
        "id": record.id,
        "restoration_date": record.restoration_date
    }


@app.post("/location/swap-supply/")
def swap_supply(request: SupplySwapRequest, db: Session = Depends(get_db)):
    def get_location(name: str):
        return db.query(Location).filter(Location.location_name == name).first()

    def get_location_by_supply_id(supply_id: int):
        return db.query(Location).filter(Location.supply_id == supply_id).first()

    loc1 = loc2 = None

    if request.location_name_1:
        loc1 = get_location(request.location_name_1)
        if not loc1:
            raise HTTPException(status_code=404, detail=f"Location '{request.location_name_1}' not found")
        supply_id_1 = loc1.supply_id
    elif request.supply_id_1 is not None:
        loc1 = get_location_by_supply_id(request.supply_id_1)
        supply_id_1 = request.supply_id_1
    else:
        raise HTTPException(status_code=400, detail="Provide either location_name_1 or supply_id_1")

    if request.location_name_2:
        loc2 = get_location(request.location_name_2)
        if not loc2:
            raise HTTPException(status_code=404, detail=f"Location '{request.location_name_2}' not found")
        supply_id_2 = loc2.supply_id
    elif request.supply_id_2 is not None:
        loc2 = get_location_by_supply_id(request.supply_id_2)
        supply_id_2 = request.supply_id_2
    else:
        raise HTTPException(status_code=400, detail="Provide either location_name_2 or supply_id_2")

    if supply_id_1 is None or supply_id_2 is None:
        raise HTTPException(status_code=400, detail="Supply IDs could not be resolved.")

    if loc1:
        loc1.supply_id = supply_id_2
    if loc2:
        loc2.supply_id = supply_id_1

    db.commit()

    result = []
    if loc1:
        db.refresh(loc1)
        result.append({"location": loc1.location_name, "new_supply_id": loc1.supply_id})
    else:
        result.append({"location": None, "now_has_supply_id": supply_id_2})
    if loc2:
        db.refresh(loc2)
        result.append({"location": loc2.location_name, "new_supply_id": loc2.supply_id})
    else:
        result.append({"location": None, "now_has_supply_id": supply_id_1})

    return {"message": "Supply lines swapped successfully", "result": result}

@app.get("/supply/unassigned", response_model=List[WaterboardSimple])
def get_unassigned_supply_lines(db: Session = Depends(get_db)):
    unassigned = (
        db.query(models.Waterboard)
        .outerjoin(models.Location, models.Location.supply_id == models.Waterboard.supply_id)
        .filter(models.Location.supply_id == None)
        .all()
    )
    return unassigned

@app.get("/recommend-swap")
async def recommend_swap(db: Session = Depends(get_db)):
    try:
        # Get all waterboard lines (with or without locations)
        water_lines = db.query(models.Waterboard).all()

        surplus_lines = []
        scarcity_lines = []

        for line in water_lines:
            # Calculate the difference between available and allowed water
            diff = line.water_available - line.water_allowed

            # Check if the line has a location (location_name is not NULL)
            has_location = line.location is not None

            if diff > 0:  # surplus
                surplus_lines.append((line, diff, has_location))
            elif diff < 0:  # scarcity
                scarcity_lines.append((line, diff, has_location))

        # Sort by the largest differences
        surplus_lines.sort(key=lambda x: x[1], reverse=True)  # Sort descending by difference
        scarcity_lines.sort(key=lambda x: abs(x[1]), reverse=True)  # Sort descending by absolute difference

        # Generate swap recommendations
        recommendations = []
        for surplus, scarcity in zip(surplus_lines, scarcity_lines):
            # If at least one line has a location, recommend swap
            if surplus[2] or scarcity[2]:  # at least one line has a location
                recommendations.append({
                    "surplus_supply_id": surplus[0].supply_id,
                    "surplus_diff": surplus[1],
                    "scarcity_supply_id": scarcity[0].supply_id,
                    "scarcity_diff": scarcity[1]
                })

        return {"message": "Swap recommendations generated", "recommendations": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
