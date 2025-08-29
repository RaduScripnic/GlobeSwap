from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Trip, SkillSwap

# ----------------------------
# Flask App Configuration
# ----------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///globeswap.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "supersecret"  # For flash messages

# Initialize DB and Migration
db.init_app(app)
migrate = Migrate(app, db)

# ----------------------------
# Home Route
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# Users Management
# ----------------------------
@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")

        # Validation
        if not username or not email:
            flash("⚠️ Username and Email are required!", "warning")
            return redirect(url_for("users"))

        # Check duplicates
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("❌ Username or email already exists.", "danger")
            return redirect(url_for("users"))

        try:
            new_user = User(username=username, email=email)
            db.session.add(new_user)
            db.session.commit()
            flash("✅ User added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"🚨 Error: {str(e)}", "danger")

        return redirect(url_for("users"))

    users = User.query.all()
    return render_template("users.html", users=users)

# ----------------------------
# Trips Management
# ----------------------------
@app.route("/trips", methods=["GET", "POST"])
def trips():
    if request.method == "POST":
        destination = request.form.get("destination")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        user_id = request.form.get("user_id")

        if not destination or not start_date or not end_date or not user_id:
            flash("⚠️ All fields are required!", "warning")
            return redirect(url_for("trips"))

        try:
            new_trip = Trip(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
            )
            db.session.add(new_trip)
            db.session.commit()
            flash("✅ Trip added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"🚨 Error: {str(e)}", "danger")

        return redirect(url_for("trips"))

    trips = Trip.query.all()
    users = User.query.all()
    return render_template("trips.html", trips=trips, users=users)

# ----------------------------
# SkillSwap Management
# ----------------------------
@app.route("/skillswap", methods=["GET", "POST"])
def skillswap():
    if request.method == "POST":
        offered_skill = request.form.get("offered_skill")
        desired_skill = request.form.get("desired_skill")
        user_id = request.form.get("user_id")

        if not offered_skill or not desired_skill or not user_id:
            flash("⚠️ All fields are required!", "warning")
            return redirect(url_for("skillswap"))

        try:
            new_swap = SkillSwap(
                offered_skill=offered_skill,
                desired_skill=desired_skill,
                user_id=user_id,
            )
            db.session.add(new_swap)
            db.session.commit()
            flash("✅ SkillSwap created successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"🚨 Error: {str(e)}", "danger")

        return redirect(url_for("skillswap"))

    swaps = SkillSwap.query.all()
    users = User.query.all()
    return render_template("skillswap.html", swaps=swaps, users=users)

# ----------------------------
# Error Handlers
# ----------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
