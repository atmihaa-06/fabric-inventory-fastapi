from datetime import datetime

import pandas as pd
from fastapi import (
    FastAPI, Request, Form, Depends, UploadFile, File
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine, get_db, SessionLocal
from app.models import (
    Base, Role, User, Fabric, Material,
    Supplier, PurchaseRecord, SalesOrder
)
from app.routers import fabric
import app.routers.user as user
import app.routers.material as material


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    if db.query(Role).count() == 0:
        db.add_all([
            Role(role_id=1, role_name="admin"),
            Role(role_id=2, role_name="sales"),
            Role(role_id=3, role_name="purchase"),
        ])
        db.commit()
finally:
    db.close()


# --------------------------------------------------
# FASTAPI CONFIGURATION
# --------------------------------------------------

app = FastAPI(title="Fabric Inventory API")

app.add_middleware(
    SessionMiddleware,
    secret_key="fabric_inventory_secret"
)

templates = Jinja2Templates(directory="app/templates")

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.include_router(fabric.router)
app.include_router(user.router)
app.include_router(material.router)


# --------------------------------------------------
# ROLE CHECK
# --------------------------------------------------

def has_role(request: Request, allowed_roles: list[int]) -> bool:
    return request.session.get("role_id") in allowed_roles


def login_redirect():
    return RedirectResponse(url="/login", status_code=303)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {"message": "Fabric Inventory API"}


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    account = db.query(User).filter(
        User.username == username
    ).first()

    if not account or account.password != password:
        return {"message": "Invalid username or password"}

    request.session["username"] = account.username
    request.session["role_id"] = account.role_id

    if account.role_id == 1:
        return RedirectResponse("/admin", status_code=303)

    if account.role_id == 2:
        return RedirectResponse("/sales", status_code=303)

    if account.role_id == 3:
        return RedirectResponse("/purchase", status_code=303)

    if account.role_id == 4:
        return RedirectResponse("/sales-report", status_code=303)

    request.session.clear()
    return login_redirect()


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return login_redirect()


# --------------------------------------------------
# DASHBOARDS
# --------------------------------------------------

@app.get("/admin")
def admin_dashboard(request: Request):
    if not has_role(request, [1]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"username": request.session.get("username")}
    )


@app.get("/sales")
def sales_dashboard(request: Request):
    if not has_role(request, [1, 2]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="sales.html",
        context={"username": request.session.get("username")}
    )


@app.get("/purchase")
def purchase_dashboard(request: Request):
    if not has_role(request, [1, 3]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="purchase.html",
        context={"username": request.session.get("username")}
    )


# --------------------------------------------------
# EXCEL FABRIC UPLOAD
# --------------------------------------------------

@app.post("/upload-fabric-ui")
def upload_fabric_ui(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    try:
        if not file.filename or not file.filename.lower().endswith(
            (".xlsx", ".xls")
        ):
            return {"error": "Please upload a valid Excel file."}

        df = pd.read_excel(file.file)

        required_columns = [
            "fabric_name",
            "fabric_type",
            "color",
            "gsm",
            "price_per_meter",
            "available_stock",
            "supplier_name"
        ]

        missing = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing:
            return {
                "error": "Missing Excel columns: " + ", ".join(missing)
            }

        for _, row in df.iterrows():
            if pd.isna(row["fabric_name"]) or pd.isna(row["fabric_type"]):
                continue

            name = str(row["fabric_name"]).strip()
            fabric_type = str(row["fabric_type"]).strip()

            if not name or not fabric_type:
                continue

            gsm = pd.to_numeric(row["gsm"], errors="coerce")
            price = pd.to_numeric(
                row["price_per_meter"], errors="coerce"
            )
            stock = pd.to_numeric(
                row["available_stock"], errors="coerce"
            )

            if pd.isna(gsm) or pd.isna(price) or pd.isna(stock):
                continue

            if gsm < 0 or price < 0 or stock < 0:
                continue

            if not float(stock).is_integer():
                continue

            color = (
                "" if pd.isna(row["color"])
                else str(row["color"]).strip()
            )

            existing = db.query(Fabric).filter(
                Fabric.fabric_name == name,
                Fabric.color == color
            ).first()

            if existing:
                continue

            supplier_name = (
                "" if pd.isna(row["supplier_name"])
                else str(row["supplier_name"]).strip()
            )

            db.add(Fabric(
                fabric_name=name,
                fabric_type=fabric_type,
                color=color,
                gsm=float(gsm),
                price_per_meter=float(price),
                available_stock=int(stock),
                supplier_name=supplier_name
            ))

        db.commit()

        return RedirectResponse("/admin", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        file.file.close()


# --------------------------------------------------
# MATERIALS
# --------------------------------------------------

@app.get("/materials/view")
def view_materials(
    request: Request,
    db: Session = Depends(get_db)
):
    if not request.session.get("username"):
        return login_redirect()

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
    if not request.session.get("username"):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="upload_success.html",
        context={
            "imported": imported,
            "skipped": skipped
        }
    )


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

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

    if role_id not in [1, 2, 3, 4]:
        return {"message": "Invalid role"}

    existing = db.query(User).filter(
        User.username == username.strip()
    ).first()

    if existing:
        return {"message": "Username already exists"}

    new_user = User(
        username=username.strip(),
        password=password,
        role_id=role_id
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse("/login", status_code=303)


# --------------------------------------------------
# ADD FABRIC
# --------------------------------------------------

@app.get("/add-fabric")
def add_fabric_page(request: Request):
    if not has_role(request, [1, 3]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="add_fabric.html",
        context={"role_id": request.session.get("role_id")}
    )


@app.post("/add-fabric")
def add_fabric(
    request: Request,
    fabric_name: str = Form(...),
    fabric_type: str = Form(...),
    color: str = Form(""),
    gsm: float = Form(...),
    price_per_meter: float = Form(...),
    available_stock: int = Form(...),
    supplier_name: str = Form("")
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        if not fabric_name.strip() or not fabric_type.strip():
            return {"error": "Fabric name and type are required."}

        if gsm < 0 or price_per_meter < 0 or available_stock < 0:
            return {"error": "GSM, price and stock cannot be negative."}

        item = Fabric(
            fabric_name=fabric_name.strip(),
            fabric_type=fabric_type.strip(),
            color=color.strip(),
            gsm=gsm,
            price_per_meter=price_per_meter,
            available_stock=available_stock,
            supplier_name=supplier_name.strip()
        )

        db.add(item)
        db.commit()

        return RedirectResponse("/view-fabrics", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# VIEW FABRICS
# --------------------------------------------------

@app.get("/view-fabrics")
def view_fabrics(request: Request):
    if not has_role(request, [1, 2, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        fabrics = db.query(Fabric).all()

        return templates.TemplateResponse(
            request=request,
            name="fabrics.html",
            context={
                "fabrics": fabrics,
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()

@app.get("/fabrics/")
def fabric_inventory_page(request: Request):
    if not has_role(request, [1, 2, 3]):
        return login_redirect()

    db = SessionLocal()
    try:
        fabrics = db.query(Fabric).all()

        return templates.TemplateResponse(
            request=request,
            name="fabrics.html",
            context={
                "fabrics": fabrics,
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()
# --------------------------------------------------
# EDIT FABRIC
# --------------------------------------------------

@app.get("/edit-fabric/{fabric_id}")
def edit_fabric_page(request: Request, fabric_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        item = db.query(Fabric).filter(
            Fabric.id == fabric_id
        ).first()

        if not item:
            return {"error": "Fabric not found."}

        return templates.TemplateResponse(
            request=request,
            name="edit_fabric.html",
            context={"fabric": item}
        )
    finally:
        db.close()


@app.post("/edit-fabric/{fabric_id}")
def update_fabric_ui(
    request: Request,
    fabric_id: int,
    fabric_name: str = Form(...),
    fabric_type: str = Form(...),
    color: str = Form(...),
    gsm: float = Form(...),
    price_per_meter: float = Form(...),
    available_stock: int = Form(...),
    supplier_name: str = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        item = db.query(Fabric).filter(
            Fabric.id == fabric_id
        ).first()

        if not item:
            return {"error": "Fabric not found."}

        if not fabric_name.strip() or not fabric_type.strip():
            return {"error": "Fabric name and type are required."}

        if gsm < 0 or price_per_meter < 0 or available_stock < 0:
            return {"error": "GSM, price and stock cannot be negative."}

        item.fabric_name = fabric_name.strip()
        item.fabric_type = fabric_type.strip()
        item.color = color.strip()
        item.gsm = gsm
        item.price_per_meter = price_per_meter
        item.available_stock = available_stock
        item.supplier_name = supplier_name.strip()

        db.commit()

        return RedirectResponse("/view-fabrics", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# DELETE FABRIC
# --------------------------------------------------

@app.get("/delete-fabric/{fabric_id}")
def delete_fabric_ui(request: Request, fabric_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        item = db.query(Fabric).filter(
            Fabric.id == fabric_id
        ).first()

        if item:
            db.delete(item)
            db.commit()

        return RedirectResponse("/view-fabrics", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# UPDATE STOCK
# --------------------------------------------------

@app.get("/update-stock/{fabric_id}")
def update_stock_page(request: Request, fabric_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        item = db.query(Fabric).filter(
            Fabric.id == fabric_id
        ).first()

        if not item:
            return {"error": "Fabric not found."}

        return templates.TemplateResponse(
            request=request,
            name="update_stock.html",
            context={"fabric": item}
        )
    finally:
        db.close()


@app.post("/update-stock/{fabric_id}")
def update_stock_ui(
    request: Request,
    fabric_id: int,
    available_stock: int = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        if available_stock < 0:
            return {"error": "Stock cannot be negative."}

        item = db.query(Fabric).filter(
            Fabric.id == fabric_id
        ).first()

        if not item:
            return {"error": "Fabric not found."}

        item.available_stock = available_stock
        db.commit()

        return RedirectResponse("/view-fabrics", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# SUPPLIERS
# --------------------------------------------------

@app.get("/view-suppliers")
def view_suppliers(request: Request):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        suppliers = db.query(Supplier).all()

        return templates.TemplateResponse(
            request=request,
            name="suppliers.html",
            context={
                "suppliers": suppliers,
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()


@app.get("/add-supplier")
def add_supplier_page(request: Request):
    if not has_role(request, [1, 3]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="add_supplier.html"
    )


@app.post("/add-supplier")
def add_supplier(
    request: Request,
    supplier_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        name = supplier_name.strip()

        if not name:
            return {"error": "Supplier name is required."}

        if not phone.strip():
            return {"error": "Phone number is required."}

        existing = db.query(Supplier).filter(
            Supplier.supplier_name == name
        ).first()

        if existing:
            return {"error": "A supplier with this name already exists."}

        supplier = Supplier(
            supplier_name=name,
            contact_person=contact_person.strip(),
            phone=phone.strip(),
            email=email.strip(),
            address=address.strip()
        )

        db.add(supplier)
        db.commit()

        return RedirectResponse("/view-suppliers", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/edit-supplier/{supplier_id}")
def edit_supplier_page(request: Request, supplier_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        supplier = db.query(Supplier).filter(
            Supplier.id == supplier_id
        ).first()

        if not supplier:
            return {"error": "Supplier not found."}

        return templates.TemplateResponse(
            request=request,
            name="edit_supplier.html",
            context={"supplier": supplier}
        )
    finally:
        db.close()


@app.post("/edit-supplier/{supplier_id}")
def edit_supplier(
    request: Request,
    supplier_id: int,
    supplier_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        supplier = db.query(Supplier).filter(
            Supplier.id == supplier_id
        ).first()

        if not supplier:
            return {"error": "Supplier not found."}

        supplier.supplier_name = supplier_name.strip()
        supplier.contact_person = contact_person.strip()
        supplier.phone = phone.strip()
        supplier.email = email.strip()
        supplier.address = address.strip()

        db.commit()

        return RedirectResponse("/view-suppliers", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/delete-supplier/{supplier_id}")
def delete_supplier(request: Request, supplier_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        supplier = db.query(Supplier).filter(
            Supplier.id == supplier_id
        ).first()

        if not supplier:
            return {"error": "Supplier not found."}

        purchase = db.query(PurchaseRecord).filter(
            PurchaseRecord.supplier_name == supplier.supplier_name
        ).first()

        if purchase:
            return {
                "error": (
                    "Cannot delete this supplier because purchase "
                    "records reference this supplier."
                )
            }

        db.delete(supplier)
        db.commit()

        return RedirectResponse("/view-suppliers", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# PURCHASE RECORDS
# --------------------------------------------------

@app.get("/view-purchases")
def view_purchases(request: Request):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        purchases = db.query(PurchaseRecord).all()

        return templates.TemplateResponse(
            request=request,
            name="purchase_records.html",
            context={
                "purchases": purchases,
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()



@app.get('/add-purchase')
def add_purchase_page(request: Request):
    if not has_role(request, [1, 3]):
        return RedirectResponse(url='/login', status_code=303)

    return templates.TemplateResponse(
        request=request,
        name='add_purchase.html',
        context={
            'role_id': request.session.get('role_id'),
            'username': request.session.get('username')
        }
    )



@app.post("/add-purchase")
def add_purchase(
    request: Request,
    supplier_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    purchase_price: float = Form(...),
    purchase_date: str = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        if quantity <= 0 or purchase_price < 0:
            return {
                "error": "Quantity must be positive and price cannot be negative."
            }

        item = next(
            (
                f for f in db.query(Fabric).all()
                if f.fabric_name.strip().casefold()
                == fabric_name.strip().casefold()
            ),
            None
        )

        if not item:
            return {"error": "Fabric was not found."}

        purchase = PurchaseRecord(
            supplier_name=supplier_name.strip(),
            fabric_name=item.fabric_name,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_date=purchase_date
        )

        item.available_stock += quantity
        db.add(purchase)
        db.commit()

        return RedirectResponse("/view-purchases", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/edit-purchase/{purchase_id}")
def update_purchase(
    request: Request,
    purchase_id: int,
    supplier_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    purchase_price: float = Form(...),
    purchase_date: str = Form(...)
):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        purchase = db.query(PurchaseRecord).filter(
            PurchaseRecord.id == purchase_id
        ).first()

        if not purchase:
            return {"error": "Purchase record not found."}

        if quantity <= 0 or purchase_price < 0:
            return {
                "error": "Quantity must be positive and price cannot be negative."
            }

        fabrics = db.query(Fabric).all()

        old_fabric = next(
            (
                f for f in fabrics
                if f.fabric_name.strip().casefold()
                == purchase.fabric_name.strip().casefold()
            ),
            None
        )

        new_fabric = next(
            (
                f for f in fabrics
                if f.fabric_name.strip().casefold()
                == fabric_name.strip().casefold()
            ),
            None
        )

        if not old_fabric or not new_fabric:
            return {"error": "Original or selected fabric was not found."}

        if old_fabric.id == new_fabric.id:
            adjusted_stock = (
                old_fabric.available_stock - purchase.quantity + quantity
            )

            if adjusted_stock < 0:
                return {"error": "This edit would make stock negative."}

            old_fabric.available_stock = adjusted_stock

        else:
            if old_fabric.available_stock < purchase.quantity:
                return {
                    "error": "Original fabric stock is too low to reverse this purchase."
                }

            old_fabric.available_stock -= purchase.quantity
            new_fabric.available_stock += quantity

        purchase.supplier_name = supplier_name.strip()
        purchase.fabric_name = new_fabric.fabric_name
        purchase.quantity = quantity
        purchase.purchase_price = purchase_price
        purchase.purchase_date = purchase_date

        db.commit()

        return RedirectResponse("/view-purchases", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/delete-purchase/{purchase_id}")
def delete_purchase(request: Request, purchase_id: int):
    if not has_role(request, [1, 3]):
        return login_redirect()

    db = SessionLocal()

    try:
        purchase = db.query(PurchaseRecord).filter(
            PurchaseRecord.id == purchase_id
        ).first()

        if not purchase:
            return {"error": "Purchase record not found."}

        item = next(
            (
                f for f in db.query(Fabric).all()
                if f.fabric_name.strip().casefold()
                == purchase.fabric_name.strip().casefold()
            ),
            None
        )

        if not item:
            return {"error": "Fabric not found. Purchase was not deleted."}

        if item.available_stock < purchase.quantity:
            return {
                "error": "Deleting this purchase would make stock negative."
            }

        item.available_stock -= purchase.quantity
        db.delete(purchase)
        db.commit()

        return RedirectResponse("/view-purchases", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# SALES
# --------------------------------------------------

@app.get("/view-sales")
def view_sales(request: Request):
    if not has_role(request, [1, 2]):
        return login_redirect()

    db = SessionLocal()

    try:
        sales = db.query(SalesOrder).all()

        return templates.TemplateResponse(
            request=request,
            name="sales_orders.html",
            context={
                "sales": sales,
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()


@app.get("/add-sales")
def add_sales_page(request: Request):
    if not has_role(request, [1, 2]):
        return login_redirect()

    return templates.TemplateResponse(
        request=request,
        name="add_sales.html"
    )


@app.post("/add-sales")
def add_sales(
    request: Request,
    customer_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    selling_price: float = Form(...),
    order_date: str = Form(...)
):
    if not has_role(request, [1, 2]):
        return login_redirect()

    db = SessionLocal()

    try:
        if quantity <= 0 or selling_price < 0:
            return {
                "error": "Quantity must be positive and price cannot be negative."
            }

        item = next(
            (
                f for f in db.query(Fabric).all()
                if f.fabric_name.strip().casefold()
                == fabric_name.strip().casefold()
            ),
            None
        )

        if not item:
            return {"error": "Fabric was not found."}

        if item.available_stock < quantity:
            return {
                "error": (
                    f"Insufficient stock. Available: "
                    f"{item.available_stock}, requested: {quantity}."
                )
            }

        parsed_date = datetime.strptime(
            order_date, "%Y-%m-%d"
        ).date()

        sale = SalesOrder(
            customer_name=customer_name.strip(),
            fabric_name=item.fabric_name,
            quantity=quantity,
            selling_price=selling_price,
            order_date=parsed_date
        )

        item.available_stock -= quantity
        db.add(sale)
        db.commit()

        return RedirectResponse("/view-sales", status_code=303)

    except ValueError:
        db.rollback()
        return {"error": "Invalid order date."}

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/edit-sales/{sale_id}")
def edit_sales_page(request: Request, sale_id: int):
    if not has_role(request, [1, 2]):
        return login_redirect()

    db = SessionLocal()

    try:
        sale = db.query(SalesOrder).filter(
            SalesOrder.id == sale_id
        ).first()

        if not sale:
            return {"error": "Sales order not found."}

        return templates.TemplateResponse(
            request=request,
            name="edit_sales.html",
            context={"sale": sale}
        )
    finally:
        db.close()


@app.post("/edit-sales/{sale_id}")
def edit_sales(
    request: Request,
    sale_id: int,
    customer_name: str = Form(...),
    fabric_name: str = Form(...),
    quantity: int = Form(...),
    selling_price: float = Form(...),
    order_date: str = Form(...)
):
    if not has_role(request, [1, 2]):
        return login_redirect()

    db = SessionLocal()

    try:
        sale = db.query(SalesOrder).filter(
            SalesOrder.id == sale_id
        ).first()

        if not sale:
            return {"error": "Sales order not found."}

        if quantity <= 0 or selling_price < 0:
            return {
                "error": "Quantity must be positive and price cannot be negative."
            }

        fabrics = db.query(Fabric).all()

        old_fabric = next(
            (
                f for f in fabrics
                if f.fabric_name.strip().casefold()
                == sale.fabric_name.strip().casefold()
            ),
            None
        )

        new_fabric = next(
            (
                f for f in fabrics
                if f.fabric_name.strip().casefold()
                == fabric_name.strip().casefold()
            ),
            None
        )

        if not old_fabric or not new_fabric:
            return {"error": "Original or selected fabric was not found."}

        if old_fabric.id == new_fabric.id:
            adjusted_stock = (
                old_fabric.available_stock + sale.quantity - quantity
            )

            if adjusted_stock < 0:
                return {"error": "Insufficient stock for this edit."}

            old_fabric.available_stock = adjusted_stock

        else:
            if new_fabric.available_stock < quantity:
                return {
                    "error": f"Insufficient stock for {new_fabric.fabric_name}."
                }

            old_fabric.available_stock += sale.quantity
            new_fabric.available_stock -= quantity

        parsed_date = datetime.strptime(
            order_date, "%Y-%m-%d"
        ).date()

        sale.customer_name = customer_name.strip()
        sale.fabric_name = new_fabric.fabric_name
        sale.quantity = quantity
        sale.selling_price = selling_price
        sale.order_date = parsed_date

        db.commit()

        return RedirectResponse("/view-sales", status_code=303)

    except ValueError:
        db.rollback()
        return {"error": "Invalid order date."}

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/delete-sales/{sale_id}")
def delete_sales(request: Request, sale_id: int):
    if not has_role(request, [1, 2]):
        return login_redirect()

    db = SessionLocal()

    try:
        sale = db.query(SalesOrder).filter(
            SalesOrder.id == sale_id
        ).first()

        if not sale:
            return {"error": "Sales order not found."}

        item = next(
            (
                f for f in db.query(Fabric).all()
                if f.fabric_name.strip().casefold()
                == sale.fabric_name.strip().casefold()
            ),
            None
        )

        if not item:
            return {"error": "Fabric not found. Sales order was not deleted."}

        item.available_stock += sale.quantity
        db.delete(sale)
        db.commit()

        return RedirectResponse("/view-sales", status_code=303)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# --------------------------------------------------
# SALES REPORT
# --------------------------------------------------

@app.get("/sales-report")
def sales_report(request: Request):
    if not has_role(request, [1, 2, 4]):
        return login_redirect()

    db = SessionLocal()

    try:
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
                "role_id": request.session.get("role_id")
            }
        )
    finally:
        db.close()