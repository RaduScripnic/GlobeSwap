from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# --- User Table ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    trips = db.relationship("Trip", backref="user", lazy=True)
    skills = db.relationship("SkillSwap", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


# --- Trip Logging Table ---
class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<Trip {self.destination} ({self.start_date} → {self.end_date})>"


# --- Skill Swap Table ---
class SkillSwap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_offered = db.Column(db.String(120), nullable=False)
    skill_requested = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<SkillSwap {self.skill_offered} ↔ {self.skill_requested}>"
