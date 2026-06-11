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

from starlette.middleware.sessions import SessionMiddleware


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

    role = request.session.get("role")

    if role_id not in [1,2]:
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

    role = request.session.get("role")

    if role_id not in [1,3]:
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