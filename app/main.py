from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Dict
import models
import database
from database import SessionLocal, engine

# Create tables
models.Base.metadata.create_all(bind=engine)

# Create default user if not exists
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

app = FastAPI(title="75 Hard Tracker")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register")
async def register_user(username: str, password: str, db: Session = Depends(get_db)):
    # Add user registration logic here
    pass

@app.post("/day/complete")
async def complete_tasks(
    tasks: Dict[str, bool],
    db: Session = Depends(get_db)
):
    try:
        today = date.today()
        
        # Check if entry already exists for today
        existing_entry = db.query(models.Day).filter(
            models.Day.date == today,
            models.Day.completed == True  # Only block if they completed all tasks
        ).first()
        
        if existing_entry:
            next_available = today + timedelta(days=1)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "You've already completed your tasks for today!",
                    "next_available": next_available.strftime("%Y-%m-%d"),
                    "total_days": db.query(models.Day).filter_by(completed=True).count(),
                    "current_streak": db.query(models.User).filter_by(id=1).first().current_streak
                }
            )

        # Get or create today's entry
        day_entry = db.query(models.Day).filter(
            models.Day.date == today
        ).first()
        
        if not day_entry:
            day_entry = models.Day(
                date=today,
                user_id=1
            )
            db.add(day_entry)
        
        # Update tasks
        day_entry.workout_1 = tasks.get('workout_1', False)
        day_entry.workout_2 = tasks.get('workout_2', False)
        day_entry.diet = tasks.get('diet', False)
        day_entry.water = tasks.get('water', False)
        day_entry.reading = tasks.get('reading', False)
        day_entry.progress_picture = tasks.get('progress_picture', False)
        
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
        
        # Update user's progress
        user = db.query(models.User).filter_by(id=1).first()
        
        if all_completed:
            user.current_streak += 1
            user.best_streak = max(user.best_streak, user.current_streak)
        else:
            user.current_streak = 0
        
        db.commit()
        
        # Get total completed days
        total_days = db.query(models.Day).filter_by(completed=True).count()
        
        return {
            "total_days": total_days,
            "current_streak": user.current_streak,
            "message": "Progress saved successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@app.get("/progress")
async def get_progress(db: Session = Depends(get_db)):
    # Add progress tracking logic here
    pass