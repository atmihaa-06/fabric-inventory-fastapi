from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from sqlalchemy.orm import relationship


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

class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, unique=True, nullable=False)

    users = relationship(
        "User",
        back_populates="role"
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    role_id = Column(
        Integer,
        ForeignKey("roles.role_id"),
        nullable=False
    )

    role = relationship(
        "Role",
        back_populates="users"
    )