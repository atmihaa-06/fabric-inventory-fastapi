
from pydantic import BaseModel, Field
from typing import Optional


class FabricBase(BaseModel):

    fabric_name: str = Field(..., min_length=1)

    fabric_type: str

    color: str

    gsm: float = Field(..., gt=0)

    price_per_meter: float = Field(..., gt=0)

    available_stock: int = Field(..., ge=0)

    supplier_name: str


class FabricCreate(FabricBase):
    pass


class FabricUpdate(FabricBase):
    pass


class FabricResponse(FabricBase):

    id: int

    class Config:
        from_attributes = True

class StockUpdate(BaseModel):
    available_stock: int = Field(..., ge=0)

class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    role: str