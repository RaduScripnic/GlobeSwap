from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_migrate import Migrate
from models import db, User, Trip, SkillSwap

app = Flask(__name__)

# Configure SQLite database
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
    return render_template("base.html")

# --- User Routes ---
@app.route("/users", methods=["GET"])
def list_users():
    users = User.query.all()
    return render_template("users.html", users=users)

@app.route("/users", methods=["POST"])
def create_user():
    data = request.form
    new_user = User(username=data["username"], email=data["email"])
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for("list_users"))

# --- Trip Routes ---
@app.route("/trips/<int:user_id>")
def list_trips(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("trips.html", user=user, trips=user.trips)

@app.route("/trips/add", methods=["POST"])
def create_trip():
    data = request.form
    new_trip = Trip(
        destination=data["destination"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        notes=data.get("notes", ""),
        user_id=data["user_id"]
    )
    db.session.add(new_trip)
    db.session.commit()
    return redirect(url_for("list_trips", user_id=data["user_id"]))

# --- Skill Swap Routes ---
@app.route("/skills/<int:user_id>")
def list_skills(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("skills.html", user=user, skills=user.skills)

@app.route("/skills/add", methods=["POST"])
def create_skill():
    data = request.form
    new_skill = SkillSwap(
        skill_offered=data["skill_offered"],
        skill_requested=data["skill_requested"],
        description=data.get("description", ""),
        user_id=data["user_id"]
    )
    db.session.add(new_skill)
    db.session.commit()
    return redirect(url_for("list_skills", user_id=data["user_id"]))

if __name__ == "__main__":
    app.run(debug=True)
