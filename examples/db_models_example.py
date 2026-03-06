# Example Python Module: Database Models
# This example shows the ORM models and schemas for invoice processing

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Pydantic Schemas (Request/Response)
class LineItemSchema(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class InvoiceExtractionSchema(BaseModel):
    vendor_name: str
    invoice_number: str
    invoice_date: str
    due_date: str
    subtotal: float
    tax: float
    total: float
    currency: str = 'USD'
    line_items: List[LineItemSchema] = Field(default_factory=list)
    confidence_scores: dict = Field(default_factory=dict)

class ExportRequestSchema(BaseModel):
    invoice_ids: List[str]
    export_format: str = 'csv'  # csv or webhook

# SQLAlchemy ORM Models
class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(String, primary_key=True)
    vendor_name = Column(String)
    invoice_number = Column(String, unique=True)
    invoice_date = Column(String)
    due_date = Column(String)
    subtotal = Column(Float)
    tax = Column(Float)
    total = Column(Float)
    currency = Column(String, default='USD')
    status = Column(String, default='pending')  # pending, extracted, reviewed, exported
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    exported_at = Column(DateTime, nullable=True)

class LineItem(Base):
    __tablename__ = 'line_items'
    
    id = Column(String, primary_key=True)
    invoice_id = Column(String)
    description = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    amount = Column(Float)
