from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ------------------------
# User Model
# ------------------------
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    trips = db.relationship("Trip", backref="user", cascade="all, delete-orphan")
    skillswaps = db.relationship("SkillSwap", backref="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


# ------------------------
# Trip Model (Now supports Accommodation Offers)
# ------------------------
class Trip(db.Model):
    __tablename__ = "trip"
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NEW COLUMN: True if a local is offering their home; False if a user is traveling.
    is_accommodation_offer = db.Column(db.Boolean, default=False, nullable=False) 

    # Foreign key to user
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<Trip {self.destination}>"


# ------------------------
# SkillSwap Model
# ------------------------
class SkillSwap(db.Model):
    __tablename__ = "skillswap"
    id = db.Column(db.Integer, primary_key=True)
    skill_offered = db.Column(db.String(120), nullable=False)
    skill_wanted = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key to user
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<SkillSwap {self.skill_offered} for {self.skill_wanted}>"
