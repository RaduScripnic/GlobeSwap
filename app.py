from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Trip, SkillSwap
from datetime import datetime 

# ----------------------------
# Flask App Configuration
# ----------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///globeswap_new.db" # Changed from globeswap.db
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "supersecret"  # For flash messages

# Initialize DB and Migration
db.init_app(app)
migrate = Migrate(app, db)

# DEVELOPMENT HACK: Add this block to ensure tables are created/checked on startup
with app.app_context():
    # Attempt to create all tables if they don't exist. 
    # This often fixes issues where a migration failed to apply a new column.
    db.create_all()

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
# Listing Creation (Combined Trip/Accommodation)
# ----------------------------
@app.route("/list", methods=["GET", "POST"])
def create_listing():
    users = User.query.all()
    if request.method == "POST":
        # Data from Trip Model fields
        destination = request.form.get("destination")
        start_date_str = request.form.get("start_date") 
        end_date_str = request.form.get("end_date")     
        
        # Data from SkillSwap Model fields
        offered_skill = request.form.get("offered_skill")
        desired_skill = request.form.get("desired_skill")

        # Flag to distinguish listing type
        listing_type = request.form.get("listing_type") # 'seek' or 'offer'
        is_offer = listing_type == 'offer'

        user_id = request.form.get("user_id")

        if not all([destination, start_date_str, end_date_str, offered_skill, desired_skill, user_id, listing_type]):
            flash("⚠️ All form fields are required!", "warning")
            return redirect(url_for("create_listing"))

        try:
            # 1. Create the Trip/Accommodation listing
            DATE_FORMAT = "%Y-%m-%d"
            start_date_obj = datetime.strptime(start_date_str, DATE_FORMAT).date()
            end_date_obj = datetime.strptime(end_date_str, DATE_FORMAT).date()
            
            new_trip = Trip(
                destination=destination,
                start_date=start_date_obj, 
                end_date=end_date_obj,
                is_accommodation_offer=is_offer,
                user_id=user_id,
            )
            db.session.add(new_trip)
            db.session.flush() # Get the new_trip.id before commit

            # 2. Create the associated SkillSwap requirement/offer
            new_swap = SkillSwap(
                skill_offered=offered_skill,
                skill_wanted=desired_skill, 
                user_id=user_id,
            )
            db.session.add(new_swap)
            db.session.commit()

            flash(f"✅ {'Accommodation Offer' if is_offer else 'Trip Request'} added successfully!", "success")
        
        except ValueError:
            db.session.rollback()
            flash("🚨 Error: Start date or End date is not in the required YYYY-MM-DD format.", "danger")
            return redirect(url_for("create_listing"))
            
        except Exception as e:
            db.session.rollback()
            flash(f"🚨 Error during listing creation: {str(e)}", "danger")

        return redirect(url_for("trips"))
        
    return render_template("list.html", users=users)


# ----------------------------
# Marketplace View (formerly Trips Management)
# ----------------------------
@app.route("/trips")
def trips():
    # Queries the two distinct types of listings
    trip_requests = Trip.query.filter_by(is_accommodation_offer=False).all()
    accommodation_offers = Trip.query.filter_by(is_accommodation_offer=True).all()
    
    # We also need the SkillSwap data associated with the listings.
    # For a small application, fetching all swaps and matching in the template is simplest.
    all_swaps = {swap.user_id: swap for swap in SkillSwap.query.all()}


    return render_template(
        "marketplace.html", 
        requests=trip_requests, 
        offers=accommodation_offers,
        all_swaps=all_swaps
    )

# ----------------------------
# Error Handlers
# ----------------------------
@app.errorhandler(404)
def not_found(e):
    # This assumes 404.html is available in the templates folder
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
