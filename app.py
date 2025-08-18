from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import db, User, Trip, SkillSwap

app = Flask(__name__)

# Configure SQLite database (simple for dev)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///globeswap.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Init DB + Migrate
db.init_app(app)
migrate = Migrate(app, db)

# ----------------------
# Routes
# ----------------------

@app.route("/")
def home():
    return jsonify({"message": "🌍 Welcome to GlobeSwap API"})


# --- User Routes ---
@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    new_user = User(username=data["username"], email=data["email"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created", "user": new_user.username}), 201


@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "username": u.username, "email": u.email} for u in users])


# --- Trip Routes ---
@app.route("/trips", methods=["POST"])
def create_trip():
    data = request.json
    new_trip = Trip(
        destination=data["destination"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        notes=data.get("notes", ""),
        user_id=data["user_id"],
    )
    db.session.add(new_trip)
    db.session.commit()
    return jsonify({"message": "Trip added", "destination": new_trip.destination}), 201


@app.route("/trips/<int:user_id>", methods=["GET"])
def get_trips(user_id):
    trips = Trip.query.filter_by(user_id=user_id).all()
    return jsonify([
        {"id": t.id, "destination": t.destination, "start": t.start_date, "end": t.end_date, "notes": t.notes}
        for t in trips
    ])


# --- Skill Swap Routes ---
@app.route("/skills", methods=["POST"])
def create_skill():
    data = request.json
    new_skill = SkillSwap(
        skill_offered=data["skill_offered"],
        skill_requested=data["skill_requested"],
        description=data.get("description", ""),
        user_id=data["user_id"],
    )
    db.session.add(new_skill)
    db.session.commit()
    return jsonify({"message": "SkillSwap created"}), 201


@app.route("/skills/<int:user_id>", methods=["GET"])
def get_skills(user_id):
    skills = SkillSwap.query.filter_by(user_id=user_id).all()
    return jsonify([
        {"id": s.id, "offered": s.skill_offered, "requested": s.skill_requested, "description": s.description}
        for s in skills
    ])


if __name__ == "__main__":
    app.run(debug=True)
