from fastapi import FastAPI
from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Annotated
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine, SessionLocal

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
models.Base.metadata.create_all(bind=engine)




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]