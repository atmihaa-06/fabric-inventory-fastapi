from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.models import Supplier
from app.models import PurchaseRecord
from app.models import SalesOrder
from fastapi import Form
from fastapi.responses import RedirectResponse
from app.models import SalesOrder
from datetime import datetime

from app.database import engine
from app.models import Base
from app.routers import fabric
import app.routers.user as user

from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models import User

from fastapi import UploadFile, File
import pandas as pd
from app.models import Fabric
from app.models import Material
from starlette.middleware.sessions import SessionMiddleware
import app.routers.material as material
from app.models import Fabric
from app.database import SessionLocal


Base.metadata.create_all(bind=engine)
from app.models import Role
from app.database import SessionLocal

db = SessionLocal()

if db.query(Role).count() == 0:

    db.add(Role(role_id=1, role_name="admin"))
    db.add(Role(role_id=2, role_name="sales"))
    db.add(Role(role_id=3, role_name="purchase"))
    db.add(Role(role_id=4, role_name="accounts"))

    db.commit()

db.close()

app = FastAPI(
    title="Fabric Inventory API"
)

app.add_middleware(
    SessionMiddleware,
    secret_key="fabric_inventory_secret"
)

# Jinja2 Templates
templates = Jinja2Templates(directory="app/templates")

# Static Files (CSS)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# Routers
app.include_router(fabric.router)
app.include_router(user.router)
app.include_router(material.router)

@app.get("/")
def home():
    return {"message": "Fabric Inventory API"}


# Login Page
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# Login Handler
@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return {"message": "Invalid username or password"}

    if user.password != password:
        return {"message": "Invalid username or password"}
    request.session["username"] = user.username
    request.session["role_id"] = user.role_id

    if user.role_id == 1:
        return RedirectResponse(
            url="/admin",
            status_code=303
        )

    elif user.role_id == 2:
        return RedirectResponse(
            url="/sales",
            status_code=303
        )

    elif user.role_id == 3:
        return RedirectResponse(
            url="/purchase",
            status_code=303
        )


# Admin Dashboard
@app.get("/admin")
def admin_dashboard(request: Request):

    if request.session.get("role_id") != 1:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
    request=request,
    name="admin.html",
    context={
        "username": request.session.get("username")
    }
)

# Sales Dashboard
@app.get("/sales")
def sales_dashboard(request: Request):

    role_id = request.session.get("role_id")

    if role_id not in [1, 2]:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="sales.html",
        context={
            "username": request.session.get("username")
        }
    )


# Purchase Dashboard
@app.get("/purchase")
def purchase_dashboard(request: Request):

    role_id = request.session.get("role_id")

    if role_id not in [1, 3]:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="purchase.html",
        context={
            "username": request.session.get("username")
        }
    )

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303
    )

@app.post("/upload-fabric-ui")
def upload_fabric_ui(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    imported = 0
    skipped = 0

    for _, row in df.iterrows():

        existing = db.query(Fabric).filter(
            Fabric.fabric_name == row["fabric_name"],
            Fabric.color == row["color"]
        ).first()

        if existing:
            skipped += 1
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
        imported += 1

    db.commit()

    return RedirectResponse(
        url="/admin",
        status_code=303
    )

@app.get("/materials/view")
def view_materials(
    request: Request,
    db: Session = Depends(get_db)
):

    materials = db.query(Material).all()

    return templates.TemplateResponse(
        request=request,
        name="materials.html",
        context={
            "materials": materials,
            "username": request.session.get("username")
        }
    )

@app.get("/materials/upload-success")
def upload_success(
    request: Request,
    imported: int = 0,
    skipped: int = 0
):
    return templates.TemplateResponse(
        request=request,
        name="upload_success.html",
        context={
            "imported": imported,
            "skipped": skipped
        }
    )

@app.get("/register")
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )

@app.post("/register")
def register_user(
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role_id: int = Form(...),
    db: Session = Depends(get_db)
):

    if password != confirm_password:
        return {"message": "Passwords do not match"}

    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    if existing_user:
        return {"message": "Username already exists"}

    new_user = User(
        username=username,
        password=password,
        role_id=role_id
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse(
        url="/login",
        status_code=303
    )

@app.get("/add-fabric")
def add_fabric_page(request: Request):

    role_id = request.session.get("role_id")

    return templates.TemplateResponse(
        request=request,
        name="add_fabric.html",
        context={
            "role_id": role_id
        }
    )


@app.post("/add-fabric")
def add_fabric(

    fabric_name: str = Form(...),
    fabric_type: str = Form(...),
    color: str = Form(""),
    gsm: float = Form(...),
    price_per_meter: float = Form(...),
    available_stock: int = Form(...),
    supplier_name: str = Form("")

):

    db = SessionLocal()

    fabric = Fabric(
        fabric_name=fabric_name,
        fabric_type=fabric_type,
        color=color,
        gsm=gsm,
        price_per_meter=price_per_meter,
        available_stock=available_stock,
        supplier_name=supplier_name
    )

    db.add(fabric)
    db.commit()

    return RedirectResponse(
        url="/view-fabrics",
        status_code=303
    )
@app.get("/edit-fabric/{fabric_id}")
def edit_fabric_page(
    request: Request,
    fabric_id: int
):

    db = SessionLocal()

    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_fabric.html",
        context={
            "fabric": fabric
        }
    )
@app.post("/edit-fabric/{fabric_id}")
def update_fabric_ui(

    fabric_id: int,

    fabric_name: str = Form(...),
    fabric_type: str = Form(...),
    color: str = Form(...),
    gsm: float = Form(...),
    price_per_meter: float = Form(...),
    available_stock: int = Form(...),
    supplier_name: str = Form(...)

):

    db = SessionLocal()

    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    fabric.fabric_name = fabric_name
    fabric.fabric_type = fabric_type
    fabric.color = color
    fabric.gsm = gsm
    fabric.price_per_meter = price_per_meter
    fabric.available_stock = available_stock
    fabric.supplier_name = supplier_name

    db.commit()

    return RedirectResponse(
        url="/view-fabrics",
        status_code=303
    )
@app.get("/delete-fabric/{fabric_id}")
def delete_fabric_ui(fabric_id: int):

    db = SessionLocal()

    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    if fabric:
        db.delete(fabric)
        db.commit()

    return RedirectResponse(
        url="/view-fabrics",
        status_code=303
    )
@app.get("/view-fabrics")
def view_fabrics(request: Request):

    role_id = request.session.get("role_id")

    db = SessionLocal()

    fabrics = db.query(Fabric).all()

    return templates.TemplateResponse(
        request=request,
        name="fabrics.html",
        context={
            "fabrics": fabrics,
            "role_id": role_id
        }
    )
@app.get("/update-stock/{fabric_id}")
def update_stock_page(
    request: Request,
    fabric_id: int
):

    db = SessionLocal()

    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="update_stock.html",
        context={
            "fabric": fabric
        }
    )
@app.post("/update-stock/{fabric_id}")
def update_stock_ui(

    fabric_id: int,
    available_stock: int = Form(...)

):

    db = SessionLocal()

    fabric = db.query(Fabric).filter(
        Fabric.id == fabric_id
    ).first()

    fabric.available_stock = available_stock

    db.commit()

    return RedirectResponse(
        url="/view-fabrics",
        status_code=303
    )
@app.get("/view-suppliers")
def view_suppliers(request: Request):

    role_id = request.session.get("role_id")

    db = SessionLocal()

    suppliers = db.query(Supplier).all()

    return templates.TemplateResponse(
        request=request,
        name="suppliers.html",
        context={
            "suppliers": suppliers,
            "role_id": role_id
        }
    )
@app.get("/add-supplier")
def add_supplier_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="add_supplier.html"
    )
@app.post("/add-supplier")
def add_supplier(

    supplier_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(...)

):

    db = SessionLocal()

    supplier = Supplier(
        supplier_name=supplier_name,
        contact_person=contact_person,
        phone=phone,
        email=email,
        address=address
    )

    db.add(supplier)

    db.commit()

    return RedirectResponse(
        url="/view-suppliers",
        status_code=303
    )
@app.get("/edit-supplier/{supplier_id}")
def edit_supplier_page(
    request: Request,
    supplier_id: int
):

    db = SessionLocal()

    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_supplier.html",
        context={
            "supplier": supplier
        }
    )
@app.post("/edit-supplier/{supplier_id}")
def edit_supplier(

    supplier_id: int,
    supplier_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(...)

):

    db = SessionLocal()

    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id
    ).first()

    supplier.supplier_name = supplier_name
    supplier.contact_person = contact_person
    supplier.phone = phone
    supplier.email = email
    supplier.address = address

    db.commit()

    return RedirectResponse(
        url="/view-suppliers",
        status_code=303
    )
@app.get("/delete-supplier/{supplier_id}")
def delete_supplier(supplier_id: int):

    db = SessionLocal()

    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id
    ).first()

    if supplier:
        db.delete(supplier)
        db.commit()

    return RedirectResponse(
        url="/view-suppliers",
        status_code=303
    )
@app.get("/view-purchases")
def view_purchases(request: Request):

    role_id = request.session.get("role_id")

    db = SessionLocal()

    purchases = db.query(PurchaseRecord).all()

    return templates.TemplateResponse(
        request=request,
        name="purchase_records.html",
        context={
            "purchases": purchases,
            "role_id": role_id
        }
    )
@app.get("/add-purchase")
def add_purchase_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="add_purchase.html"
    )
@app.post("/add-purchase")
def add_purchase(

    supplier_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    purchase_price: float = Form(...),
    purchase_date: str = Form(...)

):

    db = SessionLocal()

    purchase = PurchaseRecord(
        supplier_name=supplier_name,
        fabric_name=fabric_name,
        quantity=quantity,
        purchase_price=purchase_price,
        purchase_date=purchase_date
    )

    db.add(purchase)

    db.commit()

    return RedirectResponse(
        url="/view-purchases",
        status_code=303
    )
@app.get("/edit-purchase/{purchase_id}")
def edit_purchase_page(
    request: Request,
    purchase_id: int
):

    db = SessionLocal()

    purchase = db.query(PurchaseRecord).filter(
        PurchaseRecord.id == purchase_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_purchase.html",
        context={
            "purchase": purchase
        }
    )
@app.post("/edit-purchase/{purchase_id}")
def update_purchase(

    purchase_id: int,

    supplier_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    purchase_price: float = Form(...),
    purchase_date: str = Form(...)

):

    db = SessionLocal()

    purchase = db.query(PurchaseRecord).filter(
        PurchaseRecord.id == purchase_id
    ).first()

    purchase.supplier_name = supplier_name
    purchase.fabric_name = fabric_name
    purchase.quantity = quantity
    purchase.purchase_price = purchase_price
    purchase.purchase_date = purchase_date

    db.commit()

    return RedirectResponse(
        url="/view-purchases",
        status_code=303
    )
@app.get("/delete-purchase/{purchase_id}")
def delete_purchase(purchase_id: int):

    db = SessionLocal()

    purchase = db.query(PurchaseRecord).filter(
        PurchaseRecord.id == purchase_id
    ).first()

    if purchase:
        db.delete(purchase)
        db.commit()

    return RedirectResponse(
        url="/view-purchases",
        status_code=303
    )
@app.get("/view-sales")
def view_sales(request: Request):

    role_id = request.session.get("role_id")

    db = SessionLocal()

    sales = db.query(SalesOrder).all()

    return templates.TemplateResponse(
    request=request,
    name="sales_orders.html",
    context={
        "sales": sales,
        "role_id": role_id
    }
)
@app.get("/add-sales")
def add_sales_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="add_sales.html"
    )
@app.post("/add-sales")
def add_sales(
    customer_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    selling_price: float = Form(...),
    order_date: str = Form(...)
):

    db = SessionLocal()

    sale = SalesOrder(
        customer_name=customer_name,
        fabric_name=fabric_name,
        quantity=quantity,
        selling_price=selling_price,
        order_date=datetime.strptime(
            order_date,
            "%Y-%m-%d"
        ).date()
    )

    db.add(sale)
    db.commit()

    return RedirectResponse(
        url="/view-sales",
        status_code=303
    )
@app.get("/edit-sales/{sale_id}")
def edit_sales_page(request: Request, sale_id: int):

    db = SessionLocal()

    sale = db.query(SalesOrder).filter(
        SalesOrder.id == sale_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_sales.html",
        context={
            "sale": sale
        }
    )
@app.post("/edit-sales/{sale_id}")
def edit_sales(
    sale_id: int,
    customer_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    selling_price: float = Form(...),
    order_date: str = Form(...)
):

    db = SessionLocal()

    sale = db.query(SalesOrder).filter(
        SalesOrder.id == sale_id
    ).first()

    sale.customer_name = customer_name
    sale.fabric_name = fabric_name
    sale.quantity = quantity
    sale.selling_price = selling_price
    sale.order_date = datetime.strptime(
        order_date,
        "%Y-%m-%d"
    ).date()

    db.commit()

    return RedirectResponse(
        url="/view-sales",
        status_code=303
    )
@app.get("/sales-report")
def sales_report(request: Request):

    role_id = request.session.get("role_id")

    db = SessionLocal()

    sales = db.query(SalesOrder).all()

    total_orders = len(sales)

    total_revenue = sum(
        sale.selling_price * sale.quantity
        for sale in sales
    )

    return templates.TemplateResponse(
        request=request,
        name="sales_report.html",
        context={
            "sales": sales,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "role_id": role_id
        }
    )