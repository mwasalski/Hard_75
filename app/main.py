from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Dict
import models
import database
from database import SessionLocal, engine
import jwt
import base64
from pydantic import BaseModel

# Secret key for JWT tokens
SECRET_KEY = "your-secret-key-here"  # In production, use a proper secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="75 Hard Tracker")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Initialize database with default user if needed
def init_db():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=1).first()
        if not user:
            default_user = models.User(
                id=1,
                username="default",
                hashed_password="default",
                current_streak=0,
                best_streak=0
            )
            db.add(default_user)
            db.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        db.close()

init_db()

# Add this class for request validation
class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Username already registered"}
            )
        
        hashed_password = models.User.get_password_hash(user.password)
        new_user = models.User(
            username=user.username, 
            hashed_password=hashed_password,
            current_streak=0,
            best_streak=0
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"Registration error: {str(e)}"}
        )

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not models.User.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/progress-pictures")
async def get_progress_pictures(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get first picture
    first_day = db.query(models.Day).filter(
        models.Day.user_id == current_user.id,
        models.Day.image_data != None
    ).order_by(models.Day.date.asc()).first()

    # Get latest picture
    latest_day = db.query(models.Day).filter(
        models.Day.user_id == current_user.id,
        models.Day.image_data != None
    ).order_by(models.Day.date.desc()).first()

    result = {}
    if first_day:
        result["first_picture"] = base64.b64encode(first_day.image_data).decode()
        result["first_date"] = first_day.date.strftime("%Y-%m-%d")
    
    if latest_day and latest_day != first_day:
        result["latest_picture"] = base64.b64encode(latest_day.image_data).decode()
        result["latest_date"] = latest_day.date.strftime("%Y-%m-%d")
        result["latest_day"] = db.query(models.Day).filter(
            models.Day.user_id == current_user.id,
            models.Day.completed == True,
            models.Day.date <= latest_day.date
        ).count()

    return result

@app.post("/day/complete")
async def complete_tasks(
    tasks: Dict[str, bool | str],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        today = date.today()
        
        # Check if entry already exists for today
        existing_entry = db.query(models.Day).filter(
            models.Day.date == today,
            models.Day.user_id == current_user.id,
            models.Day.completed == True
        ).first()
        
        if existing_entry:
            next_available = today + timedelta(days=1)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "You've already completed your tasks for today!",
                    "next_available": next_available.strftime("%Y-%m-%d"),
                    "total_days": db.query(models.Day).filter_by(completed=True, user_id=current_user.id).count(),
                    "current_streak": current_user.current_streak
                }
            )

        # Get or create today's entry
        day_entry = db.query(models.Day).filter(
            models.Day.date == today,
            models.Day.user_id == current_user.id
        ).first()
        
        if not day_entry:
            day_entry = models.Day(
                date=today,
                user_id=current_user.id
            )
            db.add(day_entry)
        
        # Update tasks
        day_entry.workout_1 = tasks.get('workout_1', False)
        day_entry.workout_2 = tasks.get('workout_2', False)
        day_entry.diet = tasks.get('diet', False)
        day_entry.water = tasks.get('water', False)
        day_entry.reading = tasks.get('reading', False)
        day_entry.progress_picture = tasks.get('progress_picture', False)
        
        if tasks.get("image_data"):
            day_entry.image_data = base64.b64decode(tasks["image_data"])
        
        # Check if all tasks are completed
        all_completed = all([
            day_entry.workout_1,
            day_entry.workout_2,
            day_entry.diet,
            day_entry.water,
            day_entry.reading,
            day_entry.progress_picture
        ])
        
        day_entry.completed = all_completed
        
        if all_completed:
            current_user.current_streak += 1
            current_user.best_streak = max(current_user.best_streak, current_user.current_streak)
        else:
            current_user.current_streak = 0
        
        db.commit()
        
        # Get total completed days
        total_days = db.query(models.Day).filter_by(completed=True, user_id=current_user.id).count()
        
        return {
            "total_days": total_days,
            "current_streak": current_user.current_streak,
            "message": "Progress saved successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )