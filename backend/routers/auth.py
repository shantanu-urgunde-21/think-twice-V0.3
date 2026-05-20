from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import timedelta
from auth import AdminLogin, Token, authenticate_admin, create_access_token, require_admin
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(credentials: AdminLogin, db: Session = Depends(get_db)):
    if not authenticate_admin(credentials.username, credentials.password, db):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": credentials.username}, expires_delta=timedelta(minutes=480)
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/verify")
def verify_admin(admin: str = Depends(require_admin)):
    return {"authenticated": True}
