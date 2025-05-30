from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging
from ..database import get_db
from .. import models, schemas
from ..security.authUtils import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Configure logger
logger = logging.getLogger("auth_service")
logger.setLevel(logging.INFO)
# Create console handler if none exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

router = APIRouter()

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Endpoint to get access token"""
    try:
        # Find user by username
        user = db.query(models.User).filter(models.User.username == form_data.username).first()
        
        # Validate user exists and password is correct
        if not user or not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {form_data.username}")
            return {
                "status": "error",
                "message": "Incorrect username or password"
            }
        
        # Create access token with expiration time
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login for user: {user.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        logger.error(f"Error during login process: {str(e)}")
        return {
            "status": "error",
            "message": f"Login failed due to server error: {str(e)}"
        }

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if username already exists
        db_user_by_username = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user_by_username:
            logger.warning(f"Registration attempt with existing username: {user.username}")
            return {
                "status": "error",
                "message": "Username already registered"
            }
        
        # Check if email already exists
        db_user_by_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_by_email:
            logger.warning(f"Registration attempt with existing email: {user.email}")
            return {
                "status": "error",
                "message": "Email already registered"
            }
        
        # Create new user with hashed password
        hashed_password = get_password_hash(user.password)
        db_user = models.User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            is_admin=user.is_admin
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User registered successfully: {user.username}")
        return db_user
    
    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        db.rollback()
        return {
            "status": "error",
            "message": f"Registration failed: {str(e)}"
        }
