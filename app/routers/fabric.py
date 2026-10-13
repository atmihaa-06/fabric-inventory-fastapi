from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Fabric
from app.schemas import FabricCreate, FabricResponse, FabricUpdate, StockUpdate
import pandas as pd
from fastapi import UploadFile, File

router = APIRouter(
    prefix="/api/fabrics",
    tags=["Fabrics"]
)

@router.get("/", response_model=List[FabricResponse])
def get_all_fabrics(
    db: Session = Depends(get_db)
):

    fabrics = db.query(Fabric).all()

    return fabrics

@router.get("/{fabric_id}", response_model=FabricResponse)
def get_fabric_by_id(
    fabric_id: int,
    db: Session = Depends(get_db)
):
    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    return fabric

@router.post("/", response_model=FabricResponse)
def create_fabric(
    fabric: FabricCreate,
    db: Session = Depends(get_db)
):

    existing_fabric = db.query(Fabric).filter(
        Fabric.fabric_name == fabric.fabric_name,
        Fabric.color == fabric.color
    ).first()

    if existing_fabric:
        raise HTTPException(
            status_code=400,
            detail="Fabric with this color already exists"
        )

    new_fabric = Fabric(
        fabric_name=fabric.fabric_name,
        fabric_type=fabric.fabric_type,
        color=fabric.color,
        gsm=fabric.gsm,
        price_per_meter=fabric.price_per_meter,
        available_stock=fabric.available_stock,
        supplier_name=fabric.supplier_name
    )

    db.add(new_fabric)
    db.commit()
    db.refresh(new_fabric)

    return new_fabric

@router.put("/{fabric_id}", response_model=FabricResponse)
def update_fabric(
    fabric_id: int,
    updated_fabric: FabricUpdate,
    db: Session = Depends(get_db)
):
    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    if fabric is None:
        raise HTTPException(
            status_code=404,
            detail="Fabric not found"
        )

    fabric.fabric_name = updated_fabric.fabric_name
    fabric.fabric_type = updated_fabric.fabric_type
    fabric.color = updated_fabric.color
    fabric.gsm = updated_fabric.gsm
    fabric.price_per_meter = updated_fabric.price_per_meter
    fabric.available_stock = updated_fabric.available_stock
    fabric.supplier_name = updated_fabric.supplier_name

    db.commit()
    db.refresh(fabric)

    return fabric

@router.delete("/{fabric_id}")
def delete_fabric(
    fabric_id: int,
    db: Session = Depends(get_db)
):
    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    if fabric is None:
        raise HTTPException(
            status_code=404,
            detail="Fabric not found"
        )

    db.delete(fabric)
    db.commit()

    return {"message": "Fabric deleted successfully"}
    
@router.patch("/{fabric_id}/stock", response_model=FabricResponse)
def update_stock(
    fabric_id: int,
    stock: StockUpdate,
    db: Session = Depends(get_db)
):
    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    if fabric is None:
        raise HTTPException(
            status_code=404,
            detail="Fabric not found"
        )

    fabric.available_stock = stock.available_stock

    db.commit()
    db.refresh(fabric)

    return fabric

@router.post("/upload-excel")
def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    df = pd.read_excel(file.file)

    imported_count = 0
    skipped_count = 0

    for _, row in df.iterrows():

        existing_fabric = db.query(Fabric).filter(
            Fabric.fabric_name == row["fabric_name"],
            Fabric.color == row["color"]
        ).first()

        if existing_fabric:
            skipped_count += 1
            continue

        fabric = Fabric(
            fabric_name=row["fabric_name"],
            fabric_type=row["fabric_type"],
            color=row["color"],
            gsm=row["gsm"],
            price_per_meter=row["price_per_meter"],
            available_stock=row["available_stock"],
            supplier_name=row["supplier_name"]
        )

        db.add(fabric)
        imported_count += 1

    db.commit()

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "message": "Excel import completed"
    }