from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date
from sqlalchemy import exc

# --- AUTHENTICATION IMPORTS ---
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField 
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length

# --- DATABASE SETUP ---
app = Flask(__name__)
# Changed DB name to ensure new schema is created
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///globeswap_new.db" 
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_strong_secret_key_here" # Required for Flask-Login and Flask-WTF

# INITIALIZE SQLAlchemy HERE
db = SQLAlchemy(app) 

migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Set the view function for logging in


# --- USER LOADER FOR FLASK-LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    """Callback function used by Flask-Login to reload the user object from the session."""
    return db.session.get(User, int(user_id))

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    trips = db.relationship("Trip", backref="user", cascade="all, delete-orphan")
    skillswaps = db.relationship("SkillSwap", backref="user", cascade="all, delete-orphan")
    sent_interactions = db.relationship("Interaction", foreign_keys='Interaction.sender_id', backref="sender", lazy='dynamic', cascade="all, delete-orphan")
    received_interactions = db.relationship("Interaction", foreign_keys='Interaction.recipient_id', backref="recipient", lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Trip(db.Model):
    __tablename__ = "trip"
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_accommodation_offer = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    interactions = db.relationship("Interaction", backref="trip", lazy='dynamic', cascade="all, delete-orphan")
    # FIXED: One-to-one relationship with SkillSwap, accessible via 'trip.skillswap'.
    skillswap = db.relationship("SkillSwap", backref="trip", uselist=False, cascade="all, delete-orphan") 

    def __repr__(self):
        return f"<Trip {self.destination}>"


class SkillSwap(db.Model):
    __tablename__ = "skillswap"
    id = db.Column(db.Integer, primary_key=True)
    skill_offered = db.Column(db.String(120), nullable=False)
    skill_wanted = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # FIXED: Foreign Key to Trip, ensuring a one-to-one relationship with 'unique=True'
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), unique=True, nullable=False)
    
    def __repr__(self):
        return f"<SkillSwap {self.skill_offered} for {self.skill_wanted}>"


class Interaction(db.Model):
    __tablename__ = "interaction"
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending", nullable=False) # e.g., Pending, Accepted, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Interaction {self.id} for Trip {self.trip_id} from {self.sender_id} to {self.recipient_id}>"


# --- AUTHENTICATION FORMS ---

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class ListingForm(FlaskForm):
    """Form for creating or editing a new Trip listing and associated SkillSwap."""
    destination = StringField('Destination', validators=[DataRequired()])
    # Use StringField to receive the date string from the HTML input type="date"
    start_date = StringField('Start Date', validators=[DataRequired()]) 
    end_date = StringField('End Date', validators=[DataRequired()])
    offered_skill = StringField('Skill Offered', validators=[DataRequired()])
    desired_skill = StringField('Skill Wanted', validators=[DataRequired()])
    submit = SubmitField('Post Listing')


class InteractionForm(FlaskForm):
    """Simple form for a user to initiate contact about a listing."""
    message = StringField('Your Message', validators=[DataRequired()])
    submit = SubmitField('Send Request')


# --- APPLICATION ROUTES ---

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route("/")
def home():
    """Renders the home page."""
    return render_template("index.html")

# --- AUTHENTICATION ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user)
        flash('Login successful!', 'success')
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard'))
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# --- PERSONAL CABINET (DASHBOARD) ROUTE ---

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Personal Cabinet: Displays the user's trips, skill swaps, 
    and received/sent interactions.
    
    NOTE: Removed fetching user_swaps separately; they are now accessed via user_trips relationship.
    """
    user_trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.created_at.desc()).all()
    
    # Received Interactions (requests made on the user's listings)
    received_interactions = Interaction.query.filter_by(recipient_id=current_user.id).order_by(Interaction.created_at.desc()).all()
    
    # Sent Interactions (requests the user has made on others' listings)
    sent_interactions = Interaction.query.filter_by(sender_id=current_user.id).order_by(Interaction.created_at.desc()).all()

    return render_template(
        "dashboard.html",
        trips=user_trips,
        received_interactions=received_interactions,
        sent_interactions=sent_interactions
    )

# --- INTERACTION/BOOKING ROUTES ---

@app.route("/interact/<int:trip_id>", methods=["GET", "POST"])
@login_required
def interact_with_listing(trip_id):
    """Handles a user sending an interaction/booking request for a trip."""
    trip = db.session.get(Trip, trip_id)
    
    if not trip:
        return render_template('404.html'), 404
    
    # Prevent users from interacting with their own listing
    if trip.user_id == current_user.id:
        flash("You cannot send a request for your own listing!", "warning")
        return redirect(url_for('trips'))

    form = InteractionForm()
    if form.validate_on_submit():
        try:
            new_interaction = Interaction(
                trip_id=trip.id,
                sender_id=current_user.id,
                recipient_id=trip.user_id,
                message=form.message.data,
                status="Pending"
            )
            db.session.add(new_interaction)
            db.session.commit()
            flash("Your request has been sent! Check your Dashboard for updates.", "success")
            return redirect(url_for('trips'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error sending request: {e}", "danger")
            return redirect(url_for('trips'))

    return render_template("interact.html", trip=trip, form=form)


@app.route("/interaction/update/<int:interaction_id>/<new_status>")
@login_required
def update_interaction_status(interaction_id, new_status):
    """Allows the recipient of a request to update its status (Accept/Reject)."""
    interaction = db.session.get(Interaction, interaction_id)
    
    if not interaction:
        return render_template('404.html'), 404

    # Security check: Only the recipient can update the status
    if interaction.recipient_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard'))

    # Validate status
    if new_status in ["Accepted", "Rejected"]:
        try:
            interaction.status = new_status
            db.session.commit()
            flash(f"Request status updated to {new_status}!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating status: {e}", "danger")
    else:
        flash("Invalid status update.", "danger")

    return redirect(url_for('dashboard'))

# --- CRUD ROUTES: UPDATE (EDIT) ---

@app.route("/listing/edit/<int:trip_id>", methods=["GET", "POST"])
@login_required
def edit_listing(trip_id):
    """Handles the editing of an existing Trip listing and its associated SkillSwap."""
    trip = db.session.get(Trip, trip_id)
    
    if not trip:
        return render_template('404.html'), 404

    # Security check: Only the owner can edit the listing
    if trip.user_id != current_user.id:
        flash("You are not authorized to edit this listing.", "danger")
        return redirect(url_for('dashboard'))

    # Access SkillSwap directly using the new one-to-one relationship
    swap = trip.skillswap
    
    # Pre-populate the form fields
    form = ListingForm(obj=trip)
    
    # Pre-populate skill fields manually if a swap is found for GET requests
    if request.method == "GET" and swap:
        # Determine how to pre-populate based on listing type 
        if trip.is_accommodation_offer:
            # Host (Offer): Form input 1 (offered_skill) is Host's want (swap.skill_wanted)
            # Form input 2 (desired_skill) is Host's offer (swap.skill_offered)
            form.offered_skill.data = swap.skill_wanted
            form.desired_skill.data = swap.skill_offered
        else:
            # Traveler (Seek): Form input 1 (offered_skill) is user's offer (swap.skill_offered)
            # Form input 2 (desired_skill) is user's want (swap.skill_wanted)
            form.offered_skill.data = swap.skill_offered
            form.desired_skill.data = swap.skill_wanted


    if request.method == "POST":
        
        # Manually fetch data from the request object for non-WTF fields
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        listing_type = request.form.get("listing_type") # 'seek' or 'offer'

        if form.validate_on_submit() and listing_type:
            try:
                # 1. Update Trip details
                trip.destination = form.destination.data
                
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                if end_date <= start_date:
                    flash("End date must be after the start date.", "danger")
                    # Re-render with existing form errors
                    return render_template("edit_listing.html", form=form, trip=trip, is_offer=trip.is_accommodation_offer)
                
                trip.start_date = start_date
                trip.end_date = end_date
                
                is_offer = True if listing_type == 'offer' else False
                trip.is_accommodation_offer = is_offer
                
                # 2. Update SkillSwap details
                if swap: 
                    # Apply the same logic as create_listing to determine which skill is offered/wanted
                    if listing_type == 'seek':
                        skill_offer = form.offered_skill.data
                        skill_want = form.desired_skill.data
                    else: # listing_type == 'offer'
                        skill_offer = form.desired_skill.data # Host's offer
                        skill_want = form.offered_skill.data  # Host's want

                    swap.skill_offered = skill_offer
                    swap.skill_wanted = skill_want
                
                db.session.commit()
                flash("Listing updated successfully!", "success")
                return redirect(url_for("dashboard"))

            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
                
    
    # GET request or POST failure
    # Ensure date fields are formatted as YYYY-MM-DD string for HTML input
    form.start_date.data = trip.start_date.isoformat()
    form.end_date.data = trip.end_date.isoformat()
    
    return render_template("edit_listing.html", form=form, trip=trip, is_offer=trip.is_accommodation_offer)

# --- CRUD ROUTES: DELETE ---

@app.route("/listing/delete/<int:trip_id>", methods=["POST"])
@login_required
def delete_listing(trip_id):
    """
    Handles the deletion of a Trip listing. 
    Associated SkillSwap and Interactions are automatically deleted due to cascade rules.
    """
    trip = db.session.get(Trip, trip_id)
    
    if not trip:
        flash("Listing not found.", "danger")
        return redirect(url_for('dashboard'))

    # Security check: Only the owner can delete the listing
    if trip.user_id != current_user.id:
        flash("You are not authorized to delete this listing.", "danger")
        return redirect(url_for('dashboard'))

    try:
        db.session.delete(trip)
        db.session.commit()
        
        # SkillSwap and Interactions are deleted automatically via relationship cascades
        flash("Listing and associated data successfully deleted.", "success")
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting listing: {e}", "danger")
        return redirect(url_for('dashboard'))


# --- MARKETPLACE & LISTING ROUTES ---

@app.route("/trips")
def trips():
    """
    The marketplace route. Fetches and displays both trip requests and 
    accommodation offers (SkillShares).
    
    NOTE: Templates must now access the SkillSwap via 'trip.skillswap'.
    """
    
    # 1. Fetch all trip requests (is_accommodation_offer = False)
    trip_requests = Trip.query.filter_by(is_accommodation_offer=False).all()
    
    # 2. Fetch all accommodation offers (is_accommodation_offer = True)
    accommodation_offers = Trip.query.filter_by(is_accommodation_offer=True).all()
    
    return render_template(
        "marketplace.html", 
        requests=trip_requests,
        accommodation_offers=accommodation_offers
    )

@app.route("/list", methods=["GET", "POST"])
@login_required # Ensure user is logged in to post a listing
def create_listing():
    """Handles the creation of a new Trip listing and a corresponding SkillSwap."""
    
    # INSTANTIATE THE FORM FOR BOTH GET AND POST
    form = ListingForm() 

    if request.method == "POST":
        
        # 1. Validate the Flask-WTF fields first. 
        if form.validate_on_submit():
            
            # 2. Get data from request.form.get() for custom fields (listing_type) 
            destination = request.form.get("destination")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            listing_type = request.form.get("listing_type") # 'seek' or 'offer'
            offered_skill = request.form.get("offered_skill")
            desired_skill = request.form.get("desired_skill")

            user_id = current_user.id 

            # Check for custom fields not covered by form.validate_on_submit()
            if not listing_type:
                flash("Please select a listing type.", "danger")
                return render_template("list.html", form=form)

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                # Input validation: End date must be after start date
                if end_date <= start_date:
                    flash("End date must be after the start date.", "danger")
                    return render_template("list.html", form=form)

                is_offer = True if listing_type == 'offer' else False
                
                # 3. Create the Trip/Accommodation Listing
                new_trip = Trip(
                    destination=destination,
                    start_date=start_date,
                    end_date=end_date,
                    is_accommodation_offer=is_offer,
                    user_id=user_id
                )
                db.session.add(new_trip)
                
                # Commit or flush the new_trip to get its ID before creating the SkillSwap
                db.session.flush() 
                
                # 4. Create the corresponding SkillSwap
                
                if listing_type == 'seek':
                    # Traveler offers X, wants Y (accommodation)
                    skill_offer = offered_skill
                    skill_want = desired_skill
                else: # listing_type == 'offer'
                    # Host offers X (guide/cooking), wants Y (skill)
                    skill_offer = desired_skill # Host's offer (e.g., guide)
                    skill_want = offered_skill  # Host's want (e.g., web design)

                new_swap = SkillSwap(
                    skill_offered=skill_offer,
                    skill_wanted=skill_want,
                    user_id=user_id,
                    trip_id=new_trip.id # Link the swap to the newly created trip
                )
                db.session.add(new_swap)
                
                db.session.commit()
                flash("Listing posted successfully to the Marketplace!", "success")
                return redirect(url_for("trips"))

            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
            
        # If POST failed validation or hit an exception, re-render the template with the form (which contains errors)
        return render_template("list.html", form=form)


    # GET request: render the template with the empty form
    return render_template("list.html", form=form)

# --- RUNNING THE APP ---
@app.cli.command('init-db')
def init_db_command():
    """Initializes a new database or updates the schema."""
    with app.app_context():
        db.create_all() 
        print("Initialized the database with all tables.")

if __name__ == "__main__":
    app.run(debug=True)
