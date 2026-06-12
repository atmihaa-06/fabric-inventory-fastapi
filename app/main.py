from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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