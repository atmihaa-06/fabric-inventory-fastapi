from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Fabric(Base):
    __tablename__ = "fabrics"

    id = Column(Integer, primary_key=True, index=True)

    fabric_name = Column(String, nullable=False)

    fabric_type = Column(String, nullable=False)

    color = Column(String)

    gsm = Column(Float, nullable=False)

    price_per_meter = Column(Float, nullable=False)

    available_stock = Column(Integer, nullable=False)

    supplier_name = Column(String)