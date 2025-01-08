from sqlalchemy import Boolean, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    days = relationship("Day", back_populates="user")
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)

class Day(Base):
    __tablename__ = "days"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    user_id = Column(Integer, ForeignKey("users.id"))
    workout_1 = Column(Boolean, default=False)
    workout_2 = Column(Boolean, default=False)
    diet = Column(Boolean, default=False)
    water = Column(Boolean, default=False)
    reading = Column(Boolean, default=False)
    progress_picture = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    user = relationship("User", back_populates="days")
