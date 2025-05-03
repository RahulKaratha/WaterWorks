from typing import List, Annotated, Optional
from pydantic import BaseModel,Field
from datetime import date,datetime
from enum import Enum

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

class HouseholdCreate(BaseModel):
    owner_name: str
    address: str
    members_count: int
    location_name: str
    contacts: List[ContactCreate]

class HouseholdUpdate(BaseModel):
    owner_name: Optional[str] = None
    address: Optional[str] = None
    members_count: Optional[int] = None
    water_allowed: Optional[int] = None
    water_used: Optional[int] = None
    supply_status: Optional[str] = None
    location_name: Optional[str] = None
    last_payment: Optional[date] = None
    contacts: Optional[List[ContactOut]] = None

    class Config:
        from_attributes = True


class HouseholdOut(BaseModel):
    meter_no: int
    owner_name: str
    address: str
    members_count: int
    water_allowed: int
    water_used: int  
    supply_status: str
    location_name: str
    last_payment: date

    class Config:
        from_attributes = True
class WaterUsedUpdate(BaseModel):
    meter_no:int
    water_used:int

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

class WaterboardResponse(BaseModel):
    supply_id: int
    water_available: Optional[int]
    water_allowed: Optional[int]
    water_used: Optional[int]
    balance: Optional[int]

    class Config:
        orm_mode = True  # Allows SQLAlchemy model instances to be serialized

# Pydantic model for Location response
class LocationResponse(BaseModel):
    location_name: str
    location_status: LocationStatusEnum
    total_household: int
    supply_id: int  # Foreign key to Waterboard table
    waterboard: Optional[WaterboardResponse]  # Nested response for Waterboard

    class Config:
        orm_mode = True 

class ServiceRequestBase(BaseModel):
    request_type: str
    request_status: str
    meter_no: Optional[int]

class ServiceRequestCreate(BaseModel):
    request_type: str
    meter_no:int
    

class ServiceRequestOut(BaseModel):
    meter_no:int
    request_type: str
    request_date: datetime
    request_status: str

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

class SupplySwapRequest(BaseModel):
    location_name_1: Optional[str] = None
    location_name_2: Optional[str] = None
    supply_id_1: Optional[int] = None
    supply_id_2: Optional[int] = None

class WaterboardSimple(BaseModel):
    supply_id: int
    water_available: int
    water_allowed: int
    water_used: int
    balance: int

    class Config:
        orm_mode = True
