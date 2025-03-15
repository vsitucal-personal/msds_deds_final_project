from pydantic import BaseModel


class Customer(BaseModel):
    first_name: str
    last_name: str
    email: str
    joined_at: str


class Vendor(BaseModel):
    vendor_name: str
    region: str
    joined_at: str


class InventoryItem(BaseModel):
    vendor_id: int
    item_name: str
    category: str
    price: float
    updated_at: str
