from sqlalchemy import Text,DateTime,Date,Computed,Enum,Boolean,Column,ForeignKey,String,Integer,CheckConstraint,PrimaryKeyConstraint
from database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class Household(Base):
    __tablename__='household'

    meter_no=Column(Integer,primary_key=True,index=True)
    owner_name=Column(String,nullable=False,index=True)
    address=Column(Text,index=True)
    members_count=Column(Integer,CheckConstraint('members_count>0'),nullable=False,index=True)
    water_allowed=Column(Integer,CheckConstraint('water_allowed>0'),index=True)
    water_used=Column(Integer,CheckConstraint('water_used>0'),index=True,default=0)
    supply_status=Column(Enum('Active','Inactive',name='status'),index=True,default="Active")
    location_name=Column(String,ForeignKey('location.location_name'),nullable=False,index=True)
    last_payment=Column(Date,index=True,default=func.now())

    contacts=relationship("Contacts",back_populates="household",cascade="all, delete-orphan")
    location=relationship("Location",back_populates="household")
    servicerequest=relationship("ServiceRequest",back_populates="household",cascade="all, delete-orphan")
    watercutoff=relationship("WaterCutoff",back_populates="household",cascade="all, delete-orphan")
    fine=relationship("Fine",back_populates="household")


   
class Contacts(Base):
    __tablename__='contacts'
    meter_no=Column(Integer,ForeignKey('household.meter_no'),index=True,nullable=False)
    contact_number=Column(String(10),index=True,unique=True)

    __table_args__ = (
        PrimaryKeyConstraint('meter_no', 'contact_number'),
    )

    household=relationship("Household",back_populates="contacts")

class Location(Base):
    __tablename__='location'

    location_name=Column(String,primary_key=True,index=True)
    location_status=Column(Enum('Scarcity','Shortage','Sufficient','Surplus',name='condition'),index=True)
    total_household=Column(Integer,CheckConstraint('total_household>0'),index=True)
    supply_id=Column(Integer,ForeignKey('waterboard.supply_id'),index=True,nullable=False)

    waterboard=relationship("Waterboard",back_populates="location")
    household=relationship("Household",back_populates="location")

class Waterboard(Base):
    __tablename__='waterboard'

    supply_id=Column(Integer,primary_key=True,index=True)
    water_available=Column(Integer,index=True)
    water_allowed=Column(Integer,index=True)
    water_used=Column(Integer,index=True)
    balance=Column(Integer,Computed('water_allowed-water_used'),index=True)

    location=relationship("Location",back_populates="waterboard")

class ServiceRequest(Base):
    __tablename__='servicerequest'

    
    request_type=Column(String,index=True)
    request_date=Column(DateTime(timezone=True), server_default=func.now(),index=True)
    request_status=Column(Enum('Pending','Resolved','Rejected',name='request'),index=True,default='Pending')
    meter_no=Column(Integer,ForeignKey("household.meter_no"),index=True,nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('meter_no', 'request_type'),
    )

    household=relationship("Household",back_populates="servicerequest")

class WaterCutoff(Base):
    __tablename__='watercutoff'

    id=Column(Integer,primary_key=True,autoincrement=True,index=True)
    cutoff_date=Column(Date,index=True,nullable=False)
    reason=Column(String,index=True,nullable=False)
    restoration_date=Column(Date,index=True)
    meter_no=Column(Integer,ForeignKey("household.meter_no",ondelete="SET NULL"),index=True,nullable=True)

    household=relationship("Household",back_populates="watercutoff")

class Fine(Base):
    __tablename__='fine'

    id=Column(Integer,primary_key=True,autoincrement=True,index=True)
    overdue=Column(Integer,CheckConstraint('overdue>0'),index=True,nullable=True)
    payment_status=Column(Enum('Paid','Pending',name='transaction'),index=True,default='Pending')
    meter_no=Column(Integer,ForeignKey("household.meter_no"),index=True)

    household=relationship("Household",back_populates="fine")


