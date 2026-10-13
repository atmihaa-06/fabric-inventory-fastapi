from sqlalchemy import Column, Integer, String, Float, ForeignKey,Date
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

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)

    product_name = Column(String, nullable=False)

    category = Column(String, nullable=False)

    fabric_used = Column(String, nullable=False)

    size = Column(String)

    price = Column(Float, nullable=False)

    stock = Column(Integer, nullable=False)

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)

    supplier_name = Column(String, nullable=False)

    contact_person = Column(String)

    phone = Column(String)

    email = Column(String)

    address = Column(String)

class PurchaseRecord(Base):
    __tablename__ = "purchase_records"

    id = Column(Integer, primary_key=True, index=True)

    supplier_name = Column(String, nullable=False)

    fabric_name = Column(String, nullable=False)

    quantity = Column(Integer, nullable=False)

    purchase_price = Column(Float, nullable=False)

    purchase_date = Column(String, nullable=False)

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String)
    fabric_name = Column(String)
    quantity = Column(Integer)
    selling_price = Column(Float)
    order_date = Column(Date)