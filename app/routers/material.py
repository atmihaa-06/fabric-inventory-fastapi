from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Material
from app.schemas import MaterialCreate

from app.models import Material
import pandas as pd
from fastapi import UploadFile, File
from fastapi.responses import RedirectResponse

router = APIRouter(
    prefix="/materials",
    tags=["Material Register"]
)

@router.post("/")
def create_material(
    material: MaterialCreate,
    db: Session = Depends(get_db)
):
    new_material = Material(**material.model_dump())

    db.add(new_material)
    db.commit()
    db.refresh(new_material)

    return new_material


@router.get("/")
def get_materials(
    db: Session = Depends(get_db)
):
    return db.query(Material).all()

@router.post("/upload-excel")
def upload_material_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    df = pd.read_excel(file.file)

    imported_count = 0
    skipped_count = 0

    for _, row in df.iterrows():

        existing_material = db.query(Material).filter(
            Material.product_name == row["product_name"],
            Material.size == row["size"]
        ).first()

        if existing_material:
            skipped_count += 1
            continue

        material = Material(
            product_name=row["product_name"],
            category=row["category"],
            fabric_used=row["fabric_used"],
            size=row["size"],
            price=row["price"],
            stock=row["stock"]
        )

        db.add(material)
        imported_count += 1

    db.commit()

    return RedirectResponse(
    url=f"/materials/upload-success?imported={imported_count}&skipped={skipped_count}",
    status_code=303
)