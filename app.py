from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import exc

# --- AUTHENTICATION IMPORTS ---
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

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
# REMOVED: db.init_app(app) <--- This was the duplicate that caused the error!


# --- USER LOADER FOR FLASK-LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    """Callback function used by Flask-Login to reload the user object from the session."""
    return User.query.get(int(user_id))

# --- DATABASE MODELS (Moved to top for clarity and access by forms) ---
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # New: Password hash field
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    trips = db.relationship("Trip", backref="user", cascade="all, delete-orphan")
    skillswaps = db.relationship("SkillSwap", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the stored hash against the given password."""
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

    def __repr__(self):
        return f"<Trip {self.destination}>"


class SkillSwap(db.Model):
    __tablename__ = "skillswap"
    id = db.Column(db.Integer, primary_key=True)
    skill_offered = db.Column(db.String(120), nullable=False)
    skill_wanted = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<SkillSwap {self.skill_offered} for {self.skill_wanted}>"


# --- AUTHENTICATION FORMS (Using Flask-WTF) ---

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
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
        
        # Redirect user to the page they tried to access before logging in
        next_page = request.args.get('next')
        return redirect(next_page or url_for('home'))
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# --- USER MANAGEMENT (CRUD, mostly for testing now) ---

@app.route("/users", methods=["GET", "POST"])
def users():
    """Displays all users and allows for new user creation."""
    
    # Handle user creation (using simple POST, will be replaced by registration form)
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")

        # In a real app, we'd hash the password here. For this demo, we'll use a placeholder.
        if username and email:
            try:
                new_user = User(username=username, email=email)
                new_user.set_password("password123") # Set a default password
                db.session.add(new_user)
                db.session.commit()
                flash("User added successfully!", "success")
            except exc.IntegrityError:
                db.session.rollback()
                flash("Error: Username or Email already exists.", "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
        else:
            flash("All fields are required!", "danger")
            
        return redirect(url_for("users"))

    all_users = User.query.order_by(User.id).all()
    return render_template("users.html", users=all_users)


# --- MARKETPLACE & LISTING ROUTES ---

@app.route("/trips")
def trips():
    """
    The marketplace route. Fetches and displays both trip requests and 
    accommodation offers (SkillShares).
    """
    
    # 1. Fetch all trip requests (is_accommodation_offer = False)
    trip_requests = Trip.query.filter_by(is_accommodation_offer=False).all()
    
    # 2. Fetch all accommodation offers (is_accommodation_offer = True)
    accommodation_offers = Trip.query.filter_by(is_accommodation_offer=True).all()
    
    # 3. Get all skill swaps and map them by user_id for quick lookup
    # This is not scalable, but works for the current schema structure.
    all_swaps_list = SkillSwap.query.all()
    all_swaps = {swap.user_id: swap for swap in all_swaps_list}
    
    return render_template(
        "marketplace.html", 
        requests=trip_requests,
        accommodation_offers=accommodation_offers,
        all_swaps=all_swaps
    )

@app.route("/list", methods=["GET", "POST"])
@login_required # Ensure user is logged in to post a listing
def create_listing():
    """Handles the creation of a new Trip listing and a corresponding SkillSwap."""
    
    if request.method == "POST":
        # Get data from the fixed list.html form
        destination = request.form.get("destination")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        listing_type = request.form.get("listing_type") # 'seek' or 'offer'
        offered_skill = request.form.get("offered_skill")
        desired_skill = request.form.get("desired_skill")

        # user_id is now automatically set to the logged-in user
        user_id = current_user.id 

        if not all([destination, start_date_str, end_date_str, listing_type, offered_skill, desired_skill, user_id]):
            flash("All form fields are required!", "danger")
            return redirect(url_for("create_listing"))
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            is_offer = True if listing_type == 'offer' else False
            
            # 1. Create the Trip/Accommodation Listing
            new_trip = Trip(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                is_accommodation_offer=is_offer,
                user_id=user_id
            )
            db.session.add(new_trip)
            
            # 2. Create the corresponding SkillSwap
            
            if listing_type == 'seek':
                # Traveler offers X, wants Y (accommodation)
                skill_offer = offered_skill
                skill_want = desired_skill
            else: # listing_type == 'offer'
                # Host offers X (guide/cooking), wants Y (skill)
                # The form labels are reversed for the Host perspective, so we swap them back here.
                # Skill offered in form (skill_input_2) is the skill_offered by the Host
                # Skill wanted in form (skill_input_1) is the skill_wanted by the Host
                skill_offer = desired_skill # Host's offer (e.g., guide)
                skill_want = offered_skill  # Host's want (e.g., web design)

            new_swap = SkillSwap(
                skill_offered=skill_offer,
                skill_wanted=skill_want,
                user_id=user_id
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
            
        return redirect(url_for("create_listing"))

    # GET request
    # NOTE: Since user_id is now taken from current_user, we don't need to pass all users to the template.
    return render_template("list.html", users=[current_user] if current_user.is_authenticated else [])

# --- RUNNING THE APP ---
@app.cli.command('init-db')
def init_db_command():
    """Initializes a new database or updates the schema."""
    with app.app_context():
        # Ensure the new password field is created
        db.create_all() 
        print("Initialized the database with all tables.")

if __name__ == "__main__":
    with app.app_context():
        # This will create the database file and tables (including the password_hash field)
        # if globeswap_new.db doesn't exist.
        db.create_all() 
    app.run(debug=True)
