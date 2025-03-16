from datetime import datetime

from pydantic import BaseModel, field_validator


class Customer(BaseModel):
    first_name: str
    last_name: str
    email: str


class CustomerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    joined_at: str

    @field_validator("joined_at", mode="before")
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)  # Ensures non-datetime values are also converted to strings


class Vendor(BaseModel):
    vendor_name: str
    region: str


class VendorResponse(BaseModel):
    id: int
    vendor_name: str
    region: str
    joined_at: str

    @field_validator("joined_at", mode="before")
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)  # Ensures non-datetime values are also converted to strings


class InventoryItem(BaseModel):
    item_name: str
    category: str
    price: float


class InventoryItemResponse(BaseModel):
    id: int
    item_name: str
    category: str
    price: float
    vendor_id: int
    updated_at: str

    @field_validator("updated_at", mode="before")
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)  # Ensures non-datetime values are also converted to strings
