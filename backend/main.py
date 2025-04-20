from fastapi import FastAPI, HTTPException, Depends, Request, Form,status
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


import models
from models import Household,Waterboard,WaterCutoff,Fine,ServiceRequest,Location,Contacts
from database import engine, SessionLocal



''' QUERY DEBUGGING

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 # Log the SQL query
logger.info("SQL Query: %s", str(query))

'''

app = FastAPI()

class ContactBase(BaseModel):
    contact_number: str

class ContactCreate(ContactBase):
    pass

class ContactOut(ContactBase):
    contact_number: str
    class Config:
         from_attributes = True

class HouseholdBase(BaseModel):
    meter_no: int
    owner_name: str
    address: str
    contacts: List[ContactOut] = []
    members_count: Annotated[int, Field(strict=True, gt=0)]
    water_allowed: Annotated[int, Field(strict=True, gt=0)]
    water_used: Annotated[int, Field(strict=True, gt=0)]
    supply_status: str
    location_name: str
    last_payment: Optional[date]

class HouseholdCreate(HouseholdBase):
    pass

class HouseholdUpdate(HouseholdBase):
    meter_no: int
    owner_name: str = None
    address: str = None
    members_count: int = None
    water_allowed: int = None
    water_used: int = None
    supply_status: str = None
    location_name: str = None
    last_payment: str = None

    class Config:
        from_attributes = True


class HouseholdOut(HouseholdBase):
    

    class Config:
         from_attributes = True


class LocationStatusEnum(str, Enum):
    Scarcity = "Scarcity"
    Shortage = "Shortage"
    Sufficient = "Sufficient"
    Surplus = "Surplus"

# Base model for Location
class LocationBase(BaseModel):
    location_name: str
    location_status: LocationStatusEnum
    total_household: int
    supply_id: int

# Model for updating a Location
class LocationUpdate(LocationBase):
    pass

# Model for returning Location details
class LocationOut(LocationBase):
    class Config:
        from_attributes = True

class WaterboardBase(BaseModel):
    water_available:  Annotated[int, Field(strict=True, gt=0)]
    water_allowed:  Annotated[int, Field(strict=True, gt=0)]
    water_used: Annotated[int, Field(strict=True, gt=0)]


class WaterboardOut(WaterboardBase):
    supply_id: int
    balance: Optional[int]
    class Config:
        from_attributes = True

class ServiceRequestBase(BaseModel):
    request_type: str
    request_status: str
    meter_no: Optional[int]

class ServiceRequestCreate(ServiceRequestBase):
    pass

class ServiceRequestOut(ServiceRequestBase):
    id: int
    request_date: datetime
    class Config:
        from_attributes = True

class WaterCutoffBase(BaseModel):
    cutoff_date: date
    reason: str
    restoration_date: Optional[date]
    meter_no: Optional[int]

class WaterCutoffCreate(WaterCutoffBase):
    pass

class WaterCutoffOut(WaterCutoffBase):
    id: int
    class Config:
        from_attributes = True

class FineBase(BaseModel):
    overdue:Annotated[int, Field(strict=True, gt=0)]
    payment_status: str
    meter_no: int

class FineCreate(FineBase):
    pass

class FineOut(FineBase):
    id: int
    class Config:
        from_attributes = True



"""
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
"""
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

from fastapi import Query

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
    
@app.patch("/update/household", response_model=HouseholdOut)
def update_household_records(household: HouseholdUpdate, contacts: List[ContactCreate], db: Session = Depends(get_db)):
    # Check if the household with the given meter_no exists
    existing_household = db.query(Household).filter_by(meter_no=household.meter_no).first()
    if not existing_household:
        raise HTTPException(status_code=404, detail="Household not found")

    # Update household fields if provided
    if household.owner_name:
        existing_household.owner_name = household.owner_name
    if household.address:
        existing_household.address = household.address
    if household.members_count:
        existing_household.members_count = household.members_count
    if household.water_allowed:
        existing_household.water_allowed = household.water_allowed
    if household.water_used:
        existing_household.water_used = household.water_used
    if household.supply_status:
        existing_household.supply_status = household.supply_status
    if household.location_name:
        existing_household.location_name = household.location_name
    if household.last_payment:
        existing_household.last_payment = household.last_payment

    # Now handle the contacts update
    # Clear existing contacts and add new ones
    existing_household.contacts.clear()

    for contact in contacts:
        # The meter_no will be taken from the outer household attributes
        contact_number = contact.contact_number
        
        # Ensure that the contact number is unique for this household
        existing_contact = db.query(Contacts).filter_by(meter_no=household.meter_no, contact_number=contact_number).first()
        if existing_contact:
            raise HTTPException(status_code=400, detail=f"Contact number {contact_number} already exists for this household")
        
        # Create new contact with the same meter_no as the household
        new_contact = Contacts(
            meter_no=household.meter_no,  # Use the meter_no from the household
            contact_number=contact_number
        )
        existing_household.contacts.append(new_contact)

    # Commit the changes to the database
    db.commit()
    db.refresh(existing_household)

    return existing_household  # Return the updated household details


