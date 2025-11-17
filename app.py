from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session,send_file,abort
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from threading import Thread
import jwt
from werkzeug.utils import secure_filename
import os
from flask_mail import Mail, Message
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from waitress import serve
from datetime import datetime, timezone
import pytz
from datetime import timedelta
from flask import session  # Make sure this is imported
from datetime import timedelta
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json

app = Flask(__name__)
app.config.update(
    SECRET_KEY='your-secret-key-here',
    
    # PostgreSQL Database Configuration
    SQLALCHEMY_DATABASE_URI='sqlite:///edutrade.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,  # Recommended to disable
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_pre_ping': True,  # Helps with connection drops
        'pool_recycle': 300,    # Recycle connections every 5 minutes
    },
    
    # File Upload Configuration
    UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    GOOGLE_CLIENT_ID='1001673663662-2mvcl8i7f0sis205ivq3o451s8i4gl13.apps.googleusercontent.com',
    GOOGLE_CLIENT_SECRET='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',
    
    # OAuth Configuration
    
    # Email Configuration
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='stud.studentsmart@gmail.com',
    MAIL_PASSWORD='jygr uhcl odmk flve',
    MAIL_DEFAULT_SENDER=('StudentsMart', 'stud.studentsmart@gmail.com'),
    
    # ADD THESE SESSION CONFIGURATIONS:
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # Sessions last 7 days
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)
# Replace your current Google OAuth configuration with this:

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


def check_mail_configuration():
    required_configs = [
        'MAIL_SERVER',
        'MAIL_PORT',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'MAIL_USE_TLS'
    ]

    missing_configs = [config for config in required_configs
                      if not app.config.get(config)]

    if missing_configs:
        print("WARNING: Missing email configurations:", missing_configs)
        return False
    return True
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf', 'ppt', 'pptx', 'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
IST = pytz.timezone('Asia/Kolkata')

# Register custom Jinja2 filter for parsing JSON
import json as json_module
import re

@app.template_filter('fromjson')
def fromjson_filter(value):
    """Parse JSON string to Python object"""
    if not value:
        return []
    try:
        return json_module.loads(value)
    except (ValueError, TypeError):
        return []

@app.template_filter('create_slug')
def create_slug(name):
    """Create URL-friendly slug from name"""
    if not name:
        return "user"
    # Convert to lowercase and replace spaces with hyphens
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special characters
    slug = re.sub(r'[\s_]+', '-', slug)  # Replace spaces/underscores with hyphens
    slug = re.sub(r'-+', '-', slug)  # Remove consecutive hyphens
    return slug.strip('-')

def parse_date_safe(date_str):
    """
    Safely parse date strings from multiple formats.
    Returns a date object or None if parsing fails.
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()
    if not date_str:
        return None

    # Try multiple date formats
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue

    return None

# Add this model after the existing model
#
# s
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Updated database model - remove old_college_proof field
class CollegeChangeRequest(db.Model):
    __tablename__ = 'college_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    old_college = db.Column(db.String(200), nullable=False)
    new_college = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    new_college_proof = db.Column(db.String(200), nullable=False)  # Only new college proof needed
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Relationships with CASCADE configuration
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('college_change_requests', cascade="all, delete-orphan"))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    year = db.Column(db.Integer)
    roll_number = db.Column(db.String(50), unique=True, nullable=True)
    profile_picture = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)  # Google user ID
    is_google_user = db.Column(db.Boolean, default=False)  #
    
    # Replace verification_token with OTP fields
    otp_code = db.Column(db.String(6), nullable=True)  # 6-digit OTP
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, default=0)  # Track failed attempts
    
    reset_token = db.Column(db.String(255))
    reset_token_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    college = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    admin_role = db.Column(db.String(20), default=None)  # 'super_admin', 'normal_admin', 'intern_admin'
    unread_notifications = db.Column(db.Integer, default=0)
    
    size = db.Column(db.String(10))  # XS, S, M, L, XL, XXL
    gender = db.Column(db.String(20))
    state = db.Column(db.String(100))  # Indian state
    interests = db.Column(db.Text)  # JSON array of interests/skills

    # Relationships remain the same
    listings = db.relationship('Listing', backref=db.backref('seller'), cascade="all, delete-orphan", lazy=True)
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', back_populates='user', lazy=True)
    sent_notifications = db.relationship('Notification', foreign_keys='Notification.sender_id', back_populates='sender', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_otp(self):
        """Generate a 6-digit OTP and set expiry time"""
        import random
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)  # OTP valid for 10 minutes
        self.otp_attempts = 0
        
    def is_otp_valid(self, otp):
        """Check if OTP is valid and not expired"""
        if not self.otp_code or not self.otp_expires_at:
            return False
        if datetime.utcnow() > self.otp_expires_at:
            return False
        return self.otp_code == otp
    
    def clear_otp(self):
        """Clear OTP data after successful verification"""
        self.otp_code = None
        self.otp_expires_at = None
        self.otp_attempts = 0
    def set_google_user(self, google_id, google_info):
        """Set up user as Google OAuth user"""
        self.google_id = google_id
        self.is_google_user = True
        self.is_verified = True  # Auto-verify Google users
        if google_info.get('picture'):
            self.profile_picture = google_info['picture']


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    rent_price = db.Column(db.Float)
    category = db.Column(db.String(50), nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    is_for_rent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    
    # ONLY CHANGE: Added CASCADE DELETE to foreign key
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    
    
    # New fields
    product_type = db.Column(db.String(50))
    branch = db.Column(db.String(50))
    study_year = db.Column(db.String(20))
    working_condition = db.Column(db.String(50))
    warranty_status = db.Column(db.String(50))
    subject = db.Column(db.String(100))
    faculty_name = db.Column(db.String(100))
    is_fake_warning = db.Column(db.Boolean, default=False)
    is_softcopy = db.Column(db.Boolean, default=False)
    file_url = db.Column(db.String(200))


class MessageThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # SET NULL: When user is deleted, keep messages but set sender/receiver to NULL
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="SET NULL"), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="SET NULL"), nullable=True)

    # CASCADE DELETE: When listing is deleted, delete all related messages
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete="CASCADE"), nullable=True)

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)

    # Relationships - EXACTLY as your original
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    listing = db.relationship('Listing', backref='messages')

    # Self-referencing for replies
    parent_message_id = db.Column(db.Integer, db.ForeignKey('message_thread.id', ondelete="CASCADE"), nullable=True)
    replies = db.relationship('MessageThread', backref=db.backref('parent_message', remote_side=[id]))


class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    id = db.Column(db.Integer, primary_key=True)
    
    # CASCADE DELETE: When user is deleted, delete their wishlist items
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    
    # CASCADE DELETE: When listing is deleted, remove from wishlists  
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete="CASCADE"), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - EXACTLY as your original
    user = db.relationship('User', backref='wishlist_items')
    listing = db.relationship('Listing', backref='wishlist_entries')


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # CASCADE DELETE: When user is deleted, delete their reports
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    
    # CASCADE DELETE: When listing is deleted, delete reports about it
    reported_listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete="CASCADE"), nullable=True)
    
    # CASCADE DELETE: When message is deleted, delete reports about it
    message_thread_id = db.Column(db.Integer, db.ForeignKey('message_thread.id', ondelete="CASCADE"), nullable=True)
    
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - EXACTLY as your original
    reporter = db.relationship('User', backref='reports_made')
    reported_listing = db.relationship('Listing', backref='reports')
    message_thread = db.relationship('MessageThread', backref='reports')


class SoldItem(db.Model):
    __tablename__ = 'sold_items'
    id = db.Column(db.Integer, primary_key=True)
    
    # CASCADE DELETE: When listing is deleted, delete sold record
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete="CASCADE"), nullable=True)
    
    # CASCADE DELETE: When seller is deleted, delete their sold items
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    
    buyer_name = db.Column(db.String(100), nullable=False)
    buyer_email = db.Column(db.String(255), nullable=False)
    confirmation_token = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')
    sold_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    
    # Relationships - EXACTLY as your original
    listing = db.relationship('Listing', backref='sold_record')
    seller = db.relationship('User', backref='sold_items')


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)

    # CASCADE DELETE: When user is deleted, delete their notifications
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)

    # Sender of the notification (for message notifications)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=True)

    type = db.Column(db.String(50), default='general')
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)

    # CASCADE DELETE: When listing is deleted, delete related notifications
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete="CASCADE"), nullable=True)

    buyer_email = db.Column(db.String(255))
    buyer_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], back_populates='notifications')
    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_notifications')
    listing = db.relationship('Listing', backref='notifications')


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    profile_photo = db.Column(db.String(200))
    resume_url = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(300))
    github_url = db.Column(db.String(300))
    portfolio_url = db.Column(db.String(300))
    leetcode_url = db.Column(db.String(300))
    state = db.Column(db.String(100))
    interests = db.Column(db.Text)  # JSON array of interests
    onboarding_complete = db.Column(db.Boolean, default=False)
    approved_by_admin = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('student_profile', uselist=False, cascade="all, delete-orphan"))
    education = db.relationship('Education', backref='student_profile', cascade="all, delete-orphan", lazy=True)
    work_experience = db.relationship('WorkExperience', backref='student_profile', cascade="all, delete-orphan", lazy=True)
    skills = db.relationship('Skill', backref='student_profile', cascade="all, delete-orphan", lazy=True)
    certifications = db.relationship('Certification', backref='student_profile', cascade="all, delete-orphan", lazy=True)
    applications = db.relationship('Application', backref='student_profile', cascade="all, delete-orphan", lazy=True)


class Education(db.Model):
    __tablename__ = 'education'
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete="CASCADE"), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    field_of_study = db.Column(db.String(100))
    grade = db.Column(db.String(20))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)


class WorkExperience(db.Model):
    __tablename__ = 'work_experience'
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete="CASCADE"), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)


class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    proficiency_level = db.Column(db.String(20), default='beginner')


class Certification(db.Model):
    __tablename__ = 'certifications'
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    issuing_organization = db.Column(db.String(200))
    issue_date = db.Column(db.Date)
    credential_url = db.Column(db.String(300))


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    company_name = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(300))
    description = db.Column(db.Text)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    logo_url = db.Column(db.String(200))
    mobile = db.Column(db.String(20))
    contact_person_name = db.Column(db.String(100))
    contact_person_position = db.Column(db.String(100))
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    is_google_user = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    internships = db.relationship('Internship', backref='company', cascade="all, delete-orphan", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Internship(db.Model):
    __tablename__ = 'internships'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    salary_min = db.Column(db.Float)
    salary_max = db.Column(db.Float)
    location = db.Column(db.String(100))
    posted_by_company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete="CASCADE"), nullable=True)
    admin_managed = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    applications = db.relationship('Application', backref='internship', cascade="all, delete-orphan", lazy=True)


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete="CASCADE"), nullable=False)
    internship_id = db.Column(db.Integer, db.ForeignKey('internships.id', ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="SET NULL"), nullable=True)
    action = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref='audit_logs')


# Admin Role Decorators
from functools import wraps

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin or current_user.admin_role != 'super_admin':
            flash('You need super admin privileges to access this page.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for routes that require any admin role (super_admin or normal_admin)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            abort(403)
        if current_user.admin_role == 'intern_admin':
            flash('Insufficient permissions.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def any_admin_required(f):
    """Decorator for routes accessible by any admin including intern_admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

ALLOWED_DOMAINS = ['ac.in', 'edu', 'org', 'in', 'org.in', 'ac.edu', 'ac.co.in']
def send_welcome_email(email, full_name, college):
    """Send a welcome email to new Google OAuth users"""
    try:
        if not check_mail_configuration():
            print("Email configuration is incomplete")
            return False

        msg = Message(
            'Welcome to StudentsMart!',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2563eb; margin-bottom: 10px;">StudentsMart</h1>
                <h2 style="color: #1f2937; margin-top: 0;">Welcome Aboard!</h2>
            </div>
            
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 25px; margin: 20px 0;">
                <p style="margin-top: 0; color: #374151;">Hi {full_name},</p>
                <p style="color: #374151;">Welcome to StudentsMart! Your account has been successfully created with Google authentication.</p>
                
                <div style="background: white; border-radius: 6px; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #374151;"><strong>College:</strong> {college}</p>
                    <p style="margin: 10px 0 0 0; color: #374151;"><strong>Login Method:</strong> Google Account</p>
                </div>
                
                <p style="color: #374151;">You can now buy and sell study materials, connect with other students, and make the most of your academic journey.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('index', _external=True)}" 
                       style="display: inline-block; background: #2563eb; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                        Start Exploring
                    </a>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px; margin-bottom: 5px;">
                    If you didn't create this account, please contact us immediately.
                </p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 5px;">
                    This is an automated email, please do not reply.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #9ca3af; font-size: 12px;">
                    Best regards,<br>
                    Team StudentsMart
                </p>
            </div>
        </div>
        '''
        
        try:
            mail.send(msg)
            print(f"Welcome email sent successfully to {email}")
            return True
        except Exception as e:
            print(f"Failed to send welcome email: {str(e)}")
            return False
    except Exception as e:
        print(f"Error in send_welcome_email: {str(e)}")
        return False
def send_buyer_confirmation_email(buyer_email, buyer_name, listing, token, seller_name):
    try:
        confirm_url = url_for('confirm_purchase', token=token, action='confirm', _external=True)
        deny_url = url_for('confirm_purchase', token=token, action='deny', _external=True)
        
        msg = Message(
            subject=f'Confirm your purchase - {listing.title}',
            recipients=[buyer_email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Purchase Confirmation Required</h2>
                <p>Hello {buyer_name},</p>
                <p>{seller_name} from {listing.seller.college} has marked the following item as sold to you:</p>
                
                <div style="border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px;">
                    <h3>{listing.title}</h3>
                    <p><strong>Price:</strong> ₹{listing.price}</p>
                    <p><strong>Category:</strong> {listing.category}</p>
                </div>
                
                <p>Please confirm whether you have purchased this item:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirm_url}" style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block;">
                        Yes, I bought this
                    </a>
                    <a href="{deny_url}" style="background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block;">
                        No, I didn't buy this
                    </a>
                </div>
                
                <p><em>This is an automated email from StudentsMart. Please do not reply.</em></p>
            </div>
            """
        )
        mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")

def send_admin_sale_notification(sold_item, listing):
    try:
        admin_email = "contactstudentsmart@gmail.com"
        msg = Message(
            subject=f'Sale Confirmed - {listing.title if listing else "Listing"}',
            recipients=[admin_email],
            html=f"""
            <h3>Sale Confirmation Report</h3>
            <p><strong>Listing:</strong> {listing.title if listing else 'N/A'}</p>
            <p><strong>Seller:</strong> {sold_item.seller.full_name} ({sold_item.seller.college})</p>
            <p><strong>Buyer:</strong> {sold_item.buyer_name} ({sold_item.buyer_email})</p>
            <p><strong>Sale Date:</strong> {sold_item.confirmed_at}</p>
            <p><strong>Price:</strong> ₹{listing.price if listing else 'N/A'}</p>
            """
        )
        mail.send(msg)
    except Exception as e:
        print(f"Admin notification failed: {e}")

def send_verification_otp(email, full_name, otp_code):
    try:
        if not check_mail_configuration():
            print("Email configuration is incomplete")
            return False

        msg = Message('Your StudentsMart Verification Code',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2563eb; margin-bottom: 10px;">StudentsMart</h1>
                <h2 style="color: #1f2937; margin-top: 0;">Email Verification</h2>
            </div>
            
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 25px; margin: 20px 0;">
                <p style="margin-top: 0; color: #374151;">Hi {full_name},</p>
                <p style="color: #374151;">Thank you for registering with StudentsMart! To complete your registration, please use the verification code below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="display: inline-block; background: #2563eb; color: white; padding: 15px 30px; border-radius: 8px; font-size: 24px; font-weight: bold; letter-spacing: 3px;">
                        {otp_code}
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 14px; text-align: center;">
                    This code will expire in 10 minutes for security purposes.
                </p>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px; margin-bottom: 5px;">
                    If you didn't create this account, please ignore this email.
                </p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 5px;">
                    This is an automated email, please do not reply.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #9ca3af; font-size: 12px;">
                    Best regards,<br>
                    Team StudentsMart
                </p>
            </div>
        </div>
        '''
        
        try:
            mail.send(msg)
            print(f"OTP email sent successfully to {email}")
            return True
        except Exception as e:
            print(f"Failed to send OTP email: {str(e)}")
            return False
    except Exception as e:
        print(f"Error in send_verification_otp: {str(e)}")
def save_image(image):
    if not image:
        return None
    filename = secure_filename(image.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    image.save(image_path)
    return f"uploads/{unique_filename}"
@app.route('/')
def index():
    return send_file('index.html')
@app.route('/api/listing/<int:listing_id>/interested-buyers', methods=['GET'])
@login_required
def get_interested_buyers(listing_id):
    """Get all users who have messaged about this listing"""
    try:
        listing = Listing.query.filter_by(id=listing_id, seller_id=current_user.id).first()
        if not listing:
            return jsonify({'success': False, 'message': 'Listing not found'}), 404

        # Get all unique users who have sent messages about this listing
        # Find messages where the current user (seller) is the receiver
        messages = MessageThread.query.filter_by(
            listing_id=listing_id,
            receiver_id=current_user.id
        ).all()

        # Get unique senders
        interested_users = {}
        for msg in messages:
            if msg.sender_id and msg.sender_id not in interested_users:
                user = msg.sender
                if user:
                    interested_users[msg.sender_id] = {
                        'id': user.id,
                        'name': user.full_name,
                        'email': user.email,
                        'college': user.college,
                        'last_message_date': msg.created_at.isoformat()
                    }

        # Convert to list and sort by last message date
        buyers_list = list(interested_users.values())
        buyers_list.sort(key=lambda x: x['last_message_date'], reverse=True)

        return jsonify({
            'success': True,
            'buyers': buyers_list,
            'count': len(buyers_list)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/mark_sold/<int:listing_id>', methods=['POST'])
@login_required
def mark_sold(listing_id):
    try:
        listing = Listing.query.filter_by(id=listing_id, seller_id=current_user.id).first()
        if not listing:
            return jsonify({'success': False, 'message': 'Listing not found'})

        # Check if buyer_id is provided (selecting from interested buyers list)
        buyer_id = request.form.get('buyer_id', '').strip()

        if buyer_id:
            # Fetch buyer details from database
            buyer = db.session.get(User, int(buyer_id))
            if not buyer:
                return jsonify({'success': False, 'message': 'Buyer not found'})
            buyer_name = buyer.full_name
            buyer_email = buyer.email
        else:
            # Fallback to manual entry
            buyer_name = request.form.get('buyer_name', '').strip()
            buyer_email = request.form.get('buyer_email', '').strip()

        if not buyer_name or not buyer_email:
            return jsonify({'success': False, 'message': 'Please provide buyer information'})

        # Generate confirmation token
        confirmation_token = secrets.token_urlsafe(32)

        # Create sold item record
        sold_item = SoldItem(
            listing_id=listing_id,
            seller_id=current_user.id,
            buyer_name=buyer_name,
            buyer_email=buyer_email,
            confirmation_token=confirmation_token
        )
        db.session.add(sold_item)

        # Create notification for seller
        notification = Notification(
            user_id=current_user.id,
            type='sale_confirmation',
            title=f'Purchase confirmation required',
            message=f'Please confirm your purchase of "{listing.title}"',
            listing_id=listing_id,
            buyer_email=buyer_email,
            buyer_name=buyer_name
        )
        db.session.add(notification)

        # Get all users who messaged about this listing (interested buyers)
        interested_users = db.session.query(User).join(
            MessageThread,
            db.or_(
                MessageThread.sender_id == User.id,
                MessageThread.receiver_id == User.id
            )
        ).filter(
            MessageThread.listing_id == listing_id,
            User.id != current_user.id  # Don't notify the seller
        ).distinct().all()

        # Create notifications for all interested users
        for user in interested_users:
            sold_notification = Notification(
                user_id=user.id,
                sender_id=current_user.id,
                type='listing_sold',
                title=f'Listing "{listing.title}" has been sold',
                message=f'The listing "{listing.title}" you were interested in has been sold out and removed from the website.',
                listing_id=listing_id,
                action_url=f'/buy.html',
                is_read=False
            )
            db.session.add(sold_notification)
            user.unread_notifications = (user.unread_notifications or 0) + 1

        # Archive all message threads for this listing
        MessageThread.query.filter_by(listing_id=listing_id).update({'is_archived': True})

        db.session.commit()

        # Send confirmation email to buyer
        send_buyer_confirmation_email(buyer_email, buyer_name, listing, confirmation_token, current_user.full_name)

        return jsonify({'success': True, 'message': 'Confirmation email sent to buyer'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.form
        email = data.get('email', '').strip().lower()
        roll_number = data.get('roll_number', '').strip()
        
        # Check if roll number is provided and unique
        if roll_number:
            existing_roll = User.query.filter_by(roll_number=roll_number).first()
            if existing_roll:
                return jsonify({
                    'error': 'This roll number is already registered. Please use a different one or leave it blank.'
                }), 400

        # Validate email format
        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400

        # Split domain parts
        domain = email.split('@')[-1]
        domain_parts = domain.split('.')

        # Check against allowed domains
        ALLOWED_DOMAINS = ['ac.in', 'edu', 'org', 'in','org.in', 'ac.edu','ac.co.in','com']
        valid_domain = any(
            '.'.join(domain_parts[-len(d.split('.')):]) == d
            for d in ALLOWED_DOMAINS
        )

        if not valid_domain:
            return jsonify({
                'error': 'Only institutional emails allowed. Valid domains: ' + ', '.join(ALLOWED_DOMAINS)
            }), 400

        # Check existing user
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Create new user
        user = User(
            email=email,
            full_name=data['full_name'],
            department=data['department'],
            year=int(data['year']),
            college=data['college'],
            is_verified=False,
            roll_number=roll_number if roll_number else None
        )
        user.set_password(data['password'])
        
        # Generate and set OTP
        user.generate_otp()

        db.session.add(user)
        db.session.commit()

        # Send OTP email
        if not send_verification_otp(user.email, user.full_name, user.otp_code):
            db.session.rollback()
            return jsonify({'error': 'Failed to send verification code'}), 500

        return jsonify({
            'message': 'Registration successful! Please check your email for the verification code.',
            'user_id': user.id,
            'requires_otp': True
        })

    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 4. Add OTP verification route
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        otp_code = data.get('otp_code', '').strip()
        
        if not email or not otp_code:
            return jsonify({'error': 'Email and OTP code are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if user.is_verified:
            return jsonify({'error': 'Email is already verified'}), 400
            
        # Check for too many attempts
        if user.otp_attempts >= 3:
            return jsonify({
                'error': 'Too many failed attempts. Please request a new code.',
                'requires_new_otp': True
            }), 429
            
        # Verify OTP
        if not user.is_otp_valid(otp_code):
            user.otp_attempts += 1
            db.session.commit()
            
            remaining_attempts = 3 - user.otp_attempts
            if remaining_attempts <= 0:
                return jsonify({
                    'error': 'Too many failed attempts. Please request a new code.',
                    'requires_new_otp': True
                }), 429
            else:
                return jsonify({
                    'error': f'Invalid or expired code. {remaining_attempts} attempts remaining.'
                }), 400
        
        # OTP is valid - verify the user
        user.is_verified = True
        user.clear_otp()
        db.session.commit()
        
        return jsonify({
            'message': 'Email verified successfully! You can now login.',
            'success': True
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 5. Add resend OTP route
@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if user.is_verified:
            return jsonify({'error': 'Email is already verified'}), 400
        
        # Generate new OTP
        user.generate_otp()
        db.session.commit()
        
        # Send new OTP
        if not send_verification_otp(user.email, user.full_name, user.otp_code):
            return jsonify({'error': 'Failed to send verification code'}), 500
        
        return jsonify({
            'message': 'New verification code sent successfully',
            'success': True
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 6. Update the login route to handle unverified users
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.form
       
        if not all(k in data for k in ['email', 'password']):
            return jsonify({
                'error': 'Missing email or password',
                'error_code': 'MISSING_FIELDS'
            }), 400
            
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            return jsonify({
                'error': 'Invalid email or password',
                'error_code': 'INVALID_CREDENTIALS'
            }), 401
            
        # Check if this is a Google user trying to login with password
        if user.is_google_user and not user.password_hash:
            return jsonify({
                'error': 'This account was created with Google. Please use "Sign in with Google" instead.',
                'error_code': 'USE_GOOGLE_LOGIN',
                'is_google_user': True
            }), 401
            
        # Regular password check
        if not user.check_password(data['password']):
            return jsonify({
                'error': 'Invalid email or password',
                'error_code': 'INVALID_CREDENTIALS'
            }), 401
            
        if not user.is_verified:
            # Generate new OTP for unverified users trying to login
            user.generate_otp()
            db.session.commit()
            
            # Send OTP
            send_verification_otp(user.email, user.full_name, user.otp_code)
            
            return jsonify({
                'error': 'Please verify your email first. We\'ve sent you a new verification code.',
                'error_code': 'EMAIL_NOT_VERIFIED',
                'email': user.email,
                'requires_otp': True
            }), 401
            
        # Login successful
        login_user(user, remember=True)
        session.permanent = True
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'department': user.department,
                'year': user.year,
                'is_admin': user.is_admin,
                'admin_role': user.admin_role,
                'roll_number': user.roll_number,
                'is_google_user': user.is_google_user
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_code': 'SERVER_ERROR'
        }), 500

@app.route('/confirm_purchase/<token>')
def confirm_purchase(token):
    try:
        action = request.args.get('action', 'confirm')
        sold_item = SoldItem.query.filter_by(confirmation_token=token).first()
        
        if not sold_item:
            flash('Invalid or expired confirmation link', 'error')
            return redirect(url_for('index'))
        
        if action == 'confirm':
            # Get listing and save title BEFORE deleting
            listing = sold_item.listing
            if not listing:
                flash('Listing not found', 'error')
                return redirect(url_for('index'))
                
            # Store listing data before deletion
            listing_title = listing.title
            listing_data = {
                'title': listing.title,
                'price': listing.price,
                'description': listing.description
            }
            
            # FIRST: Clean up ALL related records before deleting listing
            listing_id = listing.id
            
            # Delete related notifications
            Notification.query.filter_by(listing_id=listing_id).delete()
            
            # Delete related wishlist entries
            from sqlalchemy import text
            db.session.execute(text("DELETE FROM wishlist WHERE listing_id = :listing_id"), 
                             {"listing_id": listing_id})
            
            # Delete any other related records if they exist
            # Add more cleanup here if you have other tables referencing listing
            
            # Update sold item status
            sold_item.status = 'confirmed'
            sold_item.confirmed_at = datetime.utcnow()
            
            # Now delete the listing (all references are cleaned up)
            db.session.delete(listing)
            
            # Create notification WITHOUT listing_id (since listing is deleted)
            notification = Notification(
                user_id=sold_item.seller_id,
                type='purchase_confirmed',
                title='Purchase Confirmed',
                message=f'Your item "{listing_title}" has been confirmed as sold to {sold_item.buyer_name}',
                listing_id=None,  # Set to None since listing is deleted
                buyer_email=sold_item.buyer_email,
                buyer_name=sold_item.buyer_name,
                status='confirmed'
            )
            db.session.add(notification)
            
            # Commit ALL changes together
            db.session.commit()
            
            return render_template('confirmation_success.html', 
                                 listing=listing_data,
                                 buyer_name=sold_item.buyer_name)
        
        elif action == 'deny':
            sold_item.status = 'denied'
            db.session.commit()
            return render_template('confirmation_denied.html')
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in confirm_purchase: {str(e)}")
        return render_template('confirmation_error.html', 
                             error_message="An error occurred while processing your request.")

    print(f"Token received: {token}")
    print(f"SoldItem found: {sold_item}")
    print(f"Action: {action}")

@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()
    
    # Mark as read
    current_user.unread_notifications = 0
    db.session.commit()
    
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/api/notification_count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, status='pending').count()
    return jsonify({'count': count})
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def get_or_create_student_profile(user_id):
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        user = db.session.get(User, user_id)
        if user:
            profile = StudentProfile(
                user_id=user_id,
                phone='',
                bio='',
                location=user.college if hasattr(user, 'college') else '',
                onboarding_complete=False,
                approved_by_admin=False,
                featured=False
            )
            db.session.add(profile)
            db.session.commit()
    return profile


@app.route('/test-email')
def test_email():
    try:
        msg = Message('Test Email',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[app.config['MAIL_USERNAME']])
        msg.body = 'This is a test email'
        mail.send(msg)
        return jsonify({'message': 'Test email sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Authentication Routes

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists or not for security
            return jsonify({
                'message': 'If an account with that email exists, we\'ve sent password reset instructions.'
            })

        if not user.is_verified:
            return jsonify({
                'error': 'Please verify your email first before resetting your password.',
                'requires_verification': True,
                'email': email
            }), 400

        # Generate secure reset token
        import secrets
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        db.session.commit()

        # Send reset email
        if send_reset_email(user.email, reset_token, user.full_name):
            return jsonify({
                'message': 'Password reset instructions have been sent to your email.'
            })
        else:
            return jsonify({
                'error': 'Failed to send reset email. Please try again later.'
            }), 500

    except Exception as e:
        db.session.rollback()
        print(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/reset-password/<token>')
def reset_password_page(token):
    """Serve the password reset page"""
    try:
        user = User.query.filter_by(reset_token=token).first()
        
        if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
            # Token is invalid or expired
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invalid Reset Link - StudentsMart</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container-fluid vh-100 d-flex align-items-center justify-content-center">
                    <div class="card shadow-sm" style="max-width: 500px;">
                        <div class="card-body text-center p-5">
                            <div class="mb-4">
                                <i class="fas fa-exclamation-triangle text-warning" style="font-size: 3rem;"></i>
                            </div>
                            <h3 class="mb-3">Invalid Reset Link</h3>
                            <p class="text-muted mb-4">
                                This password reset link is invalid or has expired. 
                                Please request a new password reset.
                            </p>
                            <a href="/" class="btn btn-primary">
                                <i class="fas fa-home me-2"></i>Back to StudentsMart
                            </a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
        
        # Token is valid, show reset form
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reset Password - StudentsMart</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        </head>
        <body class="bg-light">
            <div class="container-fluid vh-100 d-flex align-items-center justify-content-center">
                <div class="card shadow-sm" style="max-width: 500px;">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <img src="https://i.ibb.co/1YBpx2KS/logo.png" alt="StudentsMart" style="height: 40px;" class="mb-2">
                            <h3>Reset Your Password</h3>
                            <p class="text-muted">Enter your new password below</p>
                        </div>
                        
                        <form id="resetPasswordForm">
                            <input type="hidden" id="resetToken" value="{token}">
                            
                            <div class="mb-3">
                                <label for="newPassword" class="form-label">New Password</label>
                                <input type="password" class="form-control form-control-lg" id="newPassword" 
                                       name="new_password" required minlength="6"
                                       placeholder="Enter your new password">
                                <div class="form-text">Password must be at least 6 characters long</div>
                            </div>
                            
                            <div class="mb-4">
                                <label for="confirmPassword" class="form-label">Confirm Password</label>
                                <input type="password" class="form-control form-control-lg" id="confirmPassword" 
                                       name="confirm_password" required minlength="6"
                                       placeholder="Confirm your new password">
                            </div>
                            
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary btn-lg">
                                    <i class="fas fa-key me-2"></i>Reset Password
                                </button>
                            </div>
                        </form>
                        
                        <div class="text-center mt-4">
                            <a href="/" class="text-muted text-decoration-none">
                                <i class="fas fa-arrow-left me-1"></i>Back to StudentsMart
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                document.getElementById('resetPasswordForm').addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    const submitBtn = this.querySelector('button[type="submit"]');
                    const originalText = submitBtn.innerHTML;
                    const newPassword = document.getElementById('newPassword').value;
                    const confirmPassword = document.getElementById('confirmPassword').value;
                    const token = document.getElementById('resetToken').value;
                    
                    // Validate passwords match
                    if (newPassword !== confirmPassword) {{
                        Swal.fire({{
                            title: 'Password Mismatch',
                            text: 'Passwords do not match. Please try again.',
                            icon: 'error',
                            confirmButtonColor: '#2563eb'
                        }});
                        return;
                    }}
                    
                    if (newPassword.length < 6) {{
                        Swal.fire({{
                            title: 'Password Too Short',
                            text: 'Password must be at least 6 characters long.',
                            icon: 'error',
                            confirmButtonColor: '#2563eb'
                        }});
                        return;
                    }}
                    
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Resetting Password...';
                    
                    try {{
                        const response = await fetch('/reset-password', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                token: token,
                                new_password: newPassword
                            }})
                        }});
                        
                        const data = await response.json();
                        
                        if (response.ok) {{
                            Swal.fire({{
                                title: 'Password Reset Successful!',
                                text: 'Your password has been reset. You can now login with your new password.',
                                icon: 'success',
                                confirmButtonColor: '#2563eb'
                            }}).then(() => {{
                                window.location.href = '/';
                            }});
                        }} else {{
                            Swal.fire({{
                                title: 'Reset Failed',
                                text: data.error || 'Failed to reset password. Please try again.',
                                icon: 'error',
                                confirmButtonColor: '#2563eb'
                            }});
                        }}
                    }} catch (error) {{
                        console.error('Reset error:', error);
                        Swal.fire({{
                            title: 'Connection Error',
                            text: 'Unable to reset password. Please check your internet connection and try again.',
                            icon: 'error',
                            confirmButtonColor: '#2563eb'
                        }});
                    }} finally {{
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }}
                }});
            </script>
        </body>
        </html>
        '''
        
    except Exception as e:
        print(f"Reset password page error: {str(e)}")
        return "An error occurred. Please try again.", 500

@app.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['token', 'new_password']):
            return jsonify({'error': 'Missing required fields'}), 400

        user = User.query.filter_by(reset_token=data['token']).first()
        
        if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
            return jsonify({'error': 'Invalid or expired reset token'}), 400

        # Validate password length
        if len(data['new_password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        # Reset password
        user.set_password(data['new_password'])
        user.reset_token = None
        user.reset_token_expiry = None
        
        db.session.commit()

        return jsonify({'message': 'Password reset successful'})

    except Exception as e:
        db.session.rollback()
        print(f"Reset password error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    try:
        redirect_uri = url_for('google_callback', _external=True)
        print(f"Google OAuth redirect URI: {redirect_uri}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"Google OAuth initiation error: {str(e)}")
        flash('Failed to initiate Google login. Please try again.', 'error')
        return redirect(url_for('index'))


@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        print("=== Google OAuth Callback Started ===")
        
        # Get the OAuth token
        token = google.authorize_access_token()
        print(f"Token received: {bool(token)}")
        
        # Extract user info from token
        if 'userinfo' in token:
            user_info = token['userinfo']
        else:
            # Try to parse ID token
            user_info = google.parse_id_token(token)
        
        print(f"User info received: {user_info}")
        
        if not user_info:
            print("No user info received from Google")
            flash('Failed to get user information from Google', 'error')
            return redirect(url_for('index'))

        google_id = user_info.get('sub')  # Google's unique user ID
        email = user_info.get('email')
        full_name = user_info.get('name')
        picture = user_info.get('picture')

        if not email or not google_id:
            print("Missing email or Google ID")
            flash('Failed to get required information from Google', 'error')
            return redirect(url_for('index'))

        print(f"Google user: {email} (ID: {google_id})")

        # Check if user exists by Google ID first, then by email
        existing_user = User.query.filter_by(google_id=google_id).first()
        if not existing_user:
            existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            print(f"Existing user found: {existing_user.email}")
            
            # If user exists but doesn't have Google ID, link the accounts
            if not existing_user.google_id:
                existing_user.set_google_user(google_id, user_info)
                print("Linked existing account with Google")
            
            # Update profile picture if they don't have one
            if not existing_user.profile_picture and picture:
                existing_user.profile_picture = picture
            
            # Ensure user is verified
            if not existing_user.is_verified:
                existing_user.is_verified = True
                
            db.session.commit()
            login_user(existing_user, remember=True)
            
            print(f"User {existing_user.email} logged in successfully")
            return redirect(url_for('index') + '?login=success&method=google')
        
        else:
            print("New Google user - redirecting to complete registration")
            # New user - store Google info in session and redirect to complete registration
            session['google_user_data'] = {
                'google_id': google_id,
                'email': email,
                'full_name': full_name,
                'picture': picture
            }
            
            return redirect(url_for('complete_google_registration'))

    except Exception as e:
        print(f"Google OAuth callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Google authentication failed. Please try again.', 'error')
        return redirect(url_for('index'))


@app.route('/auth/google/register')
def complete_google_registration():
    """Show registration completion form for Google users"""
    
    # Get Google user data from session
    google_data = session.get('google_user_data')
    if not google_data:
        flash('Registration session expired. Please try again.', 'error')
        return redirect(url_for('index'))
    
    # Return HTML form for completing registration
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complete Registration - StudentsMart</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        <style>
            body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
            .card {{ border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
            .form-control {{ border-radius: 10px; }}
            .btn {{ border-radius: 10px; }}
            .select2-container .select2-selection--single {{
                height: 46px;
                border-radius: 10px;
                border: 1px solid #ced4da;
                padding: 10px;
            }}
            .select2-container--default .select2-selection--single .select2-selection__rendered {{
                line-height: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="container-fluid d-flex align-items-center justify-content-center min-vh-100 py-4">
            <div class="card" style="max-width: 600px; width: 100%;">
                <div class="card-body p-5">
                    <div class="text-center mb-4">
                        <h2 class="text-primary">Complete Your Registration</h2>
                        <p class="text-muted">Just a few more details to get you started!</p>
                        <div class="d-flex align-items-center justify-content-center mb-3">
                            {f'<img src="{google_data["picture"]}" class="rounded-circle me-3" width="50" height="50">' if google_data.get("picture") else ''}
                            <div>
                                <div class="fw-bold">{google_data["full_name"]}</div>
                                <div class="text-muted small">{google_data["email"]}</div>
                            </div>
                        </div>
                    </div>
                    
                    <form id="completeGoogleRegistration">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label">Department *</label>
                                <input type="text" class="form-control" name="department" 
                                       placeholder="e.g., Computer Science" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Year *</label>
                                <select class="form-select" name="year" required>
                                    <option value="">Select Year</option>
                                    <option value="1">1st Year</option>
                                    <option value="2">2nd Year</option>
                                    <option value="3">3rd Year</option>
                                    <option value="4">4th Year</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label">College *</label>
                                <select class="form-select college-select" name="college" required>
                                    <option value="">Select your college</option>
                                    <!-- Colleges will be loaded dynamically -->
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label">Roll Number (Optional)</label>
                                <input type="text" class="form-control" name="roll_number" 
                                       placeholder="Your college roll number (optional)">
                                <div class="form-text">You can leave this blank if you prefer</div>
                            </div>
                        </div>
                        
                        <div class="d-grid mt-4">
                            <button type="submit" class="btn btn-primary btn-lg">
                                <i class="fab fa-google me-2"></i>Complete Registration
                            </button>
                        </div>
                    </form>
                    
                    <div class="text-center mt-4">
                        <a href="/" class="text-muted text-decoration-none">
                            <i class="fas fa-arrow-left me-1"></i>Back to StudentsMart
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
        <script>
            $(document).ready(function() {{
                console.log("Initializing college dropdown...");
                
                // Initialize Select2 for college dropdown with improved configuration
                $('.college-select').select2({{
                    placeholder: "Search for your college",
                    allowClear: true,
                    width: '100%',
                    minimumInputLength: 2, // Require at least 2 characters to start searching
                    ajax: {{
                        url: '/api/colleges',
                        dataType: 'json',
                        delay: 250,
                        data: function (params) {{
                            console.log("Searching for:", params.term);
                            return {{
                                q: params.term, // search term
                                page: params.page
                            }};
                        }},
                        processResults: function (data, params) {{
                            console.log("Received data:", data);
                            return {{
                                results: data.results,
                                pagination: data.pagination
                            }};
                        }},
                        cache: true
                    }}
                }}).on('select2:open', function () {{
                    // Focus on the search field when dropdown opens
                    setTimeout(function() {{
                        document.querySelector('.select2-search__field').focus();
                    }}, 100);
                }}).on('select2:select', function (e) {{
                    console.log("Selected college:", e.params.data.text);
                }});
                
                // Debug: Check if Select2 is properly initialized
                console.log("Select2 initialized:", $('.college-select').data('select2'));
            }});
            
            document.getElementById('completeGoogleRegistration').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const submitBtn = this.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating Account...';
                
                try {{
                    const formData = new FormData(this);
                    const response = await fetch('/auth/google/complete', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        Swal.fire({{
                            title: 'Welcome to StudentsMart!',
                            text: 'Your account has been created successfully.',
                            icon: 'success',
                            confirmButtonColor: '#2563eb'
                        }}).then(() => {{
                            window.location.href = '/';
                        }});
                    }} else {{
                        Swal.fire({{
                            title: 'Registration Error',
                            text: data.error || 'Failed to complete registration. Please try again.',
                            icon: 'error',
                            confirmButtonColor: '#2563eb'
                        }});
                    }}
                }} catch (error) {{
                    console.error('Registration error:', error);
                    Swal.fire({{
                        title: 'Connection Error',
                        text: 'Unable to complete registration. Please check your internet connection.',
                        icon: 'error',
                        confirmButtonColor: '#2563eb'
                    }});
                }} finally {{
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }}
            }});
        </script>
    </body>
    </html>
    '''


@app.route('/auth/google/complete', methods=['POST'])
def complete_google_registration_submit():
    """Handle the completion of Google OAuth registration"""
    try:
        # Get Google user data from session
        google_data = session.get('google_user_data')
        if not google_data:
            return jsonify({'error': 'Registration session expired'}), 400
        
        data = request.form
        
        # Validate required fields
        required_fields = ['department', 'year', 'college']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        email = google_data['email']
        roll_number = data.get('roll_number', '').strip()
        
        # Check if user already exists (shouldn't happen, but safety check)
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Account already exists'}), 400
        
        # Check roll number uniqueness if provided
        if roll_number and User.query.filter_by(roll_number=roll_number).first():
            return jsonify({'error': 'Roll number already registered'}), 400
        
        # Create new Google user
        user = User(
            email=email,
            full_name=google_data['full_name'],
            department=data['department'],
            year=int(data['year']),
            college=data['college'],
            roll_number=roll_number if roll_number else None,
            profile_picture=google_data.get('picture', ''),
            google_id=google_data['google_id'],
            is_google_user=True,
            is_verified=True,  # Google users are auto-verified
            # No password for Google users
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        send_welcome_email(user.email, user.full_name, user.college)
        
        # Clear session data
        session.pop('google_user_data', None)
        
        # Auto-login the user
        login_user(user, remember=True)
        
        print(f"New Google user created and logged in: {user.email}")
        
        return jsonify({
            'message': 'Registration completed successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'is_google_user': True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Complete Google registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500
@app.route('/api/colleges')
def get_colleges():
    """Return the list of colleges for dropdown in Select2 format"""
    try:
        # Your complete list of 500+ colleges
        colleges = [
            "A U College Of Engg. Visakhapatnam, Visakhapatnam",
"A U College Of Engg For Women, Visakhapatnam",
"AAR Mahaveer Engineering College, Hyderabad",
"Abhinav Hi-Tech College of Engineering and Technology, Moinabad",
"Abr College Of Engg And Technology, Kanigiri",
"Adarsh College Of Engineering, Gollaprolu",
"Adi Shankara Inst Of Technology, Gudur",
"Adikavi Nannaya University College Of Engineering, Rajahmundry",
"Aditya College Of Engineering, Madanapalle",
"Aditya College Of Engineering, Peddapuram",
"Aditya College Of Engineering And Technology, Peddapuram",
"Aditya Engineering College, Peddapuram",
"Aditya Institute Of Technology And Mgmt, Tekkali",
"Adhisankara College Of Engg. And Technology, Gudur",
"Akrg College Of Engg And Technology, Nallajerla",
"Akula Sreeramulu College Of Engineering, Tanuku",
"Amalapuram Inst Of Mgmt Sci Coll Of Engg, Mummidivaram",
"A.M.Reddy Memorial Coll. Of Engineering, Narasaraopet",
"Amrita Sai Inst. Of Science And Technology, Paritala",
"Anantha Lakshmi Inst Of Technology And Sci, Anantapuramu",
"Andhra Engineering College, Atmakur N",
"Andhra Loyola Instt Of Engg And Technology, Vijayawada",
"Anil Neerukonda Institute Of Technology And Sci, Bheemunipatnam",
"Annamacharya Inst Of Tech And Sci, Kadapa",
"Annamacharya Inst Of Technology And Sciences, Rajampet",
"Annamacharya Inst Of Technology And Sciences-2Nd Shift, Rajampet",
"Annamacharya Inst Of Technology And Sciences, Tirupathi",
"Anurag University, Hyderabad",
"Anu College Of Engg Technology-Self Finance, Guntur",
"ASK College Of Technology Management, Anakapalle",
"ASN Womens Engineering College, Tenali",
"Audisankara College Of Engg And Technology, Nellore",
"Audisankara College Of Engg For Women, Gudur",
"Aurora's Technological and Research Institute, Uppal",
"Avanthi Institute Of Engg. And Technology, Narsipatnam",
"Avanthi Inst. Of Engineering And Technology, Bhogapuram",
"AVN College of Engineering, Ibrahmipatnam",
"Baba Inst Of Tech And Sciences, Visakhapatnam",
"Bandari Srinivas Institute of Technology, Chevella",
"Bapatla Engineering College, Bapatla",
"Bapatla Womens Engg College, Bapatla",
"Benaiah Inst Of Tech And Sciences, Rajahmundry",
"Bharath College Of Engg And Technology For Women, Kadapa",
"Bharath Institute of Science and Technology, Ibrahmipatnam",
"Bhaskar Engineering College, Hyderabad",
"Bheema Inst Of Technology And Sci, Adoni",
"Bhimavaram Inst. Of Engg. And Technology, Bhimavaram",
"Bhoj Reddy Engineering College for Women, Saidabad",
"Bit Institute Of Technology, Hindupur",
"BITS-Pilani, Hyderabad, Shameerpet",
"Bonam Venkata Chalamaiah Inst. Of Tech And Sci., Amalapuram",
"Brahmaiah College Of Engineering, Nellore",
"Brindavan Inst Of Technology And Sci, Kurnool",
"BVRIT Narsapur, Narsapur",
"Bvc Engineering College, Rajahmundry",
"Bvsr Engineering College, Chimakurthy",
"B V Chalamaiah Engineering College, Odalarevu",
"CBIT Hyderabad, Hyderabad",
"Chadalawada Ramanamma Engg. College, Tirupathi",
"Chaitanya Bharathi Institute Of Technology, Pallavolu",
"Chaitanya Engineering College, Visakhapatnam",
"Chaitanya Inst. Of Sci. And Technology, Kakinada",
"Chalapathi Inst Of Engg And Technology, Guntur",
"Chalapathi Inst Of Technology, Guntur",
"Chebrolu Engineering College, Guntur",
"Chintalapudi Engineering College, Guntur",
"Chirala Engineering College, Chirala",
"Chundi Ranganayakulu Engineering College, Chilakaluripet",
"CMR College Of Engineering & Technology, Kandlakoya",
"CMR Engineering college, kandlakoya",
"CMR Institute Of Technology, Kandlakoya",
"CMR Technical Campus, Kandlakoya",
"Coastal Inst Of Technology And Management, Vizianagaram",
"College Of Engineering Br Ambedkar Univ Self Finance, Srikakulam",
"CVR College of Engineering, Hyderabad",
"Dadi Instt. Of Engineering And Technology, Anakapalle",
"D.B.S.Inst Of Technology, Kavali",
"Deccan College of Engineering and Technology, Nampally",
"Dhanekula Inst Of Engg Technology, Vijayawada",
"DMSSVH College Of Engineering, Machilipatnam",
"Dnr College Of Engg And Tech, Bhimavaram",
"Dr L Bullayya College Of Engg For Women, Visakhapatnam",
"Dr Paul Rajs Engineering College, Yetapaka",
"Dr.K.V.Subba Reddy Inst. Of Technology, Kurnool",
"Dr.K.V.Subba Reddycoll Of Engg For Women, Kurnool",
"D Venkataramana And Dr.Himasekhar Mic Coll Of Tech, Kanchikacherla",
"DVR College of Engineering and Technology, Kandi",
"Ellenki College of Engineering and Technology, Patancheru",
"Eluru College Of Engg And Technology, Eluru",
"Eswar College Of Engineering, Narasaraopet",
"G. Narayanamma Institute of Technology and Science, Shaikpet",
"Gandhi Institute of Technology and Management, Rudraram",
"Gates Institute Of Technology, Gooty",
"Geethanjali College Of Engineering And Technology, Hyderabad",
"Geethanjali College Of Engineering And Technology, Kurnool",
"Geethanjali Inst Of Science And Technology, Nellore",
"Giet College Of Engineering, Rajahmundry",
"Giet Engineering College, Rajahmundry",
"Global Coll Of Engg And Technology, Chenur",
"GMR Institute Of Technology, Rajam",
"Godavari Institute Of Engg. And Technology, Rajahmundry",
"Gokraju Ranjaraju Institute of Engineering and Technology, Nizampet",
"Gokul Group Of Institutions, Bobbili",
"Gokula Krishna College Of Engineering, Sullurpet",
"Golden Valley Integrated Campus, Madanapalle",
"Gonna Inst Of Info Technology Sciences, Visakhapatnam",
"Gouthami Inst Of Technology Mgmt For Women, Proddatur",
"GPR Engineering. College, Kurnool",
"GRIET Hyderabad, Hyderabad",
"Gudlavalleru Engineering College, Gudlavalleru",
"Guntur Engineering College, Guntur",
"Guru Nanak Institute of Technology, Ibrahmipatnam",
"Guru Nanak Institutions Technical Campus, Ibrahmipatnam",
"GV VR Institute Of Technology, Bhimavaram",
"Gayathri Vidya Parishad Coll. Of Engineering, Visakhapatnam",
"Gayathri Vidya Parishad Coll Of Engg For Women, Visakhapatnam",
"GVP College For Degree And Pg Courses, Visakhapatnam",
"GVR And S College Of Engg. And Technology, Guntur",
"Helapuri Inst Of Tech And Science, Eluru",
"Hindu College Of Engineering And Technology, Guntur",
"Holy mary institute of technology, Bogaram",
"Hyderabad Institute of Technology and Management, Hyderabad",
"IARE Hyderabad, Hyderabad",
"Ideal Institute Of Technology, Kakinada",
"IIITDM Kurnool",
"IIT Hyderabad",
"IIT Tirupati",
"Indian Institute of Technology Hyderabad",
"Institute of Aeronautical Engineering, Dundigal",
"International Institute of Information Technology, Hyderabad",
"International School Of Tech And Sci For Women, Rajahmundry",
"Islamia College of Engineering and Technology, Bandlaguda",
"Jagans College Of Engg And Technology, Nellore",
"Jagruti Institute of Engineering & Technology, Ibrahmipatnam",
"Jawaharlal Nehru Technological University, Hyderabad",
"JB Institute of Engineering and Technology, Moinabad",
"Joginpally B R Engineering College, Moinabad",
"JNTUHCEH Hyderabad, Hyderabad",
"JNTUH College of Engineering, Karimnagar, Karimnagar",
"JNTUH College of Engineering, Sultanpur, Sultanpur",
"Jntua College Of Engg. Anantapuramu, Anantapuramu",
"Jntua College Of Engineering, Kalikiri",
"Jntua College Of Engg Pulivendula, Pulivendula",
"Jntuk College Of Engg. Kakinada, Kakinada",
"Jntuk College Of Engineering Narasaraopet, Narasaraopet",
"Jntuk College Of Engineering Vizianagaram, Vizianagaram",
"St. Johns College Of Engg. And Technology, Yemmiganur",
"Kakatiya Institute of Technology and Science, Warangal",
"Kakatiya University, Warangal",
"Kakinada Institute Of Engg. And Technology, Kakinada",
"Kakinada Inst Of Engg And Technology For Women, Kakinada",
"Kakinada Institute Of Technology And Science, Divili",
"Kakinada Institute Of Technology Sciences, Ramachandrapuram",
"Kallam Haranadha Reddy Inst Of Tech, Guntur",
"Kandula Obul Reddy Memorial Coll. Of Engg., Kadapa",
"Keshav Memorial Institute of Technology, Narayanguda",
"KG Reddy Engineering College, Moinabad",
"KITSW Warangal, Warangal",
"Kkr And Ksr Inst Of Technology And Sci, Guntur",
"K.Lakshumma Memorial College Of Engg For Women, Kadapa",
"KMIT Hyderabad, Hyderabad",
"Kmm Inst Of Technology And Science, Tirupathi",
"Kommuri pratap reddy institute of technology, Ghanpur",
"Krishna Chaitanya Inst Of Technology And Sciences, Markapur",
"Krishnaveni Engg College For Women, Narasaraopet",
"Krishna University College Of Engg And Technology, Machilipatnam",
"Sri Krishnadeveraya Engineering College, Gooty",
"Sri Krishnadevaraya Univ.Coll. Of Eng.- Self Finance, Anantapuramu",
"KSRM College Of Engineering, Kadapa",
"KU College of Engineering and Technology, Warangal",
"Kuppam Engineering College, Kuppam",
"Lakireddy Balireddy College Of Engineering, Mylavaram",
"Lendi Inst Of Engg And Technology, Vizianagaram",
"Lenora College Of Engineering, Rampachodavaram",
"Lingayas Inst Of Mgmt And Technology, Vijayawada",
"Lords Institute of Engineering and Technology, Rajendra Nagar",
"Loyola Institute Of Technology And Mgmt, Sattenapally",
"Madanapalle Institute Of Technology And Sci-1St Shift, Madanapalle",
"Madanapalle Institute Of Technology And Sci-2Nd Shift, Madanapalle",
"Mahatma Gandhi Institute of Technology, Gandipet",
"Mahaveer Institute of Science and Technology, Bandlaguda",
"Maheshwara College of Engineering, Rangareddy",
"Malineni Lakshmaiah Engineering College, Singarayakonda",
"Malineni Lakshmaiah Womens Engg. College, Guntur",
"Malineni Perumallu Ednl Soc Group Of Instns, Guntur",
"Malla Reddy Engineering College, Maisammaguda",
"Malla Reddy institution of technology and science, Maisammaguda",
"Mandava Institute Of Engg And Technology, Jaggaiahpet",
"Matrusri Engineering College, Saidabad",
"Maturi Venkata Subba Rao Engineering College, Nadargul",
"Megha Institute of Engineering and Technology for Women, Ghatkesar",
"Mekapati Raja Mohan Reddy Inst Of Tech And Sci., Udayagiri",
"Methodist College of Engineering and Technology, Abids",
"MGIT Hyderabad, Hyderabad",
"Miracle Ednl Soc Group Of Instns, Bhogapuram",
"Mjr College Of Engg And Technology, Piler",
"MLR Institute of Technology, Hyderabad",
"MNR College of Engineering and Technology, Kandi",
"Mother Teresa Inst Of Engg And Tech, Palamner",
"Muffakam Jha College of Engineering and Technology, Banjara hills",
"MVGR College Of Engineering, Vizianagaram",
"MVSR Engineering College, Hyderabad",
"M.V.R.Coll Of Engineering And Technology, Paritala",
"Nadimpalli Satyanarayana Raju Institute Of Technology, Visakhapatnam",
"Nalanda Institute Of Engg. And Technology, Sattenapally",
"Nalla Malla Reddy Engineering College, Ghatkesar",
"Nalla Malla Reddy Engineering College, Kachivani Singaram",
"Narasaraopet Institute Of Technology, Narasaraopet",
"Narasaraopeta Engineering College, Narasaraopet",
"Narayana Engineering College, Gudur",
"Narayana Engineering College, Nellore",
"Narayanadri Inst Of Sci Technology, Rajampet",
"National Institute of Technology, Warangal",
"Nawab Shah Alam Khan College of Engineering and Technology, New Malakpet",
"Nbkr Institute Of Sci. And Technology, Vidyanagar",
"Newton Institute Of Engineering, Macherla",
"Nimra College Of Engg And Technology, Jupudi",
"NIT Andhra Pradesh",
"Nri Institute Of Technology, Agiripalli",
"Nri Instt Of Technology, Guntur",
"N.V.R.College Of Engg Technology, Tenali",
"Osmania University, Hyderabad",
"Pace Institute Of Technology And Sciences, Ongole",
"Paladugu Parvathi Devi College Of Engg And Tech, Vijayawada",
"PBR Visvodaya Institute Of Technology And Sci., Kavali",
"P Nagaiah Choudary And Vijay Inst Of Engg And Tech, Guntur",
"Potti Sriramulu College Of Engg And Technology, Vijayawada",
"Pragati Engineering College, Peddapuram",
"Pragati Engineering College-2Nd Shift, Peddapuram",
"Prakasam Engineering College, Kandkur",
"Prasad V Potluri Siddhartha Instt Of Technology, Vijayawada",
"Prasiddha College Of Engg Technology, Anathavaram",
"Princeton College of Engineering and Technology, Ankushapur",
"Princeton Institute of engineering and technology, Ghatkesar",
"Priyadarshini College Of Engineering, Sullurpet",
"Priyadarshini Coll Of Engg. And Technology, Nellore",
"Priyadarshini Inst Of Technology, Nellore",
"Priyadarshini Inst Of Technology, Tirupathi",
"Priyadarshini Inst. Of Technology And Sciences, Tenali",
"G.Pullaiah Coll. Of Engg. And Technology, Kurnool",
"P.V.K.K. Institute Of Technology, Anantapuramu",
"Pydah College Of Engineering, Kakinada",
"Qis College Of Engg. And Technology, Ongole",
"Qis College Of Engg. And Technology-2Nd Shift, Ongole",
"Qis Institute Of Technology, Ongole",
"Raghu Engineering College, Bheemunipatnam",
"Raghu Inst. Of Technology, Bheemunipatnam",
"Rajamahendri Inst Of Engg And Technology, Rajahmundry",
"Rajiv Gandhi Memorial College Of Engg. And Tech., Nandyal",
"Rajiv Gandhi University of Knowledge Technologies, Basar",
"Ramachandra College Of Engineering, Eluru",
"Ramireddy Subba Ramireddy Engg College, Nellore",
"Ravindra College Of Engg For Women, Kurnool",
"Rayalaseema University College Of Engg, Kurnool",
"Rise Krishna Sai Gandhi Group Of Institutions, Ongole",
"Rise Krishna Sai Prakasam Group Of Institutions, Ongole",
"R.K.College Of Engineering, Ibrahimpatnam",
"RVR And J C College Of Engineering, Guntur",
"Sai Ganapathi Engineering College, Visakhapatnam",
"Sai Rajeswari Institute Of Technology, Proddatur",
"Sai Tirumala NVR Engineering College, Narasaraopet",
"Samskruti college of Engineering and Technology, Bogaram",
"Sankethika Inst Of Technology Management, Visakhapatnam",
"Sankethika Vidya Parishad Engineering College, Visakhapatnam",
"Sanskrithi School Of Engineering, Puttaparthi",
"Santhiram Engineering College, Nandyal",
"Sarada Institute Of Sci. Technology And Mgmt, Srikakulam",
"Sasi Institute Of Technology And Engineering, Tadepalligudem",
"Satya Inst Of Technology And Mgmt, Vizianagaram",
"School Of Engg. Tech. Spmvv - Self Finance, Tirupathi",
"School of Engineering Sciences and Technology, UoH, Gachibowli",
"SCIENT Institute of Technology, Ibrahmipatnam",
"Seshachala Inst Of Technology, Puttur",
"Shadan College of Engineering & Technology, Peeram Cheruvu",
"Shadan Women's College of Engineering and Technology, Khairatabad",
"Shree Inst Of Technological Education, Renigunta",
"Shree Rama Ednl Soc Grp Of Instns, Tirupati",
"Shri Shirdi Sai Inst Of Sci And Engg, Anantapuramu",
"Shri Vishnu Engg. College For Women, Bhimavaram",
"Siddharth Institute Of Engg. And Technology, Puttur",
"Siddhartha Institute of Technology and Sciences, Ibrahmipatnam",
"Siddartha Ednl Academy Grp Of Instns, Tirupathi",
"Siddhartha Inst Of Sci And Technology, Puttur",
"Simhadri Ednl Soc Grp Of Instns, Sabbavaram",
"Sir C R R College Of Engineering, Eluru",
"Sir C.V Raman Inst Of Technology Sciences, Tadipatri",
"Sir Vishveshwaraiah Inst Of Science And Technology, Madanapalle",
"SNIST Ghatkesar, Ghatkesar",
"Sphoorthy Engineering College, Vanasthallipuram",
"Sree Rama Engineering College, Tirupathi",
"Sree Vahini Institute Of Science And Technology, Tiruvuru",
"Sree Venkateswara College Of Engg, Nellore",
"Sree Vidyanikethan Engineering College, Rangampeta",
"Sreenidhi institute of science and technology, Ghatkesar",
"Sreyas Institute Of Engineering & Technology, Bandlaguda",
"Sri Annamacharya Institute Of Technology And Science, Rajampet",
"Sri Chaitanya -Djr Coll Of Engg And Tech, Vijayawada",
"Sri Chaitanya Djr Institute Of Engineering And Technology, Vijayawada",
"Sri Datta College of Engineering, Ibrahmipatnam",
"Sri Indu College of Engineering and Technology, Ibrahmipatnam",
"SRKR Engineering College, Bhimavaram",
"SRKR Engineering College-2Nd Shift, Bhimavaram",
"SRK Inst. Of Technology, Vijayawada",
"Sri Mittapalli College Of Engineering, Guntur",
"Sri Mittapalli Inst Of Technology For Women, Guntur",
"Sri Raghavendra Inst Of Technology And Sci., Vinjamur",
"Sri Sai Institute Of Technology. And Sci.., Rayachoti",
"Sri Sarathi Institute Of Engg. And Technology, Nuzvid",
"Sri Satyanarayana Engineering College, Ongole",
"Sri Sivani College Of Engineering, Srikakulam",
"Sri Sunflower College Of Engg And Technology, Lankapalli",
"Sri Vasavi Engineering College, Tadepalligudem",
"Sri Vasavi Instt Of Engineering And Technology., Pedana",
"Sri Venkateswara Coll Of Engineering, Srikakulam",
"Sri Venkateswara Coll Of Engineering, Tirupathi",
"Sri Venkateswara College Of Engg. And Technology., Chittoor",
"Sri Venkateswara College Of Engineering, Kadapa",
"Sri Venkateswara Engg College, Tirupathi",
"Sri Venkateswara Inst Of Technology, Anantapuramu",
"Sri Venkateswara Instt. Of Science And Technology., Kadapa",
"Sri Venkatesa Perumal College Of Engg. And Tech, Puttur",
"Sridevi Women's Engineering College, Vattinagulapally",
"Srinivasa Institute Of Technology And Mang Studies, Chittoor",
"Srinivasa Inst Of Engg And Technology, Cheyyeru",
"Srinivasa Inst Of Technology Science, Kadapa",
"Srinivasa Ramanujan Inst Of Technology, Anantapuramu",
"St. Anns College Of Engg. And Technology, Chirala",
"St. Martins Engineering College, Dhulapally",
"Stanley College of Engineering and Technology for Women, Abids",
"Sumathi Reddy Institute of Technology for Women, Ananthsagar",
"SVU College Of Engg. Tirupathi, Tirupathi",
"Svr Engineering College, Nandyal",
"Swarnandhra Coll. Of Engg And Technology, Narsapuram",
"Swarnandhra Coll. Of Engg And Tech-2Nd Shift, Narsapuram",
"Swarnandhra Inst. Of Engg And Technology, Narsapuram",
"Swetha Institute Of Technology And Science, Tirupathi",
"Tadipatri Engg College, Tadipatri",
"Tammannagari Ramakrishna Reddy College of Engineering, Inole",
"Teegala Krishna Reddy Engineering College, Saroornagar",
"Tirumala Engineering College, Narasaraopet",
"TKR College of Engineering and Technology, Saroornagar",
"Universal College Of Engg And Technology, Guntur",
"University College of Engineering, Osmania University, Hyderabad",
"University of Hyderabad",
"Usha Rama College Of Engg And Technology, Telaprolu",
"Vaagdevi College of Engineering, Bollikunta",
"Vaagdevi Engineering College, Bollikunta",
"Vaagdevi Institute Of Technology. And Sci., Proddatur",
"Vardhaman College of Engineering, Kacharam",
"Vasavi College of Engineering, Hyderabad",
"Vasireddy Venkatadri Inst. Of Technology, Guntur",
"VBIT Ghatkesar, Ghatkesar",
"Velaga Nageswara Rao College Of Engineering, Ponnur",
"Vemu Institute Of Technology, Chittoor",
"Vidya Jyothi Institute of Science and Technology, Moinabad",
"Vignana Bharathi Institute of Technology, Ghatkesar",
"Vignana Bharathi Institute of technology, Korremulla",
"Vignan Institute of management and technology For Women, Ghatkesar",
"Vignans Inst Of Engineering For Women, Visakhapatnam",
"Vignan'S Institute Of Information Technology, Visakhapatnam",
"Vignan'S Nirula Inst Of Tech. And Sci For Women, Guntur",
"Vignans Lara Inst. Of Technology And Sci, Vadlamudi",
"Vijaya Inst. Of Technology For Women, Vijayawada",
"Vikas College Of Engineering And Technology, Vijayawada",
"Vikas Group Of Institutions, Vijayawada Rural",
"Visakha Inst Of Engg And Technology, Visakhapatnam",
"Visakha Technical Campus, Visakhapatnam",
"Vishnu Grp Of Instns - Vishnu Inst Of Technology, Bhimavaram",
"Visvodaya Engineering College, Kavali",
"Viswanadha Institute Of Technology And Mgmt, Visakhapatnam",
"Visvesvaraya College of Engineering and Technology, Ibrahmipatnam",
"VJIT Hyderabad, Hyderabad",
"Vkr Vnb And Agk Engineering College, Gudivada",
"VNR VJIET Hyderabad, Hyderabad",
"V R Siddhartha Engineering College, Vijayawada",
"Vrs And Yrn College Of Engg. And Technology, Chirala",
"V.S.Lakshmi Engg College For Women, Vijayawada",
"V.S.M College Of Engineering, Ramachandrapuram",
"Vizag Institute Of Technology, Bheemunipatnam",
"VNR Vignana Jyothi Institute of Engineering and Technology, Hyderabad",
"Wellfare Inst Of Science Tech And Mgmt, Pinagadi",
"West Godavari Instt Of Science And Engineering, Nallajerla",
"Ygvu Ysr Engineering College, Proddatur",
"Yogananda Inst Of Technology And Science, Tirupathi"
        ]
        
        # Sort alphabetically
        colleges.sort()
        
        # Get search query parameter
        search_term = request.args.get('q', '').lower()
        
        # Filter colleges based on search term
        if search_term:
            filtered_colleges = [college for college in colleges if search_term in college.lower()]
        else:
            filtered_colleges = colleges
        
        # Format for Select2
        results = [{"id": college, "text": college} for college in filtered_colleges]
        
        return jsonify({
            "results": results,
            "pagination": {"more": False}  # No pagination needed for now
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/verify-email/<token>')
def verify_email(token):
    try:
        user = db.session.execute(db.select(User).filter_by(verification_token=token)).scalar_one_or_none()
        if not user:
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verify Your StudenTsmart Account</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
                <style>
                    :root {
                        --primary-color: #2563eb;
                        --secondary-color: #3b82f6;
                        --accent-color: #60a5fa;
                        --success-color: #22c55e;
                        --error-color: #ef4444;
                        --text-dark: #1f2937;
                        --text-light: #6b7280;
                        --background-light: #f3f4f6;
                    }
                    
                    body {
                        font-family: 'Inter', sans-serif;
                        background-color: var(--background-light);
                        color: var(--text-dark);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    
                    .error-container {
                        text-align: center;
                        padding: 2rem;
                        background-color: white;
                        border-radius: 1rem;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        width: 90%;
                        max-width: 500px;
                    }
                    
                    h1 {
                        color: var(--error-color);
                        margin-bottom: 1rem;
                    }
                    
                    p {
                        color: var(--text-light);
                        margin-bottom: 1.5rem;
                    }
                    
                    .btn-primary {
                        display: inline-block;
                        background-color: var(--primary-color);
                        color: white;
                        text-decoration: none;
                        border-radius: 0.5rem;
                        padding: 0.75rem 1.5rem;
                        font-weight: 600;
                        transition: background-color 0.2s;
                    }
                    
                    .btn-primary:hover {
                        background-color: var(--secondary-color);
                    }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>Invalid Verification Link</h1>
                    <p>The verification link you clicked is invalid or has expired.</p>
                    <a href="/" class="btn-primary">Get to the website</a>
                </div>
            </body>
            </html>
            """
            return error_html, 400
        
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        # Return HTML success page with custom styling
        success_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verify Your StudenTsmart Account</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --primary-color: #2563eb;
                    --secondary-color: #3b82f6;
                    --accent-color: #60a5fa;
                    --success-color: #22c55e;
                    --error-color: #ef4444;
                    --text-dark: #1f2937;
                    --text-light: #6b7280;
                    --background-light: #f3f4f6;
                }
                
                body {
                    font-family: 'Inter', sans-serif;
                    background-color: var(--background-light);
                    color: var(--text-dark);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                
                .success-container {
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 1rem;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    width: 90%;
                    max-width: 500px;
                }
                
                h1 {
                    color: var(--success-color);
                    margin-bottom: 1rem;
                }
                
                p {
                    color: var(--text-light);
                    margin-bottom: 1.5rem;
                }
                
                .check-icon {
                    font-size: 60px;
                    color: var(--success-color);
                    margin-bottom: 1rem;
                }
                
                .btn-primary {
                    display: inline-block;
                    background-color: var(--primary-color);
                    color: white;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    padding: 0.75rem 1.5rem;
                    font-weight: 600;
                    transition: background-color 0.2s;
                }
                
                .btn-primary:hover {
                    background-color: var(--secondary-color);
                }
            </style>
        </head>
        <body>
            <div class="success-container">
                <div class="check-icon">✓</div>
                <h1>Verify Your StudentsMart Account</h1>
                <p>Your email has been verified successfully! You can now access the StudenTsmart website.</p>
                <a href="/" class="btn-primary">Get to the website</a>
            </div>
        </body>
        </html>
        """
        return success_html
        
    except Exception as e:
        db.session.rollback()
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Error</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary-color: #2563eb;
                    --secondary-color: #3b82f6;
                    --accent-color: #60a5fa;
                    --success-color: #22c55e;
                    --error-color: #ef4444;
                    --text-dark: #1f2937;
                    --text-light: #6b7280;
                    --background-light: #f3f4f6;
                }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    background-color: var(--background-light);
                    color: var(--text-dark);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                
                .error-container {{
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 1rem;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    width: 90%;
                    max-width: 500px;
                }}
                
                h1 {{
                    color: var(--error-color);
                    margin-bottom: 1rem;
                }}
                
                p {{
                    color: var(--text-light);
                    margin-bottom: 1.5rem;
                }}
                
                .btn-primary {{
                    display: inline-block;
                    background-color: var(--primary-color);
                    color: white;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    padding: 0.75rem 1.5rem;
                    font-weight: 600;
                    transition: background-color 0.2s;
                }}
                
                .btn-primary:hover {{
                    background-color: var(--secondary-color);
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>Verification Error</h1>
                <p>An error occurred during verification. Please try again later.</p>
                <a href="/" class="btn-primary">Get to the website</a>
            </div>
        </body>
        </html>
        """
        return error_html, 500
# Listing Routes
@app.route('/create-listing', methods=['POST'])
@login_required
def create_listing():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        image = request.files['image']
        if image.filename == '':
            return jsonify({'error': 'No image selected'}), 400

        # Save the image and get its path
        image_url = save_image(image)
        if not image_url:
            return jsonify({'error': 'Failed to save image'}), 500

        # Check if listing is for rent
        is_for_rent = request.form.get('is_for_rent') == 'true'

        # Set price and rent_price based on listing type
        price = 0
        rent_price = 0

        if is_for_rent:
            rent_price = float(request.form.get('rent_price', 0))
            # Optional: Store rental tenure in description or as a separate field
            rent_tenure = request.form.get('rent_tenure', '0')
        else:
            price = float(request.form.get('price', 0))
        
        is_softcopy = request.form.get('copy_type') == 'soft'
        file = request.files.get('document') if is_softcopy else None

        # Handle file upload
        if is_softcopy and file:
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Only PDF and Word documents allowed'}), 400

            try:
                # Check if we can locate working files to understand the correct path
                working_files_check = []
                test_filenames = [
                    "2881bee4-a0ee-4efe-ae76-4dd654b79429_NLP_Exam_Preparation_Topics.pdf",
                    "603f8fa0-0fa4-4295-a383-81dd385778e2_N_L_RAM_CHARAN_TEJA.pdf"
                ]
                
                for test_file in test_filenames:
                    possible_locations = [
                        os.path.join(app.root_path, 'static', 'uploads', test_file),
                        os.path.join(os.getcwd(), 'static', 'uploads', test_file)
                    ]
                    
                    for location in possible_locations:
                        if os.path.exists(location):
                            working_files_check.append({
                                "file": test_file,
                                "found_at": location,
                                "exists": True
                            })
                            
                print(f"Working files check: {working_files_check}")
                
                # Ensure upload directory exists
                if working_files_check:
                    # Use the location where working files were found
                    uploads_dir = os.path.dirname(working_files_check[0]["found_at"])
                    print(f"Using uploads directory where working files were found: {uploads_dir}")
                else:
                    # Default location
                    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
                    print(f"No working files found, using default uploads directory: {uploads_dir}")
                
                os.makedirs(uploads_dir, exist_ok=True)

                # Generate a unique filename to prevent collisions
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)
                
                # Store only the filename without any path prefix
                file_url = filename
                
                print(f"Softcopy file saved at: {file_path}")
                print(f"Stored file_url as: {file_url}")
                print(f"File exists after save: {os.path.exists(file_path)}")
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        else:
            file_url = None
        # Create listing
        listing = Listing(
            title=request.form['title'],
            description=request.form['description'],
            price=price,
            rent_price=rent_price,
            category=request.form['category'],
            condition=request.form.get('working_condition', 'Not specified'),
            image_url=image_url,
            seller_id=current_user.id,
            product_type=request.form.get('product_type'),
            branch=request.form.get('branch'),
            study_year=request.form.get('study_year'),
            working_condition=request.form.get('working_condition'),
            warranty_status=request.form.get('warranty_status'),
            subject=request.form.get('subject'),
            faculty_name=request.form.get('faculty_name'),
            is_softcopy=is_softcopy,
            file_url=file_url,
            is_fake_warning=bool(request.form.get('is_fake_warning', False)),
            is_for_rent=is_for_rent
        )

        db.session.add(listing)
        db.session.commit()

        return jsonify({
            'message': 'Listing created successfully',
            'listing': {
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price': listing.price,
                'rent_price': listing.rent_price,
                'category': listing.category,
                'condition': listing.condition,
                'image_url': listing.image_url,
                'product_type': listing.product_type,
                'created_at': listing.created_at.isoformat(),
                'is_for_rent': listing.is_for_rent,
                'is_softcopy': listing.is_softcopy,
                'faculty_name': listing.faculty_name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/listings')
def get_listings():
    try:
        # Get all filter parameters
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        sort_by = request.args.get('sort_by', 'created_at')
        college = current_user.college if current_user.is_authenticated else ''
        
        # Category-specific filters
        branch = request.args.get('branch', '')
        study_year = request.args.get('study_year', '')
        copy_type = request.args.get('copy_type', '')
        working_condition = request.args.get('working_condition', '')
        warranty_status = request.args.get('warranty_status', '')
        size = request.args.get('size', '')
        gender = request.args.get('gender', '')
        price_range = request.args.get('price_range', '')
        product_type = request.args.get('product_type', '')

        # Base query
        listings_query = Listing.query.join(User)
        if college:
            listings_query = listings_query.filter(User.college == college)

        # Search filter
        if query:
            listings_query = listings_query.filter(
                db.or_(
                    Listing.title.ilike(f'%{query}%'),
                    Listing.description.ilike(f'%{query}%'),
                    Listing.subject.ilike(f'%{query}%'),
                    Listing.faculty_name.ilike(f'%{query}%')
                )
            )

        # Category filter
        if category:
            listings_query = listings_query.filter(Listing.category == category)

        # Product type filter
        if product_type:
            listings_query = listings_query.filter(Listing.product_type == product_type)

        # Books-specific filters
        if branch:
            listings_query = listings_query.filter(Listing.branch == branch)
        
        if copy_type:
            is_soft = copy_type == 'soft'
            listings_query = listings_query.filter(Listing.is_softcopy == is_soft)

        # Electronics-specific filters
        if working_condition:
            listings_query = listings_query.filter(Listing.working_condition == working_condition)
        
        if warranty_status:
            listings_query = listings_query.filter(Listing.warranty_status == warranty_status)

        # Clothes-specific filters (you'll need to add these fields to your Listing model)
        if size:
            listings_query = listings_query.filter(Listing.size == size)
        
        if gender:
            listings_query = listings_query.filter(Listing.gender == gender)

        # Academic year filter
        if study_year:
            listings_query = listings_query.filter(Listing.study_year == study_year)

        # Price range filter
        if price_range:
            if price_range == 'free':
                listings_query = listings_query.filter(Listing.is_softcopy == True)
            elif '-' in price_range:
                min_price, max_price = price_range.split('-')
                listings_query = listings_query.filter(
                    Listing.price >= int(min_price),
                    Listing.price <= int(max_price)
                )
            elif price_range.endswith('+'):
                min_price = int(price_range[:-1])
                listings_query = listings_query.filter(Listing.price >= min_price)

        # Sorting
        if sort_by == 'price_low':
            listings_query = listings_query.order_by(Listing.price.asc())
        elif sort_by == 'price_high':
            listings_query = listings_query.order_by(Listing.price.desc())
        elif sort_by == 'title':
            listings_query = listings_query.order_by(Listing.title.asc())
        else:
            listings_query = listings_query.order_by(Listing.created_at.desc())

        listings = listings_query.all()

        return jsonify({
            'listings': [{
                'id': l.id,
                'title': l.title,
                'description': l.description,
                'price': l.price,
                'rent_price': l.rent_price,
                'category': l.category,
                'condition': l.condition,
                'image_url': l.image_url,
                'is_for_rent': l.is_for_rent,
                'created_at': l.created_at.isoformat(),
                'seller': {
                    'id': l.seller.id,
                    'name': l.seller.full_name,
                    'college': l.seller.college
                },
                'is_softcopy': l.is_softcopy,
                'file_url': l.file_url,
                'product_type': l.product_type,
                'branch': l.branch,
                'study_year': l.study_year,
                'working_condition': l.working_condition,
                'warranty_status': l.warranty_status,
                'subject': l.subject,
                'faculty_name': l.faculty_name,
                'is_fake_warning': l.is_fake_warning,
                # Add these if you have them in your model
                'size': getattr(l, 'size', None),
                'gender': getattr(l, 'gender', None)
            } for l in listings]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
def send_reset_email(email, token, user_name):
    try:
        if not check_mail_configuration():
            print("Email configuration is incomplete")
            return False

        reset_url = url_for('reset_password_page', token=token, _external=True)
        
        msg = Message(
            'Reset Your StudentsMart Password',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2563eb; margin-bottom: 10px;">StudentsMart</h1>
                <h2 style="color: #1f2937; margin-top: 0;">Password Reset Request</h2>
            </div>
            
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 25px; margin: 20px 0;">
                <p style="margin-top: 0; color: #374151;">Hi {user_name},</p>
                <p style="color: #374151;">We received a request to reset your password for your StudentsMart account.</p>
                <p style="color: #374151;">Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="display: inline-block; background: #2563eb; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                        Reset My Password
                    </a>
                </div>
                
                <p style="color: #6b7280; font-size: 14px;">
                    If you can't click the button, copy and paste this link into your browser:<br>
                    <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
                </p>
                
                <p style="color: #6b7280; font-size: 14px; margin-bottom: 0;">
                    This link will expire in 1 hour for security purposes.
                </p>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px; margin-bottom: 5px;">
                    If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
                </p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 5px;">
                    This is an automated email, please do not reply.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #9ca3af; font-size: 12px;">
                    Best regards,<br>
                    Team StudentsMart
                </p>
            </div>
        </div>
        '''
        
        try:
            mail.send(msg)
            print(f"Password reset email sent successfully to {email}")
            return True
        except Exception as e:
            print(f"Failed to send password reset email: {str(e)}")
            return False
    except Exception as e:
        print(f"Error in send_reset_email: {str(e)}")
        return False
@app.route('/check-session')
def check_session():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'department': current_user.department,
                'year': current_user.year,
                'college': current_user.college,  # Add this too
                'roll_number': current_user.roll_number,  # Add this too
                'profile_picture': current_user.profile_picture,  # ADD THIS LINE
                'is_admin': current_user.is_admin
            }
        })
    return jsonify({'authenticated': False})
@app.route('/api/my-listings')
@login_required
def get_my_listings():
    try:
        listings = Listing.query.filter_by(seller_id=current_user.id).all()
        return jsonify({
            'listings': [{
                'id': l.id,
                'title': l.title,
                'description': l.description,
                'price': l.price,
                'category': l.category,
                'condition': l.condition,
                'image_url': l.image_url,
                'created_at': l.created_at.isoformat(),
                'product_type': l.product_type,
                'branch': l.branch,
                'study_year': l.study_year,
                'working_condition': l.working_condition,
                'warranty_status': l.warranty_status,
                'subject': l.subject,
                'is_fake_warning': l.is_fake_warning,
                'is_softcopy': l.is_softcopy,
                'file_url': l.file_url
            } for l in listings]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/wishlist')
@login_required
def get_wishlist():
    try:
        items = Wishlist.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'items': [{
                'id': item.id,
                'listing': {
                    'id': item.listing.id,
                    'title': item.listing.title,
                    'price': item.listing.price,
                    'image_url': item.listing.image_url,
                    'seller': {
                        'id': item.listing.seller.id,
                        'name': item.listing.seller.full_name
                    }
                },
                'created_at': item.created_at.isoformat()
            } for item in items]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    try:
        listing_id = request.json.get('listing_id')
        if not listing_id:
            return jsonify({'error': 'Listing ID required'}), 400
            
        existing = Wishlist.query.filter_by(
            user_id=current_user.id,
            listing_id=listing_id
        ).first()
        
        if existing:
            return jsonify({'message': 'Item already in wishlist'})
            
        wishlist_item = Wishlist(
            user_id=current_user.id,
            listing_id=listing_id
        )
        
        db.session.add(wishlist_item)
        db.session.commit()
        
        return jsonify({'message': 'Added to wishlist successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/messages')
@login_required
def get_messages():
    try:
        other_user_id = request.args.get('other_user_id')
        listing_id = request.args.get('listing_id')

        query = MessageThread.query

        if other_user_id and listing_id:
            # Get specific conversation
            query = query.filter(
                MessageThread.listing_id == listing_id,
                db.or_(
                    db.and_(MessageThread.sender_id == current_user.id, MessageThread.receiver_id == other_user_id),
                    db.and_(MessageThread.sender_id == other_user_id, MessageThread.receiver_id == current_user.id)
                )
            )
        else:
            # Get all conversations
            query = query.filter(
                db.or_(
                    MessageThread.sender_id == current_user.id,
                    MessageThread.receiver_id == current_user.id
                )
            )

        messages = query.order_by(MessageThread.created_at.asc()).all()

        # Mark received messages as read
        unread_messages = [m for m in messages
                         if m.receiver_id == current_user.id and not m.read]
        for message in unread_messages:
            message.read = True

        if unread_messages:
            db.session.commit()

        return jsonify({
            'messages': [{
                'id': m.id,
                'content': m.content,
                'sender_id': m.sender_id,
                'receiver_id': m.receiver_id,
                'listing_id': m.listing_id,
                'created_at': m.created_at.isoformat(),
                'read': m.read,
                'sender': {
                    'id': m.sender.id,
                    'full_name': m.sender.full_name,
                    'profile_picture': m.sender.profile_picture
                },
                'receiver': {
                    'id': m.receiver.id,
                    'full_name': m.receiver.full_name,
                    'profile_picture': m.receiver.profile_picture
                }
            } for m in messages]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.json

        # Validate required fields
        if not all(k in data for k in ['receiver_id', 'listing_id', 'content']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Create new message
        message = MessageThread(
            sender_id=current_user.id,
            receiver_id=data['receiver_id'],
            listing_id=data['listing_id'],
            content=data['content']
        )

        db.session.add(message)
        db.session.flush()  # Get message.id before commit

        # Get listing details
        listing = Listing.query.get(data['listing_id'])

        # Create notification for receiver
        notification = Notification(
            user_id=data['receiver_id'],
            sender_id=current_user.id,
            type='message',
            title=f"New message from {current_user.full_name}",
            message=data['content'][:50] + ('...' if len(data['content']) > 50 else ''),
            listing_id=data['listing_id'],
            action_url=f"/buy.html?listing={data['listing_id']}&open_chat={current_user.id}",
            is_read=False
        )
        db.session.add(notification)

        # Update receiver's unread notification count
        receiver = User.query.get(data['receiver_id'])
        if receiver:
            receiver.unread_notifications = (receiver.unread_notifications or 0) + 1

        db.session.commit()

        return jsonify({
            'message': 'Message sent successfully',
            'data': {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender_id,
                'receiver_id': message.receiver_id,
                'listing_id': message.listing_id,
                'created_at': message.created_at.isoformat(),
                'read': message.read
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/messages/reply', methods=['POST'])
@login_required
def reply_to_message():
    try:
        data = request.json
        if not all(k in data for k in ['parent_message_id', 'content']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Get the parent message
        parent_message = db.session.get(MessageThread, data['parent_message_id'])
        if not parent_message:
            abort(404)

        # Create the reply
        reply = MessageThread(
            sender_id=current_user.id,
            receiver_id=parent_message.sender_id if parent_message.receiver_id == current_user.id else parent_message.receiver_id,
            listing_id=parent_message.listing_id,
            content=data['content'],
            parent_message_id=parent_message.id
        )

        db.session.add(reply)
        db.session.commit()

        return jsonify({
            'message': 'Reply sent successfully',
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'sender': {
                    'id': reply.sender.id,
                    'name': reply.sender.full_name
                },
                'created_at': reply.created_at.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/messages/check-new')
@login_required
def check_new_messages():
    try:
        since = request.args.get('since')
        since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        new_messages = MessageThread.query.filter(
            MessageThread.receiver_id == current_user.id,
            MessageThread.created_at > since_time,
            MessageThread.read == False
        ).all()
        
        return jsonify({
            'messages': [{
                'id': m.id,
                'content': m.content,
                'created_at': m.created_at.isoformat(),
                'sender': {
                    'id': m.sender.id,
                    'full_name': m.sender.full_name
                },
                'listing': {
                    'id': m.listing.id,
                    'title': m.listing.title
                }
            } for m in new_messages]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/listings/<int:listing_id>', methods=['DELETE'])
@login_required
def delete_listing(listing_id):
    try:
        listing = db.get_or_404(Listing, listing_id)
        
        # Check if the current user owns this listing
        if listing.seller_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Delete the image file if it exists
        if listing.image_url:
            try:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_url.split('/')[-1])
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image: {str(e)}")
        
        # Delete the listing
        db.session.delete(listing)
        db.session.commit()
        
        return jsonify({'message': 'Listing deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/my-listings')
@login_required
def my_listings_page():
    return send_file('index.html')
@app.route('/my-wishlist')
@login_required
def my_wishlist_page():
    return send_file('index.html')
@app.route('/api/wishlist/<int:wishlist_id>', methods=['DELETE'])
@login_required
def remove_from_wishlist(wishlist_id):
    try:
        wishlist_item = db.session.get(Wishlist, wishlist_id)
        if not wishlist_item:
            abort(404)
        
        # Check if the current user owns this wishlist item
        if wishlist_item.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        return jsonify({'message': 'Item removed from wishlist successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# Admin Routes
@app.route('/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        admin = db.session.execute(db.select(User).filter_by(email=email, is_admin=True)).scalar_one_or_none()

        if not admin or not admin.check_password(password):
            return jsonify({'error': 'Invalid admin credentials'}), 401

        login_user(admin)
        return jsonify({
            'message': 'Admin login successful',
            'admin': {
                'id': admin.id,
                'email': admin.email,
                'full_name': admin.full_name,
                'is_admin': True
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Check if this is a fetch/AJAX request (wants JSON) or browser navigation (wants HTML)
    # Browser requests explicitly want text/html as primary accept type
    accept_header = request.headers.get('Accept', '')
    is_browser_request = accept_header.startswith('text/html')
    wants_json = not is_browser_request

    if not current_user.is_admin:
        if wants_json:
            return jsonify({'error': 'Unauthorized'}), 403
        return redirect(url_for('index'))

    try:
        users = User.query.all()
        listings = Listing.query.all()
        reports = Report.query.all()

        stats = {
            'total_users': len(users),
            'total_listings': len(listings),
            'verified_users': len([u for u in users if u.is_verified]),
            'fake_warnings': len([l for l in listings if l.is_fake_warning]),
            'pending_reports': len([r for r in reports if r.status == 'pending']),
            'total_reports': len(reports)
        }

        # If request wants JSON, return JSON
        if wants_json:
            return jsonify({
                'users': [{
                    'id': u.id,
                    'email': u.email,
                    'full_name': u.full_name,
                    'college': u.college,
                    'is_verified': u.is_verified,
                    'created_at': u.created_at.isoformat(),
                    'listings_count': len(u.listings)
                } for u in users],
                'listings': [{
                    'id': l.id,
                    'title': l.title,
                    'price': l.price,
                    'category': l.category,
                    'seller_id': l.seller_id,
                    'seller_name': l.seller.full_name,
                    'created_at': l.created_at.isoformat(),
                    'is_fake_warning': l.is_fake_warning
                } for l in listings],
                'reports': [{
                    'id': r.id,
                    'reporter_name': r.reporter.full_name,
                    'listing_title': r.reported_listing.title if r.reported_listing else 'User Report',
                    'description': r.description,
                    'status': r.status,
                    'created_at': r.created_at.isoformat()
                } for r in reports],
                'stats': stats
            })

        # Otherwise return HTML template
        return render_template('admin/dashboard.html',
                             users=users,
                             listings=listings,
                             reports=reports,
                             stats=stats)

    except Exception as e:
        if wants_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/delete-user/<int:user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        user = db.session.get(User, user_id)
        if not user:
            abort(404)
        
        # First delete all notifications for this user
        Notification.query.filter_by(user_id=user_id).delete()
        
        # Then proceed with deleting other related data
        MessageThread.query.filter(
            db.or_(
                MessageThread.sender_id == user_id,
                MessageThread.receiver_id == user_id
            )
        ).delete(synchronize_session='fetch')
        
        Wishlist.query.filter_by(user_id=user_id).delete()
        Report.query.filter_by(reporter_id=user_id).delete()
        
        user_listings = Listing.query.filter_by(seller_id=user_id).all()
        for listing in user_listings:
            Report.query.filter_by(reported_listing_id=listing.id).delete()
            Wishlist.query.filter_by(listing_id=listing.id).delete()
            MessageThread.query.filter_by(listing_id=listing.id).delete()
            
            if listing.image_url:
                try:
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_url.split('/')[-1])
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting image for listing {listing.id}: {str(e)}")
            
            db.session.delete(listing)
        
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User and their data deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/delete-listing/<int:listing_id>', methods=['DELETE'])
@login_required
def admin_delete_listing(listing_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        listing = db.session.get(Listing, listing_id)
        if not listing:
            abort(404)
        if not listing:
            abort(404)
        
        # Delete reports about this listing
        Report.query.filter_by(reported_listing_id=listing_id).delete()
        
        # Delete wishlist entries for this listing
        Wishlist.query.filter_by(listing_id=listing_id).delete()
        
        # Delete messages about this listing
        MessageThread.query.filter_by(listing_id=listing_id).delete()
        
        # Delete the listing's image file if it exists
        if listing.image_url:
            try:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_url.split('/')[-1])
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image for listing {listing_id}: {str(e)}")
        
        # Delete the listing itself
        db.session.delete(listing)
        db.session.commit()
        
        return jsonify({'message': 'Listing deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting listing {listing_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/toggle-verification/<int:user_id>', methods=['POST'])
@login_required
def admin_toggle_verification(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        user = db.session.get(User, user_id)
        if not user:
            abort(404)
        user.is_verified = not user.is_verified
        db.session.commit()
        
        return jsonify({
            'message': 'User verification status updated',
            'is_verified': user.is_verified
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/toggle-fake-warning/<int:listing_id>', methods=['POST'])
@login_required
def admin_toggle_fake_warning(listing_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        listing = db.session.get(Listing, listing_id)
        if not listing:
            abort(404)
        listing.is_fake_warning = not listing.is_fake_warning
        db.session.commit()
        
        return jsonify({
            'message': 'Fake warning status updated',
            'is_fake_warning': listing.is_fake_warning
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# Add these new routes to app.py

@app.route('/admin/user-details/<int:user_id>')
@login_required
def admin_user_details(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        user = db.session.get(User, user_id)
        if not user:
            abort(404)
        return jsonify({
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'department': user.department,
            'year': user.year,
            'college': user.college,
            'profile_picture': user.profile_picture,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat(),
            'listings_count': len(user.listings)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/user-listings/<int:user_id>')
@login_required
def admin_user_listings(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        listings = Listing.query.filter_by(seller_id=user_id).all()
        return jsonify([{
            'id': l.id,
            'title': l.title,
            'price': l.price,
            'image_url': l.image_url,
            'category': l.category,
            'condition': l.condition,
            'created_at': l.created_at.isoformat()
        } for l in listings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/listing-details/<int:listing_id>')
@login_required
def admin_listing_details(listing_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        listing = db.session.get(Listing, listing_id)
        if not listing:
            abort(404)
        seller = db.session.get(User, listing.seller_id)
        return jsonify({
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'price': listing.price,
            'rent_price': listing.rent_price,
            'category': listing.category,
            'condition': listing.condition,
            'image_url': listing.image_url,
            'created_at': listing.created_at.isoformat(),
            'seller_id': listing.seller_id,
            'seller': {
                'id': seller.id,
                'full_name': seller.full_name,
                'email': seller.email
            },
            'product_type': listing.product_type,
            'branch': listing.branch,
            'study_year': listing.study_year,
            'working_condition': listing.working_condition,
            'warranty_status': listing.warranty_status,
            'subject': listing.subject,
            'is_fake_warning': listing.is_fake_warning,
            'is_softcopy': listing.is_softcopy,
            'file_url': listing.file_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Report Routes
@app.route('/api/report/create', methods=['POST'])
@login_required
def create_report():
    try:
        # Process image if provided
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                image_url = save_image(image)
            else:
                image_url = None
        else:
            image_url = None

        # Description is required
        description = request.form.get('description')
        if not description:
            return jsonify({'error': 'Description is required'}), 400

        # Get IDs
        listing_id = request.form.get('listing_id')
        message_thread_id = request.form.get('message_thread_id')
        
        # Check if this is a temporary message thread ID
        is_temp_id = message_thread_id and message_thread_id.startswith('temp_')
        
        # For temporary IDs, we don't need an existing message thread
        if is_temp_id:
            message_thread_id = None
        
        # Require at least one ID or a description
        if not description:
            return jsonify({'error': 'Description is required'}), 400
        
        # Create the report
        report = Report(
            reporter_id=current_user.id,
            reported_listing_id=listing_id if listing_id else None,
            message_thread_id=message_thread_id if message_thread_id else None,
            description=description,
            image_url=image_url
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report submitted successfully',
            'report_id': report.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reports')
@login_required
def admin_get_reports():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        reports = Report.query.order_by(Report.created_at.desc()).all()
        reports_data = []
        
        for r in reports:
            report_data = {
                'id': r.id,
                'reporter': {
                    'id': r.reporter.id,
                    'name': r.reporter.full_name,
                    'email': r.reporter.email
                },
                'description': r.description,
                'image_url': r.image_url,
                'status': r.status,
                'created_at': r.created_at.isoformat()
            }
            
            # Add listing info if available
            if r.reported_listing_id and r.reported_listing:
                report_data['listing'] = {
                    'id': r.reported_listing.id,
                    'title': r.reported_listing.title
                }
            else:
                report_data['listing'] = None
                
            # Add message info if available
            if r.message_thread_id and r.message_thread:
                report_data['message'] = {
                    'id': r.message_thread.id,
                    'sender_name': r.message_thread.sender.full_name,
                    'receiver_name': r.message_thread.receiver.full_name
                }
            else:
                report_data['message'] = None
                
            reports_data.append(report_data)
        
        return jsonify({'reports': reports_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reports/<int:report_id>')
@login_required
def admin_get_report_details(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        report = db.get_or_404(Report, report_id)
        response_data = {
            'id': report.id,
            'reporter': {
                'id': report.reporter.id,
                'name': report.reporter.full_name,
                'email': report.reporter.email,
                'college': report.reporter.college
            },
            'description': report.description,
            'image_url': report.image_url,
            'status': report.status,
            'created_at': report.created_at.isoformat()
        }
        
        # Add listing info if it exists
        if report.reported_listing_id and report.reported_listing:
            response_data['listing'] = {
                'id': report.reported_listing.id,
                'title': report.reported_listing.title,
                'seller': {
                    'id': report.reported_listing.seller.id,
                    'name': report.reported_listing.seller.full_name,
                    'email': report.reported_listing.seller.email
                }
            }
        else:
            response_data['listing'] = None
            
        # Add message thread info if it exists
        if report.message_thread_id and report.message_thread:
            response_data['message_thread'] = {
                'id': report.message_thread.id,
                'content': report.message_thread.content,
                'sender': {
                    'id': report.message_thread.sender.id,
                    'name': report.message_thread.sender.full_name
                },
                'receiver': {
                    'id': report.message_thread.receiver.id,
                    'name': report.message_thread.receiver.full_name
                }
            }
        else:
            response_data['message_thread'] = None
            
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reports/<int:report_id>/status', methods=['POST'])
@login_required
def admin_update_report_status(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        report = db.get_or_404(Report, report_id)
        new_status = request.json.get('status')
        
        if new_status not in ['pending', 'reviewed', 'resolved']:
            return jsonify({'error': 'Invalid status'}), 400
            
        report.status = new_status
        db.session.commit()
        
        return jsonify({
            'message': 'Report status updated successfully',
            'status': report.status
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Create admin user on startup
def create_admin_user():
    try:
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@studentsmart.co.in').first()
        
        if not admin:
            admin_user = User(
                email='admin@studentsmart.co.in',
                full_name='Super Admin',
                department='Admin',
                year=1,
                college='Admin College',
                is_verified=True,
                is_admin=True,
                admin_role='super_admin'
            )
            admin_user.set_password('MentorlyXVemuXRcee@')
            db.session.add(admin_user)
            db.session.commit()
        elif admin and not admin.admin_role:
            # Update existing admin to have super_admin role
            admin.admin_role = 'super_admin'
            db.session.commit()
            print("Admin user created successfully")
        else:
            print("Admin user already exists")
    except Exception as e:
        db.session.rollback()
        print(f"Admin user creation failed or already exists: {str(e)}")
@app.route('/debug/files/<int:listing_id>')
@login_required
def debug_file_paths(listing_id):
    """Debug route to diagnose file path issues"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        listing = db.get_or_404(Listing, listing_id)
        result = {
            'listing_id': listing.id,
            'title': listing.title,
            'is_softcopy': listing.is_softcopy,
            'file_url': listing.file_url,
            'app_root': app.root_path,
            'cwd': os.getcwd(),
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'paths_checked': []
        }
        
        if listing.is_softcopy and listing.file_url:
            # Get filename
            if listing.file_url.startswith('uploads/'):
                file_name = listing.file_url.split('/')[-1]
            else:
                file_name = listing.file_url
                
            result['extracted_filename'] = file_name
            
            # Check various paths
            paths_to_check = [
                os.path.join(app.root_path, 'static', 'uploads', file_name),
                os.path.join('static', 'uploads', file_name),
                os.path.join(os.getcwd(), 'static', 'uploads', file_name),
                os.path.join(app.root_path, 'static', listing.file_url),
                os.path.join(os.getcwd(), 'static', listing.file_url)
            ]
            
            for path in paths_to_check:
                exists = os.path.exists(path)
                result['paths_checked'].append({
                    'path': path,
                    'exists': exists,
                    'is_file': os.path.isfile(path) if exists else False,
                    'is_dir': os.path.isdir(path) if exists else False,
                    'size': os.path.getsize(path) if exists and os.path.isfile(path) else None
                })
                
            # List the static/uploads directory to see what's there
            uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
            if os.path.exists(uploads_dir):
                result['uploads_dir_contents'] = os.listdir(uploads_dir)
            else:
                result['uploads_dir_contents'] = "Directory not found"
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/debug/system')
@login_required
def debug_system():
    """Debug route to check system configuration and ensure directories exist"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        result = {
            'app_info': {
                'root_path': app.root_path,
                'static_folder': app.static_folder,
                'upload_folder_config': app.config['UPLOAD_FOLDER'],
                'current_directory': os.getcwd()
            },
            'directories': {},
            'actions_taken': []
        }
        
        # Check and create necessary directories
        directories_to_check = [
            app.config['UPLOAD_FOLDER'],
            os.path.join(app.root_path, 'static', 'uploads'),
            os.path.join('static', 'uploads'),
        ]
        
        for directory in directories_to_check:
            exists = os.path.exists(directory)
            is_dir = os.path.isdir(directory) if exists else False
            
            result['directories'][directory] = {
                'exists': exists,
                'is_directory': is_dir
            }
            
            # Create the directory if it doesn't exist
            if not exists:
                try:
                    os.makedirs(directory, exist_ok=True)
                    result['actions_taken'].append(f"Created directory: {directory}")
                    result['directories'][directory]['exists'] = True
                    result['directories'][directory]['is_directory'] = True
                except Exception as e:
                    result['actions_taken'].append(f"Failed to create {directory}: {str(e)}")
        
        # Run the path fixing code directly
        try:
            listings = Listing.query.filter(Listing.is_softcopy == True).filter(Listing.file_url.isnot(None)).all()
            updated_count = 0
            
            for listing in listings:
                if listing.file_url and listing.file_url.startswith('uploads/'):
                    # Get just the filename
                    filename = listing.file_url.split('/')[-1]
                    result['actions_taken'].append(f"Fixing path for listing #{listing.id}: {listing.file_url} -> {filename}")
                    listing.file_url = filename
                    updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                result['actions_taken'].append(f"Fixed {updated_count} file paths in database")
            else:
                result['actions_taken'].append("No file paths needed fixing in database")
        except Exception as e:
            db.session.rollback()
            result['actions_taken'].append(f"Error fixing file paths: {str(e)}")
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:listing_id>')
@login_required
def download_file(listing_id):
    """Download a softcopy file"""
    try:
        # Get the listing
        listing = db.session.get(Listing, listing_id)
        if not listing:
            abort(404)

        print(f"\n\n===== DOWNLOAD REQUEST for listing ID: {listing_id} =====")
        print(f"Listing info: {listing.title}, is_softcopy: {listing.is_softcopy}, file_url: {listing.file_url}")
        
        # Check if it's a softcopy
        if not listing.is_softcopy:
            print(f"Listing {listing_id} is not a softcopy")
            abort(404)
            
        # Get the filename from file_url
        file_url = listing.file_url
        if not file_url:
            print(f"Listing {listing_id} has no file_url")
            abort(404)
            
        # Extract just the filename regardless of format
        if '/' in file_url:
            file_name = file_url.split('/')[-1] 
        else:
            file_name = file_url
            
        print(f"Looking for file: {file_name}")
        
        # Check for working files to find the correct directory
        test_filenames = [
            "2881bee4-a0ee-4efe-ae76-4dd654b79429_NLP_Exam_Preparation_Topics.pdf",
            "603f8fa0-0fa4-4295-a383-81dd385778e2_N_L_RAM_CHARAN_TEJA.pdf"
        ]
        
        working_file_paths = []
        for test_file in test_filenames:
            possible_locations = [
                os.path.join(app.root_path, 'static', 'uploads', test_file),
                os.path.join(os.getcwd(), 'static', 'uploads', test_file),
                os.path.join('static', 'uploads', test_file)
            ]
            
            for location in possible_locations:
                if os.path.exists(location):
                    working_file_paths.append(location)
                    
        if working_file_paths:
            print(f"Found working files at: {working_file_paths}")
            working_dir = os.path.dirname(working_file_paths[0])
            print(f"Using working directory: {working_dir}")
            file_path = os.path.join(working_dir, file_name)
            print(f"Checking for file at: {file_path}")
            if os.path.exists(file_path):
                print(f"File found at working directory path: {file_path}")
                
                # Get the file extension for MIME type
                _, file_ext = os.path.splitext(file_path)
                file_ext = file_ext.lower()
                
                # Set the appropriate MIME type
                if file_ext == '.pdf':
                    mimetype = 'application/pdf'
                elif file_ext == '.doc':
                    mimetype = 'application/msword'
                elif file_ext == '.docx':
                    mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif file_ext == '.txt':
                    mimetype = 'text/plain'
                elif file_ext in ['.ppt', '.pptx']:
                    mimetype = 'application/vnd.ms-powerpoint'
                elif file_ext in ['.xls', '.xlsx']:
                    mimetype = 'application/vnd.ms-excel'
                else:
                    mimetype = 'application/octet-stream'
                    
                # Download the file
                download_name = f"{secure_filename(listing.title)}{file_ext}"
                print(f"Sending file {file_path} as {download_name} with mimetype {mimetype}")
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=download_name,
                    mimetype=mimetype
                )
        
        # Try all possible locations if working directory approach failed
        print("Working directory approach failed, trying all possible paths")
        
        # Search in multiple locations
        possible_paths = [
            os.path.join(app.root_path, 'static', 'uploads', file_name),
            os.path.join(os.getcwd(), 'static', 'uploads', file_name),
            os.path.join('static', 'uploads', file_name),
            os.path.join(app.root_path, 'static', file_url),
            os.path.join(os.getcwd(), 'static', file_url)
        ]
        
        print(f"Trying paths: {possible_paths}")
        
        file_path = None
        for path in possible_paths:
            print(f"Checking: {path}")
            if os.path.exists(path):
                file_path = path
                print(f"Found at: {file_path}")
                break
        
        if not file_path:
            # If still not found, search recursively
            print("File not found in standard paths, searching recursively")
            
            search_dirs = [
                os.path.join(app.root_path, 'static'),
                os.path.join(os.getcwd(), 'static')
            ]
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    print(f"Searching directory: {search_dir}")
                    for root, dirs, files in os.walk(search_dir):
                        if file_name in files:
                            file_path = os.path.join(root, file_name)
                            print(f"Found through recursive search: {file_path}")
                            break
                if file_path:
                    break
        
        if not file_path:
            print("File not found after exhaustive search")
            abort(404)
        
        # Get the file extension for MIME type
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        # Set the appropriate MIME type
        if file_ext == '.pdf':
            mimetype = 'application/pdf'
        elif file_ext == '.doc':
            mimetype = 'application/msword'
        elif file_ext == '.docx':
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_ext == '.txt':
            mimetype = 'text/plain'
        elif file_ext in ['.ppt', '.pptx']:
            mimetype = 'application/vnd.ms-powerpoint'
        elif file_ext in ['.xls', '.xlsx']:
            mimetype = 'application/vnd.ms-excel'
        else:
            mimetype = 'application/octet-stream'
            
        # Download the file
        download_name = f"{secure_filename(listing.title)}{file_ext}"
        print(f"Sending file {file_path} as {download_name} with mimetype {mimetype}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype=mimetype
        )
    
    except Exception as e:
        print(f"Error in download_file: {str(e)}")
        import traceback
        traceback.print_exc()
        abort(500)

@app.route('/debug/dirs')
def debug_directories():
    """Debug route to show directory structure"""
    try:
        result = {
            "app_info": {
                "root_path": app.root_path,
                "static_folder": app.static_folder,
                "upload_folder_config": app.config['UPLOAD_FOLDER'],
                "current_directory": os.getcwd()
            },
            "directory_tree": {}
        }
        
        # Check key directories
        key_dirs = [
            os.path.join(app.root_path, 'static'),
            os.path.join(app.root_path, 'static', 'uploads'),
            app.config['UPLOAD_FOLDER'],
            os.path.join(os.getcwd(), 'static'),
            os.path.join(os.getcwd(), 'static', 'uploads')
        ]
        
        # Check if directories exist and list their contents
        for directory in key_dirs:
            if os.path.exists(directory):
                result["directory_tree"][directory] = {
                    "exists": True,
                    "is_dir": os.path.isdir(directory),
                    "contents": os.listdir(directory) if os.path.isdir(directory) else None
                }
            else:
                result["directory_tree"][directory] = {
                    "exists": False
                }
        
        # Also list all softcopy listings
        with app.app_context():
            result["softcopy_listings"] = [
                {
                    "id": l.id,
                    "title": l.title,
                    "file_url": l.file_url,
                    "created_at": l.created_at.isoformat() if l.created_at else None
                }
                for l in Listing.query.filter_by(is_softcopy=True).all()
            ]
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/debug/fix-file/<int:listing_id>')
@login_required
def debug_fix_file(listing_id):
    """Debug route to fix a file location for a specific listing"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        result = {
            "listing_id": listing_id,
            "actions": []
        }
        
        # Find the listing
        listing = db.session.get(Listing, listing_id)
        if not listing:
            abort(404)
        result["listing_info"] = {
            "id": listing.id,
            "title": listing.title,
            "is_softcopy": listing.is_softcopy,
            "file_url": listing.file_url
        }
        
        if not listing.is_softcopy or not listing.file_url:
            return jsonify({"error": "Listing is not a softcopy or has no file URL"}), 400
        
        # Get filenames
        if '/' in listing.file_url:
            file_name = listing.file_url.split('/')[-1]
            result["actions"].append(f"Extracted filename {file_name} from {listing.file_url}")
            
            # Update the database to store just the filename
            old_file_url = listing.file_url
            listing.file_url = file_name
            db.session.commit()
            result["actions"].append(f"Updated database entry from {old_file_url} to {file_name}")
        else:
            file_name = listing.file_url
        
        # Find the file
        file_found = False
        found_path = None
        
        # List of places to look for the file
        search_locations = [
            app.root_path,
            os.getcwd(),
            os.path.join(app.root_path, 'static'),
            os.path.join(os.getcwd(), 'static')
        ]
        
        # Search for the file
        for location in search_locations:
            for root, dirs, files in os.walk(location):
                if file_name in files:
                    found_path = os.path.join(root, file_name)
                    file_found = True
                    result["actions"].append(f"Found file at {found_path}")
                    break
            if file_found:
                break
        
        if not file_found:
            result["actions"].append(f"File not found in any location")
            return jsonify(result), 404
        
        # Ensure target directory exists
        target_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(target_dir, exist_ok=True)
        result["actions"].append(f"Ensured target directory exists: {target_dir}")
        
        # Copy the file to the target location if it's not already there
        target_path = os.path.join(target_dir, file_name)
        if os.path.abspath(found_path) != os.path.abspath(target_path):
            import shutil
            shutil.copy2(found_path, target_path)
            result["actions"].append(f"Copied file from {found_path} to {target_path}")
            
            # Verify the copy was successful
            if os.path.exists(target_path):
                result["actions"].append(f"Verified file exists at target location")
                result["success"] = True
            else:
                result["actions"].append(f"Failed to copy file to target location")
                result["success"] = False
        else:
            result["actions"].append(f"File is already in the correct location")
            result["success"] = True
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/cofundersprofiles.html')
def cofounders_profile():
    return send_file('cofundersprofiles.html')
# Email Configuration (add with your other configs)


# Notification Endpoint
@app.route('/api/send_message_notification', methods=['POST'])
@login_required
def send_message_notification():
    print("\n=== NOTIFICATION ENDPOINT HIT ===")  # Debug log
    try:
        data = request.get_json()
        print("Received data:", data)  # Debug log
        
        if not data:
            print("No data received")  # Debug log
            return jsonify({'error': 'No data provided'}), 400

        recipient = db.session.get(User, data.get('recipient_id'))
        sender = db.session.get(User, data.get('sender_id'))
        listing = db.session.get(Listing, data.get('listing_id'))

        if not all([recipient, sender, listing]):
            print("Missing recipient, sender, or listing")  # Debug log
            return jsonify({'error': 'Invalid recipient, sender, or listing'}), 404

        print(f"Preparing email to {recipient.email}")  # Debug log
        
        # Create email with improved HTML template
        msg = Message(
            subject=f"New Message About Your Listing: {listing.title}",
            recipients=[recipient.email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">New Message on StudentsMart</h2>
                <p>You've received a new message about your listing:</p>
                <div style="background: #f3f4f6; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="margin-top: 0;">{listing.title}</h3>
                    <p><strong>From:</strong> {sender.full_name} ({sender.college})</p>
                </div>
                <a href="{url_for('index', _external=True)}" 
                   style="display: inline-block; padding: 10px 20px; background: #2563eb; 
                          color: white; text-decoration: none; border-radius: 5px;">
                    View Message
                </a>
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">
                    This is an automated notification. Please do not reply directly to this email.
                </p>
            </div>
            """
        )

        # Improved email sending with better error handling
        def send_async_email(app, msg):
            with app.app_context():
                try:
                    print("Attempting to send email...")  # Debug log
                    mail.send(msg)
                    print("Email sent successfully!")  # Debug log
                except Exception as e:
                    print(f"Failed to send email: {str(e)}")  # Debug log
                    # Log full error details for debugging
                    app.logger.error(f"Email sending failed: {str(e)}")
                    if hasattr(e, 'smtp_error'):
                        app.logger.error(f"SMTP error: {e.smtp_error}")

        # Start thread with error handling
        try:
            Thread(target=send_async_email, args=(app, msg)).start()
        except Exception as e:
            print(f"Failed to start email thread: {str(e)}")
            return jsonify({'error': 'Failed to queue email'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Notification queued for sending'
        })

    except Exception as e:
        error_msg = f"Notification processing error: {str(e)}"
        print(error_msg)  # Debug log
        app.logger.error(error_msg)
        return jsonify({
            'error': 'Failed to process notification',
            'details': str(e)
        }), 500
@app.route('/<filename>')
def serve_html(filename):
    if filename.endswith('.html') and os.path.exists(filename):
        return send_file(filename)
    else:
        return "File not found", 404
# Add these routes to your Flask app

@app.route('/profiledashboard')
@login_required
def profile_dashboard():
    print(f"Profile dashboard accessed by: {current_user.id}")
    print(f"Session: {dict(session)}")
    print(f"Authenticated: {current_user.is_authenticated}")
    return send_file('profiledashboard.html')

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.form
        print(f"Received profile update data: {dict(data)}")  # Debug log
        
        # Handle empty roll number properly
        roll_number = data.get('roll_number', '').strip()
        if not roll_number:
            roll_number = None  # Use NULL instead of empty string
            
        # Check for duplicate roll numbers (excluding current user)
        if roll_number:
            existing = User.query.filter(
                User.roll_number == roll_number,
                User.id != current_user.id
            ).first()
            if existing:
                return jsonify({'error': 'This roll number is already taken by another student'}), 400
        
        # Update the user fields
        current_user.full_name = data.get('full_name', current_user.full_name)
        current_user.department = data.get('department', current_user.department)
        current_user.year = int(data.get('year', current_user.year))
        current_user.roll_number = roll_number
        
        print(f"Updated user data: name={current_user.full_name}, dept={current_user.department}, year={current_user.year}, roll={current_user.roll_number}")
        
        db.session.commit()
        print("Profile update committed to database")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'full_name': current_user.full_name,
                'department': current_user.department,
                'year': current_user.year,
                'roll_number': current_user.roll_number,
                'college': current_user.college,
                'email': current_user.email
            }
        })
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    try:
        print("Profile picture upload started")
        
        if 'profile_picture' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF files only.'}), 400
            
        # Save the image
        filename = secure_filename(file.filename)
        unique_filename = f"profile_{current_user.id}_{uuid.uuid4()}.{file_extension}"
        
        # Use your configured upload folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        print(f"File saved to: {file_path}")
        
        # Update user profile picture
        current_user.profile_picture = f"uploads/{unique_filename}"
        db.session.commit()
        
        print(f"Profile picture updated in database: {current_user.profile_picture}")
        
        return jsonify({
            'message': 'Profile picture updated successfully',
            'profile_picture': current_user.profile_picture
        })
    except Exception as e:
        print(f"Profile picture upload error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.form
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400
            
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
            
        # Set new password
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/request-college-change', methods=['POST'])
@login_required
def request_college_change():
    try:
        print(f"College change request from user {current_user.id}")
        
        # Check if user already has a pending request
        pending_request = CollegeChangeRequest.query.filter_by(
            user_id=current_user.id, 
            status='pending'
        ).first()
        
        if pending_request:
            return jsonify({
                'error': 'You already have a pending college change request. Please wait for it to be processed.'
            }), 400

        # Validate required files - only new college proof needed
        if 'new_college_proof' not in request.files:
            return jsonify({'error': 'New college ID proof is required'}), 400
        
        new_proof = request.files['new_college_proof']
        
        if new_proof.filename == '':
            return jsonify({'error': 'New college ID proof is required'}), 400
        
        # Get form data
        new_college = request.form.get('new_college')
        reason = request.form.get('reason', '')
        
        if not new_college or not reason:
            return jsonify({'error': 'New college and reason are required'}), 400
        
        print(f"Request data: new_college={new_college}, reason={reason[:50]}...")
        
        # Save proof file using your configured upload folder
        def save_proof_file(file):
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
            unique_filename = f"college_proof_{current_user.id}_{uuid.uuid4()}.{file_extension}"
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            return file_path  # Return the full file path for email attachment
        
        new_proof_full_path = save_proof_file(new_proof)
        new_proof_path = f"uploads/{os.path.basename(new_proof_full_path)}"  # For database storage
        
        print(f"Proof file saved: new={new_proof_path}")
        
        # Create college change request
        change_request = CollegeChangeRequest(
            user_id=current_user.id,
            old_college=current_user.college,
            new_college=new_college,
            reason=reason,
            new_college_proof=new_proof_path
        )
        
        db.session.add(change_request)
        db.session.commit()
        
        print(f"College change request created with ID: {change_request.id}")
        
        # Send email to admin with proof attachment
        try:
            send_college_change_request_email(
                current_user, 
                current_user.college, 
                new_college, 
                reason,
                new_proof_full_path  # Pass the full file path for attachment
            )
            print("Admin notification email sent with attachment")
        except Exception as email_error:
            print(f"Email sending failed: {str(email_error)}")
            # Don't fail the request if email fails
        
        return jsonify({
            'message': 'College change request submitted successfully. You will receive an email once it is processed.',
            'request_id': change_request.id
        })
        
    except Exception as e:
        print(f"College change request error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/college-change-status')
@login_required
def get_college_change_status():
    try:
        # Get the latest request for this user
        change_request = CollegeChangeRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(CollegeChangeRequest.created_at.desc()).first()
        
        if not change_request:
            return jsonify({'has_request': False})
        
        return jsonify({
            'has_request': True,
            'status': change_request.status,
            'old_college': change_request.old_college,
            'new_college': change_request.new_college,
            'reason': change_request.reason,
            'rejection_reason': change_request.rejection_reason,
            'created_at': change_request.created_at.isoformat(),
            'reviewed_at': change_request.reviewed_at.isoformat() if change_request.reviewed_at else None
        })
        
    except Exception as e:
        print(f"Status check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/approve-college-change/<int:user_id>')
@login_required
def admin_approve_college_change(user_id):
    if not current_user.is_admin:
        return "Unauthorized", 403
    
    try:
        # Get the latest pending request for this user
        change_request = CollegeChangeRequest.query.filter_by(
            user_id=user_id, 
            status='pending'
        ).order_by(CollegeChangeRequest.created_at.desc()).first()
        
        if not change_request:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Request Not Found</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px; 
                        background: #f8fafc;
                        margin: 0;
                    }
                    .container {
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                    h1 { color: #1f2937; margin-bottom: 15px; }
                    p { color: #6b7280; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">⚠️</div>
                    <h1>Request Not Found</h1>
                    <p>No pending college change request found for this user.</p>
                    <p>The request may have already been processed or doesn't exist.</p>
                </div>
            </body>
            </html>
            """), 404
        
        # Update user's college
        user = User.query.get(user_id)
        if not user:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>User Not Found</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px; 
                        background: #f8fafc;
                        margin: 0;
                    }
                    .container {
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                    h1 { color: #1f2937; margin-bottom: 15px; }
                    p { color: #6b7280; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">❌</div>
                    <h1>User Not Found</h1>
                    <p>The requested user could not be found.</p>
                </div>
            </body>
            </html>
            """), 404
        
        old_college = user.college
        user.college = change_request.new_college
        
        # Update request status
        change_request.status = 'approved'
        change_request.reviewed_at = datetime.utcnow()
        change_request.reviewed_by = current_user.id
        
        db.session.commit()
        
        # Send approval email to user
        try:
            send_college_change_approval_email(user, old_college, change_request.new_college)
            email_status = "An email notification has been sent to the user."
        except Exception as e:
            print(f"Approval email failed: {str(e)}")
            email_status = "Note: Email notification could not be sent."
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Request Approved</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: #f0fdf4;
                    margin: 0;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border: 2px solid #22c55e;
                }
                .success { color: #22c55e; font-size: 64px; margin-bottom: 20px; }
                h1 { color: #1f2937; margin-bottom: 15px; }
                p { color: #6b7280; line-height: 1.6; margin-bottom: 15px; }
                .details {
                    background: #f9fafb;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: left;
                }
                .detail-row {
                    margin-bottom: 10px;
                }
                .label {
                    font-weight: 600;
                    color: #374151;
                }
                .back-btn {
                    display: inline-block;
                    background: #6366f1;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin-top: 20px;
                    transition: background 0.2s;
                }
                .back-btn:hover {
                    background: #4f46e5;
                    color: white;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>College Change Approved</h1>
                <p>The college change request has been approved successfully.</p>
                
                <div class="details">
                    <div class="detail-row">
                        <span class="label">Student:</span> {{ user.full_name }} ({{ user.email }})
                    </div>
                    <div class="detail-row">
                        <span class="label">Previous College:</span> {{ old_college }}
                    </div>
                    <div class="detail-row">
                        <span class="label">New College:</span> {{ user.college }}
                    </div>
                    <div class="detail-row">
                        <span class="label">Approved By:</span> {{ current_user.full_name }}
                    </div>
                    <div class="detail-row">
                        <span class="label">Approved At:</span> {{ change_request.reviewed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
                    </div>
                </div>
                
                <p><strong>{{ email_status }}</strong></p>
                
                <a href="javascript:window.close()" class="back-btn">Close Window</a>
            </div>
        </body>
        </html>
        """, user=user, old_college=old_college, current_user=current_user, 
           change_request=change_request, email_status=email_status)
        
    except Exception as e:
        db.session.rollback()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: #fef2f2;
                    margin: 0;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border: 2px solid #ef4444;
                }
                .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                h1 { color: #1f2937; margin-bottom: 15px; }
                p { color: #6b7280; line-height: 1.6; }
                .error-details {
                    background: #fef2f2;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    color: #dc2626;
                    font-family: monospace;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">🚨</div>
                <h1>Error Approving Request</h1>
                <p>An error occurred while processing the approval.</p>
                <div class="error-details">{{ error }}</div>
                <p>Please contact the system administrator.</p>
            </div>
        </body>
        </html>
        """, error=str(e)), 500

@app.route('/admin/reject-college-change/<int:user_id>')
@login_required
def admin_reject_college_change(user_id):
    if not current_user.is_admin:
        return "Unauthorized", 403
    
    try:
        # Get the latest pending request for this user
        change_request = CollegeChangeRequest.query.filter_by(
            user_id=user_id, 
            status='pending'
        ).order_by(CollegeChangeRequest.created_at.desc()).first()
        
        if not change_request:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Request Not Found</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px; 
                        background: #f8fafc;
                        margin: 0;
                    }
                    .container {
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                    h1 { color: #1f2937; margin-bottom: 15px; }
                    p { color: #6b7280; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">⚠️</div>
                    <h1>Request Not Found</h1>
                    <p>No pending college change request found for this user.</p>
                    <p>The request may have already been processed or doesn't exist.</p>
                </div>
            </body>
            </html>
            """), 404
        
        user = User.query.get(user_id)
        if not user:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>User Not Found</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px; 
                        background: #f8fafc;
                        margin: 0;
                    }
                    .container {
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                    h1 { color: #1f2937; margin-bottom: 15px; }
                    p { color: #6b7280; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">❌</div>
                    <h1>User Not Found</h1>
                    <p>The requested user could not be found.</p>
                </div>
            </body>
            </html>
            """), 404
        
        rejection_reason = "We were not able to verify your college change request based on the documents provided. Please ensure you upload clear copies of valid college ID cards from both institutions."
        
        # Update request status
        change_request.status = 'rejected'
        change_request.reviewed_at = datetime.utcnow()
        change_request.reviewed_by = current_user.id
        change_request.rejection_reason = rejection_reason
        
        db.session.commit()
        
        # Send rejection email to user
        try:
            send_college_change_rejection_email(
                user, 
                change_request.old_college, 
                change_request.new_college, 
                rejection_reason
            )
            email_status = "An email notification has been sent to the user with the reason."
        except Exception as e:
            print(f"Rejection email failed: {str(e)}")
            email_status = "Note: Email notification could not be sent."
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Request Rejected</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: #fef2f2;
                    margin: 0;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border: 2px solid #ef4444;
                }
                .error { color: #ef4444; font-size: 64px; margin-bottom: 20px; }
                h1 { color: #1f2937; margin-bottom: 15px; }
                p { color: #6b7280; line-height: 1.6; margin-bottom: 15px; }
                .details {
                    background: #f9fafb;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: left;
                }
                .detail-row {
                    margin-bottom: 10px;
                }
                .label {
                    font-weight: 600;
                    color: #374151;
                }
                .reason {
                    background: #fef2f2;
                    border: 1px solid #fecaca;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 15px 0;
                    color: #dc2626;
                }
                .back-btn {
                    display: inline-block;
                    background: #6366f1;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin-top: 20px;
                    transition: background 0.2s;
                }
                .back-btn:hover {
                    background: #4f46e5;
                    color: white;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">❌</div>
                <h1>College Change Rejected</h1>
                <p>The college change request has been rejected.</p>
                
                <div class="details">
                    <div class="detail-row">
                        <span class="label">Student:</span> {{ user.full_name }} ({{ user.email }})
                    </div>
                    <div class="detail-row">
                        <span class="label">Current College:</span> {{ change_request.old_college }}
                    </div>
                    <div class="detail-row">
                        <span class="label">Requested College:</span> {{ change_request.new_college }}
                    </div>
                    <div class="detail-row">
                        <span class="label">Rejected By:</span> {{ current_user.full_name }}
                    </div>
                    <div class="detail-row">
                        <span class="label">Rejected At:</span> {{ change_request.reviewed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
                    </div>
                </div>
                
                <div class="reason">
                    <strong>Rejection Reason:</strong><br>
                    {{ change_request.rejection_reason }}
                </div>
                
                <p><strong>{{ email_status }}</strong></p>
                
                <a href="javascript:window.close()" class="back-btn">Close Window</a>
            </div>
        </body>
        </html>
        """, user=user, change_request=change_request, current_user=current_user, email_status=email_status)
        
    except Exception as e:
        db.session.rollback()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: #fef2f2;
                    margin: 0;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border: 2px solid #ef4444;
                }
                .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                h1 { color: #1f2937; margin-bottom: 15px; }
                p { color: #6b7280; line-height: 1.6; }
                .error-details {
                    background: #fef2f2;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    color: #dc2626;
                    font-family: monospace;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">🚨</div>
                <h1>Error Rejecting Request</h1>
                <p>An error occurred while processing the rejection.</p>
                <div class="error-details">{{ error }}</div>
                <p>Please contact the system administrator.</p>
            </div>
        </body>
        </html>
        """, error=str(e)), 500

def send_college_change_request_email(user, old_college, new_college, reason, proof_file_path):
    """Send email to admin about college change request with proof attachment"""
    try:
        admin_email = "contactstudentsmart@gmail.com"
        
        msg = Message(
            subject=f'College Change Request - {user.full_name}',
            sender=app.config['MAIL_USERNAME'],
            recipients=[admin_email]
        )
        
        # Create approval and rejection links
        # Use your actual domain/server URL
        base_url = "http://127.0.0.1:80/"  # Change this to your actual server URL
        approve_url = f"{base_url}/admin/approve-college-change/{user.id}"
        reject_url = f"{base_url}/admin/reject-college-change/{user.id}"
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2563eb;">New College Change Request</h2>
            
            <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Request Details</h3>
                <p><strong>Student:</strong> {user.full_name} ({user.email})</p>
                <p><strong>Current College:</strong> {old_college}</p>
                <p><strong>Requested College:</strong> {new_college}</p>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            
            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>📎 Attached Document:</strong> New College ID Proof</p>
                <p style="font-size: 14px; color: #92400e;">
                    Please review the attached ID proof for verification before approving the request.
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{approve_url}" style="display: inline-block; background: #22c55e; color: white; 
                    padding: 12px 25px; text-decoration: none; border-radius: 6px; margin-right: 15px;">
                    Approve Request
                </a>
                <a href="{reject_url}" style="display: inline-block; background: #ef4444; color: white; 
                    padding: 12px 25px; text-decoration: none; border-radius: 6px;">
                    Reject Request
                </a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">
                This is an automated notification. Please review the attached proof document and take appropriate action.
            </p>
        </div>
        """
        
        # Attach the new college proof file
        try:
            # Check if file exists
            if os.path.exists(proof_file_path):
                with open(proof_file_path, 'rb') as fp:
                    # Determine file extension and content type
                    file_extension = os.path.splitext(proof_file_path)[1].lower()
                    if file_extension in ['.jpg', '.jpeg']:
                        content_type = "image/jpeg"
                    elif file_extension == '.png':
                        content_type = "image/png"
                    elif file_extension == '.pdf':
                        content_type = "application/pdf"
                    elif file_extension == '.gif':
                        content_type = "image/gif"
                    else:
                        content_type = "application/octet-stream"
                    
                    msg.attach(
                        filename=f"new_college_proof_{user.id}{file_extension}",
                        content_type=content_type,
                        data=fp.read()
                    )
                print(f"Successfully attached proof file: {proof_file_path}")
            else:
                print(f"Proof file not found at: {proof_file_path}")
        except Exception as attach_error:
            print(f"Failed to attach proof file: {attach_error}")
            # Continue sending email without attachment
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending college change request email: {str(e)}")
        return False

def send_college_change_rejection_email(user, old_college, new_college, rejection_reason):
    """Send rejection email to user"""
    try:
        msg = Message(
            subject='Your College Change Request Status',
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ef4444;">College Change Request Not Approved</h2>
            
            <div style="background: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p>Dear {user.full_name},</p>
                <p>Your request to change college from <strong>{old_college}</strong> to <strong>{new_college}</strong> could not be approved at this time.</p>
                <p><strong>Reason:</strong> {rejection_reason}</p>
                <p>If you believe this is an error or would like to provide additional documentation, please submit a new request with clearer ID proof.</p>
            </div>
            
            <p style="color: #6b7280;">
                Thank you for your understanding.
            </p>
        </div>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending rejection email: {str(e)}")
        return False
def send_college_change_approval_email(user, old_college, new_college):
    """Send approval email to user"""
    try:
        msg = Message(
            subject='Your College Change Request Has Been Approved',
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #22c55e;">College Change Approved</h2>
            
            <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p>Dear {user.full_name},</p>
                <p>Your request to change college from <strong>{old_college}</strong> to <strong>{new_college}</strong> has been approved.</p>
                <p>Your college information has been updated in our system. Your existing listings will now be visible to students from your new college.</p>
            </div>
            
            <p style="color: #6b7280;">
                If you have any questions, please contact our support team.
            </p>
        </div>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending approval email: {str(e)}")
        return False



@app.route('/api/user-stats')
@login_required
def user_stats():
    try:
        listings_count = Listing.query.filter_by(seller_id=current_user.id).count()
        wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
        
        return jsonify({
            'listings_count': listings_count,
            'wishlist_count': wishlist_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/listings/<int:listing_id>')
def get_single_listing(listing_id):
    try:
        listing = Listing.query.join(User).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
            
        return jsonify({
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'price': listing.price,
            'rent_price': listing.rent_price,
            'category': listing.category,
            'condition': listing.condition,
            'image_url': listing.image_url,
            'is_for_rent': listing.is_for_rent,
            'created_at': listing.created_at.isoformat(),
            'seller': {
                'id': listing.seller.id,
                'name': listing.seller.full_name,
                'college': listing.seller.college
            },
            'is_softcopy': listing.is_softcopy,
            'file_url': listing.file_url,
            'product_type': listing.product_type,
            'branch': listing.branch,
            'study_year': listing.study_year,
            'working_condition': listing.working_condition,
            'warranty_status': listing.warranty_status,
            'subject': listing.subject,
            'faculty_name': listing.faculty_name,
            'is_fake_warning': listing.is_fake_warning
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/messages/unread-count')
@login_required
def get_unread_count():
    try:
        unread_count = MessageThread.query.filter(
            MessageThread.receiver_id == current_user.id,
            MessageThread.read == False
        ).count()
        
        return jsonify({
            'unread_count': unread_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/sales-stats')
@login_required
def admin_sales_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Total sales by status
        total_sales = SoldItem.query.filter_by(status='confirmed').count()
        pending_sales = SoldItem.query.filter_by(status='pending').count()
        denied_sales = SoldItem.query.filter_by(status='denied').count()
        
        # Recent sales (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_sales = SoldItem.query.filter(
            SoldItem.confirmed_at >= thirty_days_ago,
            SoldItem.status == 'confirmed'
        ).count()
        
        # Sales by category
        sales_by_category = db.session.query(
            Listing.category,
            db.func.count(SoldItem.id).label('count')
        ).join(SoldItem, Listing.id == SoldItem.listing_id)\
         .filter(SoldItem.status == 'confirmed')\
         .group_by(Listing.category)\
         .all()
        
        # Get all sold items with full details
        sold_items_query = db.session.query(SoldItem, Listing, User)\
            .outerjoin(Listing, SoldItem.listing_id == Listing.id)\
            .join(User, SoldItem.seller_id == User.id)\
            .order_by(SoldItem.sold_at.desc())\
            .all()
        
        sold_items_list = []
        for item in sold_items_query:
            sold_item = item.SoldItem
            listing = item.Listing
            seller = item.User
            
            sold_items_list.append({
                'id': sold_item.id,
                'listing_title': listing.title if listing else 'Deleted Listing',
                'listing_price': listing.price if listing else 0,
                'listing_category': listing.category if listing else 'N/A',
                'seller_name': seller.full_name,
                'seller_email': seller.email,
                'seller_college': seller.college,
                'buyer_name': sold_item.buyer_name,
                'buyer_email': sold_item.buyer_email,
                'status': sold_item.status,
                'sold_at': sold_item.sold_at.isoformat(),
                'confirmed_at': sold_item.confirmed_at.isoformat() if sold_item.confirmed_at else None
            })
        
        return jsonify({
            'total_sales': total_sales,
            'pending_sales': pending_sales,
            'denied_sales': denied_sales,
            'recent_sales': recent_sales,
            'sales_by_category': [{'category': cat, 'count': count} for cat, count in sales_by_category],
            'recent_sold_items': sold_items_list
        })
        
    except Exception as e:
        print(f"Error in sales stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/colleges')
@login_required
def admin_colleges():
    """Colleges and Interest Management - serves both HTML and JSON"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    # Check if this is an HTML request or JSON/AJAX request
    accept_header = request.headers.get('Accept', '')
    is_browser_request = accept_header.startswith('text/html')

    # If browser request, serve the HTML template
    if is_browser_request:
        return render_template('admin/colleges.html')

    # Otherwise, return JSON data (legacy API support)
    try:
        # Get college statistics
        colleges = db.session.query(
            User.college.label('college_name'),
            db.func.count(User.id).label('user_count'),
            db.func.sum(db.case((User.is_verified == True, 1), else_=0)).label('verified_users')
        ).filter(User.college.isnot(None))\
         .group_by(User.college)\
         .order_by(db.desc('user_count'))\
         .all()

        colleges_list = []
        for college in colleges:
            # Get listing count for this college
            listing_count = db.session.query(db.func.count(Listing.id))\
                .join(User, Listing.seller_id == User.id)\
                .filter(User.college == college.college_name)\
                .scalar()

            colleges_list.append({
                'college_name': college.college_name,
                'user_count': college.user_count,
                'verified_users': college.verified_users or 0,
                'listing_count': listing_count or 0
            })

        return jsonify({'colleges': colleges_list})

    except Exception as e:
        print(f"Error in admin colleges: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/colleges')
@login_required
def api_admin_colleges():
    """Enhanced colleges API with interest and state statistics"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get all student profiles with their user data
        profiles = db.session.query(
            StudentProfile, User
        ).join(User, StudentProfile.user_id == User.id)\
         .filter(User.college.isnot(None))\
         .all()

        # Build college data with interests
        college_data = {}
        all_interests = []
        states_set = set()

        for profile, user in profiles:
            college = user.college
            state = user.state or profile.state

            if college not in college_data:
                college_data[college] = {
                    'college_name': college,
                    'student_count': 0,
                    'state': state,
                    'interests': []
                }

            college_data[college]['student_count'] += 1

            # Parse interests
            if profile.interests:
                try:
                    interests = json.loads(profile.interests)
                    college_data[college]['interests'].extend(interests)
                    all_interests.extend(interests)
                except:
                    pass

            if state:
                states_set.add(state)

        # Calculate top interests per college
        colleges_list = []
        for college_name, data in college_data.items():
            # Count interest frequency
            from collections import Counter
            interest_counts = Counter(data['interests'])
            top_interests = [interest for interest, count in interest_counts.most_common(5)]

            colleges_list.append({
                'college_name': college_name,
                'student_count': data['student_count'],
                'state': data['state'],
                'top_interests': top_interests
            })

        # Sort by student count
        colleges_list.sort(key=lambda x: x['student_count'], reverse=True)

        # Calculate interest statistics
        from collections import Counter
        interest_counts = Counter(all_interests)
        interest_stats = [
            {'interest': interest, 'count': count}
            for interest, count in interest_counts.most_common(10)
        ]

        # Calculate state statistics
        state_counts = {}
        for profile, user in profiles:
            state = user.state or profile.state
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1

        state_stats = [
            {'state': state, 'count': count}
            for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        ]

        # Calculate stats
        stats = {
            'total_colleges': len(college_data),
            'total_students': len(profiles),
            'total_states': len(states_set),
            'top_interest': {
                'name': interest_stats[0]['interest'] if interest_stats else None,
                'count': interest_stats[0]['count'] if interest_stats else 0
            }
        }

        return jsonify({
            'colleges': colleges_list,
            'stats': stats,
            'interest_stats': interest_stats,
            'state_stats': state_stats,
            'states': sorted(list(states_set))
        })

    except Exception as e:
        print(f"Error in api_admin_colleges: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/students/filter', methods=['POST'])
@login_required
def api_admin_filter_students():
    """Filter students by interests, college, and state"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        interests = data.get('interests', [])
        college = data.get('college', '')
        state = data.get('state', '')

        # Build query
        query = db.session.query(StudentProfile, User)\
            .join(User, StudentProfile.user_id == User.id)

        # Apply filters
        if college:
            query = query.filter(User.college == college)

        if state:
            query = query.filter(
                db.or_(User.state == state, StudentProfile.state == state)
            )

        results = query.all()

        # Filter by interests if specified
        filtered_students = []
        for profile, user in results:
            # Check if student matches interest criteria
            if interests:
                if profile.interests:
                    try:
                        student_interests = json.loads(profile.interests)
                        # Check if any of the selected interests match
                        if not any(interest in student_interests for interest in interests):
                            continue
                    except:
                        continue
                else:
                    continue

            # Build student data
            filtered_students.append({
                'id': profile.id,
                'name': user.full_name,
                'email': user.email,
                'college': user.college,
                'state': user.state or profile.state,
                'department': user.department,
                'year': user.year,
                'interests': profile.interests,
                'phone': profile.phone,
                'profile_complete': profile.onboarding_complete
            })

        return jsonify({
            'students': filtered_students,
            'count': len(filtered_students)
        })

    except Exception as e:
        print(f"Error in api_admin_filter_students: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/interest-stats')
@login_required
def api_admin_interest_stats():
    """Get interest distribution statistics"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get all student profiles
        profiles = StudentProfile.query.all()

        # Collect all interests
        all_interests = []
        for profile in profiles:
            if profile.interests:
                try:
                    interests = json.loads(profile.interests)
                    all_interests.extend(interests)
                except:
                    pass

        # Count interest frequency
        from collections import Counter
        interest_counts = Counter(all_interests)

        stats = [
            {'interest': interest, 'count': count}
            for interest, count in interest_counts.most_common()
        ]

        return jsonify({
            'interest_stats': stats
        })

    except Exception as e:
        print(f"Error in api_admin_interest_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/college-details/<college_name>')
@login_required
def admin_college_details(college_name):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get college statistics
        user_count = User.query.filter_by(college=college_name).count()
        verified_users = User.query.filter_by(college=college_name, is_verified=True).count()
        
        # Get listing count
        listing_count = db.session.query(db.func.count(Listing.id))\
            .join(User, Listing.seller_id == User.id)\
            .filter(User.college == college_name)\
            .scalar()
        
        # Get recent users
        recent_users = User.query.filter_by(college=college_name)\
            .order_by(User.created_at.desc())\
            .limit(5)\
            .all()
        
        # Get recent listings
        recent_listings = db.session.query(Listing, User)\
            .join(User, Listing.seller_id == User.id)\
            .filter(User.college == college_name)\
            .order_by(Listing.created_at.desc())\
            .limit(5)\
            .all()
        
        return jsonify({
            'college_name': college_name,
            'user_count': user_count,
            'verified_users': verified_users,
            'listing_count': listing_count or 0,
            'recent_users': [{
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'is_verified': user.is_verified,
                'created_at': user.created_at.isoformat()
            } for user in recent_users],
            'recent_listings': [{
                'id': listing.Listing.id,
                'title': listing.Listing.title,
                'category': listing.Listing.category,
                'price': listing.Listing.price,
                'seller_name': listing.User.full_name,
                'created_at': listing.Listing.created_at.isoformat()
            } for listing in recent_listings]
        })
        
    except Exception as e:
        print(f"Error in college details: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/company/login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'GET':
        return render_template('company/login.html')
    
    email = request.json.get('email')
    password = request.json.get('password')
    
    company = Company.query.filter_by(email=email).first()
    if company and company.check_password(password):
        session['company_id'] = company.id
        session['user_type'] = 'company'
        return jsonify({'success': True, 'redirect': url_for('company_dashboard')})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/company/register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'GET':
        return render_template('company/register.html')

    data = request.json
    existing_company = Company.query.filter_by(email=data['email']).first()
    if existing_company:
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    company = Company(
        email=data['email'],
        company_name=data['company_name'],
        website=data.get('website'),
        industry=data.get('industry'),
        company_size=data.get('company_size'),
        mobile=data.get('mobile'),
        contact_person_name=data.get('contact_person_name'),
        contact_person_position=data.get('contact_person_position'),
        is_verified=True
    )
    company.set_password(data['password'])
    db.session.add(company)
    db.session.commit()

    session['company_id'] = company.id
    session['user_type'] = 'company'
    return jsonify({'success': True, 'redirect': url_for('company_dashboard')})


@app.route('/company/google')
def company_google_auth():
    redirect_uri = url_for('company_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/company/google/callback')
def company_google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information', 'error')
            return redirect(url_for('company_login'))
        
        company = Company.query.filter_by(google_id=user_info['sub']).first()
        if not company:
            company = Company.query.filter_by(email=user_info['email']).first()
            if company:
                company.google_id = user_info['sub']
                company.is_google_user = True
                company.is_verified = True
            else:
                company = Company(
                    email=user_info['email'],
                    company_name=user_info.get('name', 'Company'),
                    google_id=user_info['sub'],
                    is_google_user=True,
                    is_verified=True
                )
                db.session.add(company)
            db.session.commit()
        
        session['company_id'] = company.id
        session['user_type'] = 'company'
        return redirect(url_for('company_dashboard'))
        
    except Exception as e:
        print(f"Google auth error: {e}")
        flash('Authentication failed', 'error')
        return redirect(url_for('company_login'))


@app.route('/student/onboarding/step1', methods=['GET', 'POST'])
@login_required
def student_onboarding_step1():
    if request.method == 'GET':
        return render_template('student/onboarding_step1.html')
    
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = StudentProfile(user_id=current_user.id)
        db.session.add(profile)
    
    profile.phone = request.json.get('phone')
    profile.bio = request.json.get('bio')
    profile.location = request.json.get('location')
    profile.state = request.json.get('state')
    profile.linkedin_url = request.json.get('linkedin_url')
    profile.github_url = request.json.get('github_url')
    profile.portfolio_url = request.json.get('portfolio_url')
    profile.leetcode_url = request.json.get('leetcode_url')
    db.session.commit()
    
    return jsonify({'success': True, 'redirect': url_for('student_onboarding_step2')})


@app.route('/student/onboarding/step2', methods=['GET', 'POST'])
@login_required
def student_onboarding_step2():
    if request.method == 'GET':
        return render_template('student/onboarding_step2.html')

    try:
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            print(f"[STEP2] ERROR: Profile not found for user_id: {current_user.id}")
            return jsonify({'success': False, 'message': 'Profile not found. Please complete Step 1 first or contact admin.'}), 400

        print(f"[STEP2] Found profile ID: {profile.id} for user_id: {current_user.id}")
        data = request.json
        print(f"[STEP2] Received data: {data}")

        # Validate request data
        if not data:
            print(f"[STEP2] ERROR: No data received")
            return jsonify({'success': False, 'message': 'No data received. Please try again.'}), 400

        # Save interests
        if 'interests' in data:
            import json
            interests_list = data.get('interests', [])
            # Ensure it's a list
            if isinstance(interests_list, list):
                profile.interests = json.dumps(interests_list)
                print(f"[STEP2] Saved {len(interests_list)} interests")
            else:
                print(f"[STEP2] WARNING: interests is not a list: {type(interests_list)}")

        # Delete existing education records to avoid duplicates
        deleted_count = Education.query.filter_by(student_profile_id=profile.id).delete()
        print(f"[STEP2] Deleted {deleted_count} old education records")

        # Process education data
        education_list = data.get('education', [])
        if not isinstance(education_list, list):
            print(f"[STEP2] WARNING: education is not a list: {type(education_list)}")
            education_list = []

        added_count = 0
        skipped_count = 0
        validation_errors = []

        for idx, edu in enumerate(education_list):
            try:
                # Validate all required fields
                degree = str(edu.get('degree', '')).strip()
                institution = str(edu.get('institution', '')).strip()
                field_of_study = str(edu.get('field_of_study', '')).strip()
                grade = str(edu.get('grade', '')).strip()

                # Validate string lengths to prevent database errors
                if len(degree) > 100:
                    validation_errors.append(f"Education {idx + 1}: Degree name too long (max 100 characters)")
                    skipped_count += 1
                    continue

                if len(institution) > 200:
                    validation_errors.append(f"Education {idx + 1}: Institution name too long (max 200 characters)")
                    skipped_count += 1
                    continue

                if len(field_of_study) > 100:
                    validation_errors.append(f"Education {idx + 1}: Field of study too long (max 100 characters)")
                    skipped_count += 1
                    continue

                if len(grade) > 20:
                    validation_errors.append(f"Education {idx + 1}: Grade too long (max 20 characters)")
                    skipped_count += 1
                    continue

                if not degree or not institution or not field_of_study or not grade:
                    print(f"[STEP2] Skipping education {idx}: missing required fields")
                    validation_errors.append(f"Education {idx + 1}: All fields are required (degree, institution, field of study, grade)")
                    skipped_count += 1
                    continue

                # Parse dates safely using helper function
                start_date = parse_date_safe(edu.get('start_date'))
                end_date = parse_date_safe(edu.get('end_date'))

                # Validate dates are required and parsed successfully
                if not start_date or not end_date:
                    print(f"[STEP2] Skipping education {idx}: invalid dates")
                    print(f"[STEP2]   start_date_raw: {edu.get('start_date')}, end_date_raw: {edu.get('end_date')}")
                    validation_errors.append(f"Education {idx + 1}: Start date and end date are required and must be valid")
                    skipped_count += 1
                    continue

                # Validate date logic
                if start_date > end_date:
                    validation_errors.append(f"Education {idx + 1}: Start date cannot be after end date")
                    skipped_count += 1
                    continue

                print(f"[STEP2] Parsed dates successfully - start: {start_date}, end: {end_date}")

                education = Education(
                    student_profile_id=profile.id,
                    degree=degree,
                    institution=institution,
                    field_of_study=field_of_study,
                    grade=grade,
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(education)
                added_count += 1
                print(f"[STEP2] Added education {idx}: {degree} at {institution}")

            except Exception as edu_error:
                print(f"[STEP2] Error processing education {idx}: {str(edu_error)}")
                validation_errors.append(f"Education {idx + 1}: Invalid data format")
                skipped_count += 1
                continue

        # Commit changes
        db.session.commit()
        print(f"[STEP2] Successfully saved. Added {added_count} education records, skipped {skipped_count}")

        # Return success with warnings if any entries were skipped
        if validation_errors:
            print(f"[STEP2] Validation errors: {validation_errors}")
            return jsonify({
                'success': True,
                'redirect': url_for('student_onboarding_step3'),
                'warnings': validation_errors,
                'added': added_count,
                'skipped': skipped_count
            })

        return jsonify({'success': True, 'redirect': url_for('student_onboarding_step3')})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"[STEP2] ERROR: {str(e)}")
        print(f"[STEP2] Full traceback:\n{error_details}")
        return jsonify({'success': False, 'message': f'Failed to save data: {str(e)}. Please try again.'}), 500


@app.route('/student/onboarding/step3', methods=['GET', 'POST'])
@login_required
def student_onboarding_step3():
    if request.method == 'GET':
        return render_template('student/onboarding_step3.html')

    try:
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            print(f"[STEP3] ERROR: Profile not found for user_id: {current_user.id}")
            return jsonify({'success': False, 'message': 'Profile not found. Please complete Step 1 first or contact admin.'}), 400

        print(f"[STEP3] Found profile ID: {profile.id} for user_id: {current_user.id}")
        data = request.json
        print(f"[STEP3] Received data: {data}")

        # Validate request data
        if not data:
            print(f"[STEP3] ERROR: No data received")
            return jsonify({'success': False, 'message': 'No data received. Please try again.'}), 400

        # Delete existing work experience to avoid duplicates
        deleted_count = WorkExperience.query.filter_by(student_profile_id=profile.id).delete()
        print(f"[STEP3] Deleted {deleted_count} old work experience records")

        # Process experience data
        experience_list = data.get('experience', [])
        if not isinstance(experience_list, list):
            print(f"[STEP3] WARNING: experience is not a list: {type(experience_list)}")
            experience_list = []

        added_count = 0
        skipped_count = 0
        validation_errors = []

        for idx, exp in enumerate(experience_list):
            try:
                # Validate all required fields
                company = str(exp.get('company', '')).strip()
                position = str(exp.get('position', '')).strip()
                description = str(exp.get('description', '')).strip()

                # Validate string lengths to prevent database errors
                if len(company) > 200:
                    validation_errors.append(f"Experience {idx + 1}: Company name too long (max 200 characters)")
                    skipped_count += 1
                    continue

                if len(position) > 100:
                    validation_errors.append(f"Experience {idx + 1}: Position too long (max 100 characters)")
                    skipped_count += 1
                    continue

                if not company or not position or not description:
                    print(f"[STEP3] Skipping experience {idx}: missing required fields")
                    validation_errors.append(f"Experience {idx + 1}: Company, position, and description are required")
                    skipped_count += 1
                    continue

                # Parse dates safely using helper function
                start_date = parse_date_safe(exp.get('start_date'))
                end_date = parse_date_safe(exp.get('end_date'))  # Optional for current jobs

                # Validate start_date is required (end_date is optional for current jobs)
                if not start_date:
                    print(f"[STEP3] Skipping experience {idx}: start_date missing or invalid")
                    print(f"[STEP3]   start_date_raw: {exp.get('start_date')}")
                    validation_errors.append(f"Experience {idx + 1}: Start date is required and must be valid")
                    skipped_count += 1
                    continue

                # Validate date logic if end_date exists
                if end_date and start_date > end_date:
                    validation_errors.append(f"Experience {idx + 1}: Start date cannot be after end date")
                    skipped_count += 1
                    continue

                print(f"[STEP3] Parsed dates successfully - start: {start_date}, end: {end_date}")

                work_exp = WorkExperience(
                    student_profile_id=profile.id,
                    company=company,
                    position=position,
                    description=description,
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(work_exp)
                added_count += 1
                print(f"[STEP3] Added experience {idx}: {position} at {company}")

            except Exception as exp_error:
                print(f"[STEP3] Error processing experience {idx}: {str(exp_error)}")
                validation_errors.append(f"Experience {idx + 1}: Invalid data format")
                skipped_count += 1
                continue

        # Commit changes
        db.session.commit()
        print(f"[STEP3] Successfully saved. Added {added_count} work experience records, skipped {skipped_count}")

        # Return success with warnings if any entries were skipped
        if validation_errors:
            print(f"[STEP3] Validation errors: {validation_errors}")
            return jsonify({
                'success': True,
                'redirect': url_for('student_onboarding_step4'),
                'warnings': validation_errors,
                'added': added_count,
                'skipped': skipped_count
            })

        return jsonify({'success': True, 'redirect': url_for('student_onboarding_step4')})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"[STEP3] ERROR: {str(e)}")
        print(f"[STEP3] Full traceback:\n{error_details}")
        return jsonify({'success': False, 'message': f'Failed to save data: {str(e)}. Please try again.'}), 500


@app.route('/student/onboarding/step4', methods=['GET', 'POST'])
@login_required
def student_onboarding_step4():
    if request.method == 'GET':
        return render_template('student/onboarding_step4.html')

    try:
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            print(f"[STEP4] ERROR: Profile not found for user_id: {current_user.id}")
            return jsonify({'success': False, 'message': 'Profile not found. Please complete Step 1 first or contact admin.'}), 400

        print(f"[STEP4] Found profile ID: {profile.id} for user_id: {current_user.id}")
        data = request.json
        print(f"[STEP4] Received data: {data}")

        # Validate request data
        if not data:
            print(f"[STEP4] ERROR: No data received")
            return jsonify({'success': False, 'message': 'No data received. Please try again.'}), 400

        # Delete existing skills and certifications to avoid duplicates
        deleted_skills = Skill.query.filter_by(student_profile_id=profile.id).delete()
        deleted_certs = Certification.query.filter_by(student_profile_id=profile.id).delete()
        print(f"[STEP4] Deleted {deleted_skills} old skills and {deleted_certs} old certifications")

        # Process skills
        skills_list = data.get('skills', [])
        if not isinstance(skills_list, list):
            print(f"[STEP4] WARNING: skills is not a list: {type(skills_list)}")
            skills_list = []

        added_skills = 0
        skipped_skills = 0
        validation_errors = []

        for idx, skill_data in enumerate(skills_list):
            try:
                skill_name = str(skill_data.get('name', '')).strip()

                # Validate string length
                if len(skill_name) > 100:
                    validation_errors.append(f"Skill {idx + 1}: Name too long (max 100 characters)")
                    skipped_skills += 1
                    continue

                if not skill_name:
                    print(f"[STEP4] Skipping skill {idx}: missing name")
                    skipped_skills += 1
                    continue

                proficiency = str(skill_data.get('proficiency_level', 'intermediate')).strip().lower()
                # Validate proficiency level
                valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
                if proficiency not in valid_levels:
                    proficiency = 'intermediate'
                    print(f"[STEP4] Invalid proficiency level, defaulting to 'intermediate'")

                skill = Skill(
                    student_profile_id=profile.id,
                    name=skill_name,
                    proficiency_level=proficiency
                )
                db.session.add(skill)
                added_skills += 1
                print(f"[STEP4] Added skill {idx}: {skill_name} ({proficiency})")

            except Exception as skill_error:
                print(f"[STEP4] Error processing skill {idx}: {str(skill_error)}")
                validation_errors.append(f"Skill {idx + 1}: Invalid data format")
                skipped_skills += 1
                continue

        # Process certifications
        certifications_list = data.get('certifications', [])
        if not isinstance(certifications_list, list):
            print(f"[STEP4] WARNING: certifications is not a list: {type(certifications_list)}")
            certifications_list = []

        added_certs = 0
        skipped_certs = 0

        for idx, cert_data in enumerate(certifications_list):
            try:
                # Validate all required fields
                cert_name = str(cert_data.get('name', '')).strip()
                issuing_org = str(cert_data.get('issuing_organization', '')).strip()

                # Validate string lengths
                if len(cert_name) > 200:
                    validation_errors.append(f"Certification {idx + 1}: Name too long (max 200 characters)")
                    skipped_certs += 1
                    continue

                if len(issuing_org) > 200:
                    validation_errors.append(f"Certification {idx + 1}: Organization name too long (max 200 characters)")
                    skipped_certs += 1
                    continue

                if not cert_name or not issuing_org:
                    print(f"[STEP4] Skipping certification {idx}: missing name or organization")
                    validation_errors.append(f"Certification {idx + 1}: Name and organization are required")
                    skipped_certs += 1
                    continue

                # Parse date safely using helper function
                issue_date = parse_date_safe(cert_data.get('issue_date'))

                # Validate issue_date is required
                if not issue_date:
                    print(f"[STEP4] Skipping certification {idx}: issue_date missing or invalid")
                    print(f"[STEP4]   issue_date_raw: {cert_data.get('issue_date')}")
                    validation_errors.append(f"Certification {idx + 1}: Issue date is required and must be valid")
                    skipped_certs += 1
                    continue

                print(f"[STEP4] Parsed issue_date successfully: {issue_date}")

                cert = Certification(
                    student_profile_id=profile.id,
                    name=cert_name,
                    issuing_organization=issuing_org,
                    issue_date=issue_date,
                    credential_url=str(cert_data.get('credential_url', '')).strip()
                )
                db.session.add(cert)
                added_certs += 1
                print(f"[STEP4] Added certification {idx}: {cert_name}")

            except Exception as cert_error:
                print(f"[STEP4] Error processing certification {idx}: {str(cert_error)}")
                validation_errors.append(f"Certification {idx + 1}: Invalid data format")
                skipped_certs += 1
                continue

        # Commit changes
        db.session.commit()
        print(f"[STEP4] Successfully saved. Added {added_skills} skills and {added_certs} certifications")
        print(f"[STEP4] Skipped {skipped_skills} skills and {skipped_certs} certifications")

        # Return success with warnings if any entries were skipped
        if validation_errors:
            print(f"[STEP4] Validation errors: {validation_errors}")
            return jsonify({
                'success': True,
                'redirect': url_for('student_onboarding_step5'),
                'warnings': validation_errors,
                'added_skills': added_skills,
                'added_certs': added_certs,
                'skipped_skills': skipped_skills,
                'skipped_certs': skipped_certs
            })

        return jsonify({'success': True, 'redirect': url_for('student_onboarding_step5')})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"[STEP4] ERROR: {str(e)}")
        print(f"[STEP4] Full traceback:\n{error_details}")
        return jsonify({'success': False, 'message': f'Failed to save data: {str(e)}. Please try again.'}), 500


@app.route('/student/onboarding/step5', methods=['GET', 'POST'])
@login_required
def student_onboarding_step5():
    if request.method == 'GET':
        return render_template('student/onboarding_step5.html')

    try:
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            print(f"[STEP5] ERROR: Profile not found for user_id: {current_user.id}")
            return jsonify({'success': False, 'message': 'Profile not found. Please complete Step 1 first or contact admin.'}), 400

        print(f"[STEP5] Found profile ID: {profile.id} for user_id: {current_user.id}")

        # Handle profile photo upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename:
                try:
                    # Get file extension safely
                    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                    filename = secure_filename(f"{current_user.id}_profile_{uuid.uuid4()}.{file_ext}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    profile.profile_photo = filename
                    print(f"[STEP5] Saved profile photo: {filename}")
                except Exception as e:
                    print(f"[STEP5] Error saving profile photo: {e}")

        # Handle resume upload
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename:
                try:
                    # Get file extension safely
                    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'pdf'
                    filename = secure_filename(f"{current_user.id}_resume_{uuid.uuid4()}.{file_ext}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    profile.resume_filename = filename
                    print(f"[STEP5] Saved resume: {filename}")
                except Exception as e:
                    print(f"[STEP5] Error saving resume: {e}")

        profile.onboarding_complete = True
        db.session.commit()
        print(f"[STEP5] Onboarding completed for user_id: {current_user.id}")

        return jsonify({'success': True, 'redirect': url_for('student_dashboard')})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"[STEP5] ERROR: {str(e)}")
        print(f"[STEP5] Full traceback:\n{error_details}")
        return jsonify({'success': False, 'message': 'Failed to complete onboarding. Please try again.'}), 500


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    profile = get_or_create_student_profile(current_user.id)
    if not profile.onboarding_complete:
        return redirect(url_for('student_onboarding_step1'))
    
    applications = Application.query.filter_by(student_profile_id=profile.id).order_by(Application.applied_at.desc()).limit(5).all()
    return render_template('student/dashboard.html', profile=profile, applications=applications)


@app.route('/student/profile/<slug>')
def student_profile_view(slug):
    # Find user by matching their name slug
    users = User.query.all()
    profile = None

    for user in users:
        if create_slug(user.full_name) == slug:
            profile = StudentProfile.query.filter_by(user_id=user.id).first()
            if profile:
                break

    if not profile:
        abort(404)

    return render_template('student/profile.html', profile=profile)


@app.route('/student/profile/edit', methods=['GET', 'POST'])
@login_required
def student_profile_edit():
    profile = get_or_create_student_profile(current_user.id)
    if not profile.onboarding_complete:
        return redirect(url_for('student_onboarding_step1'))

    if request.method == 'GET':
        return render_template('student/edit_profile.html', profile=profile)

    # Update personal information including social links
    profile.phone = request.json.get('phone', profile.phone)
    profile.bio = request.json.get('bio', profile.bio)
    profile.location = request.json.get('location', profile.location)
    profile.linkedin_url = request.json.get('linkedin_url', profile.linkedin_url)
    profile.github_url = request.json.get('github_url', profile.github_url)
    profile.portfolio_url = request.json.get('portfolio_url', profile.portfolio_url)
    profile.leetcode_url = request.json.get('leetcode_url', profile.leetcode_url)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Profile updated successfully'})


# Education CRUD Routes
@app.route('/student/profile/education', methods=['POST'])
@login_required
def add_education():
    profile = get_or_create_student_profile(current_user.id)

    try:
        education = Education(
            student_profile_id=profile.id,
            degree=request.json.get('degree'),
            institution=request.json.get('institution'),
            field_of_study=request.json.get('field_of_study'),
            start_date=datetime.strptime(request.json.get('start_date'), '%Y-%m-%d').date() if request.json.get('start_date') else None,
            end_date=datetime.strptime(request.json.get('end_date'), '%Y-%m-%d').date() if request.json.get('end_date') else None,
            grade=request.json.get('grade')
        )
        db.session.add(education)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Education added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/education/<int:id>', methods=['PUT'])
@login_required
def update_education(id):
    profile = get_or_create_student_profile(current_user.id)
    education = db.get_or_404(Education, id)

    # Verify ownership
    if education.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        education.degree = request.json.get('degree', education.degree)
        education.institution = request.json.get('institution', education.institution)
        education.field_of_study = request.json.get('field_of_study', education.field_of_study)
        education.grade = request.json.get('grade', education.grade)

        if request.json.get('start_date'):
            education.start_date = datetime.strptime(request.json.get('start_date'), '%Y-%m-%d').date()
        if request.json.get('end_date'):
            education.end_date = datetime.strptime(request.json.get('end_date'), '%Y-%m-%d').date()

        db.session.commit()
        return jsonify({'success': True, 'message': 'Education updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/education/<int:id>', methods=['DELETE'])
@login_required
def delete_education(id):
    profile = get_or_create_student_profile(current_user.id)
    education = db.get_or_404(Education, id)

    # Verify ownership
    if education.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        db.session.delete(education)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Education deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


# Work Experience CRUD Routes
@app.route('/student/profile/experience', methods=['POST'])
@login_required
def add_experience():
    profile = get_or_create_student_profile(current_user.id)

    try:
        experience = WorkExperience(
            student_profile_id=profile.id,
            position=request.json.get('position'),
            company=request.json.get('company'),
            description=request.json.get('description'),
            start_date=datetime.strptime(request.json.get('start_date'), '%Y-%m-%d').date() if request.json.get('start_date') else None,
            end_date=datetime.strptime(request.json.get('end_date'), '%Y-%m-%d').date() if request.json.get('end_date') else None
        )
        db.session.add(experience)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Work experience added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/experience/<int:id>', methods=['PUT'])
@login_required
def update_experience(id):
    profile = get_or_create_student_profile(current_user.id)
    experience = db.get_or_404(WorkExperience, id)

    # Verify ownership
    if experience.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        experience.position = request.json.get('position', experience.position)
        experience.company = request.json.get('company', experience.company)
        experience.description = request.json.get('description', experience.description)

        if request.json.get('start_date'):
            experience.start_date = datetime.strptime(request.json.get('start_date'), '%Y-%m-%d').date()
        if request.json.get('end_date'):
            experience.end_date = datetime.strptime(request.json.get('end_date'), '%Y-%m-%d').date()

        db.session.commit()
        return jsonify({'success': True, 'message': 'Work experience updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/experience/<int:id>', methods=['DELETE'])
@login_required
def delete_experience(id):
    profile = get_or_create_student_profile(current_user.id)
    experience = db.get_or_404(WorkExperience, id)

    # Verify ownership
    if experience.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        db.session.delete(experience)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Work experience deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


# Skills CRUD Routes
@app.route('/student/profile/skill', methods=['POST'])
@login_required
def add_skill():
    profile = get_or_create_student_profile(current_user.id)

    try:
        skill = Skill(
            student_profile_id=profile.id,
            skill_name=request.json.get('skill_name'),
            proficiency_level=request.json.get('proficiency_level', 'Intermediate')
        )
        db.session.add(skill)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Skill added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/skill/<int:id>', methods=['DELETE'])
@login_required
def delete_skill(id):
    profile = get_or_create_student_profile(current_user.id)
    skill = db.get_or_404(Skill, id)

    # Verify ownership
    if skill.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        db.session.delete(skill)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Skill deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


# Certifications CRUD Routes
@app.route('/student/profile/certification', methods=['POST'])
@login_required
def add_certification():
    profile = get_or_create_student_profile(current_user.id)

    try:
        certification = Certification(
            student_profile_id=profile.id,
            certification_name=request.json.get('certification_name'),
            issuing_organization=request.json.get('issuing_organization'),
            issue_date=datetime.strptime(request.json.get('issue_date'), '%Y-%m-%d').date() if request.json.get('issue_date') else None,
            credential_url=request.json.get('credential_url')
        )
        db.session.add(certification)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Certification added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/certification/<int:id>', methods=['PUT'])
@login_required
def update_certification(id):
    profile = get_or_create_student_profile(current_user.id)
    certification = db.get_or_404(Certification, id)

    # Verify ownership
    if certification.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        certification.certification_name = request.json.get('certification_name', certification.certification_name)
        certification.issuing_organization = request.json.get('issuing_organization', certification.issuing_organization)
        certification.credential_url = request.json.get('credential_url', certification.credential_url)

        if request.json.get('issue_date'):
            certification.issue_date = datetime.strptime(request.json.get('issue_date'), '%Y-%m-%d').date()

        db.session.commit()
        return jsonify({'success': True, 'message': 'Certification updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/profile/certification/<int:id>', methods=['DELETE'])
@login_required
def delete_certification(id):
    profile = get_or_create_student_profile(current_user.id)
    certification = db.get_or_404(Certification, id)

    # Verify ownership
    if certification.student_profile_id != profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        db.session.delete(certification)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Certification deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/student/internships')
@login_required
def student_internships():
    profile = get_or_create_student_profile(current_user.id)
    internships = Internship.query.filter_by(active=True).order_by(Internship.created_at.desc()).all()
    return render_template('student/internships.html', internships=internships)


@app.route('/student/internships/<int:id>')
@login_required
def student_internship_detail(id):
    profile = get_or_create_student_profile(current_user.id)
    internship = db.get_or_404(Internship, id)
    internship.view_count += 1
    db.session.commit()
    
    applied = Application.query.filter_by(student_profile_id=profile.id, internship_id=id).first() is not None
    
    return render_template('student/internship_detail.html', internship=internship, applied=applied)


@app.route('/student/internships/<int:id>/apply', methods=['POST'])
@login_required
def student_apply_internship(id):
    profile = get_or_create_student_profile(current_user.id)
    if not profile.onboarding_complete:
        return jsonify({'success': False, 'message': 'Complete your profile first'}), 400
    
    internship = db.get_or_404(Internship, id)
    existing = Application.query.filter_by(student_profile_id=profile.id, internship_id=id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already applied'}), 400
    
    application = Application(
        student_profile_id=profile.id,
        internship_id=id,
        status='pending'
    )
    db.session.add(application)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Application submitted successfully'})


@app.route('/student/applications')
@login_required
def student_applications():
    profile = get_or_create_student_profile(current_user.id)
    if not profile.onboarding_complete:
        return redirect(url_for('student_onboarding_step1'))
    
    applications = Application.query.filter_by(student_profile_id=profile.id).order_by(Application.applied_at.desc()).all()
    return render_template('student/applications.html', applications=applications)


def company_required(f):
    def decorated_function(*args, **kwargs):
        if 'company_id' not in session:
            return redirect(url_for('company_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@app.route('/company/dashboard')
@company_required
def company_dashboard():
    company = db.session.get(Company, session['company_id'])
    internships = Internship.query.filter_by(posted_by_company_id=company.id).all()
    total_applications = db.session.query(Application).join(Internship).filter(Internship.posted_by_company_id == company.id).count()
    
    return render_template('company/dashboard.html', company=company, internships=internships, total_applications=total_applications)


@app.route('/company/post-job', methods=['GET', 'POST'])
@company_required
def company_post_job():
    if request.method == 'GET':
        return render_template('company/post_job.html')
    
    company = db.session.get(Company, session['company_id'])
    data = request.json
    
    internship = Internship(
        title=data['title'],
        description=data['description'],
        requirements=data.get('requirements'),
        salary_min=data.get('salary_min'),
        salary_max=data.get('salary_max'),
        location=data.get('location'),
        posted_by_company_id=company.id,
        admin_managed=data.get('admin_managed', False),
        active=True
    )
    db.session.add(internship)
    db.session.commit()
    
    return jsonify({'success': True, 'redirect': url_for('company_dashboard')})


@app.route('/company/jobs')
@company_required
def company_jobs():
    company = db.session.get(Company, session['company_id'])
    internships = Internship.query.filter_by(posted_by_company_id=company.id).order_by(Internship.created_at.desc()).all()
    return render_template('company/jobs.html', internships=internships)


@app.route('/company/jobs/<int:job_id>/applicants')
@company_required
def company_job_applicants(job_id):
    company = db.session.get(Company, session['company_id'])
    internship = db.get_or_404(Internship, job_id)

    # Verify that this job belongs to the company
    if internship.posted_by_company_id != company.id:
        abort(403)

    applications = Application.query.filter_by(internship_id=job_id).order_by(Application.applied_at.desc()).all()
    return render_template('company/job_applicants.html', internship=internship, applications=applications)


@app.route('/company/applications')
@company_required
def company_applications():
    company = db.session.get(Company, session['company_id'])
    applications = db.session.query(Application).join(Internship).filter(Internship.posted_by_company_id == company.id).order_by(Application.applied_at.desc()).all()
    return render_template('company/applications.html', applications=applications)


@app.route('/company/profile/edit', methods=['GET', 'POST'])
@company_required
def company_profile_edit():
    company = db.session.get(Company, session['company_id'])

    if request.method == 'GET':
        return render_template('company/edit_profile.html', company=company)

    # Handle form data (not JSON anymore due to file upload)
    company.company_name = request.form.get('company_name', company.company_name)
    company.website = request.form.get('website', company.website)
    company.description = request.form.get('description', company.description)
    company.industry = request.form.get('industry', company.industry)
    company.company_size = request.form.get('company_size', company.company_size)
    company.mobile = request.form.get('mobile', company.mobile)
    company.contact_person_name = request.form.get('contact_person_name', company.contact_person_name)
    company.contact_person_position = request.form.get('contact_person_position', company.contact_person_position)

    # Handle logo upload
    if 'logo' in request.files:
        logo_file = request.files['logo']
        if logo_file and logo_file.filename:
            # Validate file extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            file_ext = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''

            if file_ext in allowed_extensions:
                filename = secure_filename(f"company_logo_{company.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}")
                logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo_file.save(logo_path)
                company.logo_url = filename
            else:
                return jsonify({'success': False, 'message': 'Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.'}), 400

    db.session.commit()

    return jsonify({'success': True, 'redirect': url_for('company_dashboard')})


@app.route('/admin/students')
@login_required
def admin_students():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    profiles = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    return render_template('admin/students.html', profiles=profiles)


@app.route('/admin/students/<int:id>')
@login_required
def admin_student_detail(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    profile = db.get_or_404(StudentProfile, id)
    
    audit = AuditLog(
        admin_user_id=current_user.id,
        action=f"Viewed student profile: {profile.user.full_name}",
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return render_template('admin/student_detail.html', profile=profile)


@app.route('/admin/companies')
@login_required
def admin_companies():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    companies = Company.query.order_by(Company.created_at.desc()).all()
    return render_template('admin/companies.html', companies=companies)


@app.route('/admin/companies/<int:id>')
@login_required
def admin_company_detail(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))

    company = db.get_or_404(Company, id)

    # Get all internships with their applications and student profiles
    internships = Internship.query.filter_by(posted_by_company_id=id).order_by(Internship.created_at.desc()).all()

    # For each internship, get applications with student profiles and user data
    for internship in internships:
        internship.application_list = db.session.query(Application, StudentProfile, User).join(
            StudentProfile, Application.student_profile_id == StudentProfile.id
        ).join(
            User, StudentProfile.user_id == User.id
        ).filter(
            Application.internship_id == internship.id
        ).order_by(Application.applied_at.desc()).all()

    audit = AuditLog(
        admin_user_id=current_user.id,
        action=f"Viewed company profile: {company.company_name}",
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

    return render_template('admin/company_detail.html', company=company, internships=internships)


@app.route('/admin/jobs/<int:job_id>/applicants')
@login_required
def admin_job_applicants(job_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))

    internship = db.get_or_404(Internship, job_id)
    applications = Application.query.filter_by(internship_id=job_id).order_by(Application.applied_at.desc()).all()

    audit = AuditLog(
        admin_user_id=current_user.id,
        action=f"Viewed applicants for job: {internship.title}",
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

    return render_template('admin/job_applicants.html', internship=internship, applications=applications)


@app.route('/admin/internships')
@login_required
def admin_internships():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    internships = Internship.query.order_by(Internship.created_at.desc()).all()
    return render_template('admin/internships.html', internships=internships)


@app.route('/admin/internships/create', methods=['GET', 'POST'])
@login_required
def admin_create_internship():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'GET':
        return render_template('admin/create_internship.html')
    
    data = request.json
    internship = Internship(
        title=data['title'],
        description=data['description'],
        requirements=data.get('requirements'),
        salary_min=data.get('salary_min'),
        salary_max=data.get('salary_max'),
        location=data.get('location'),
        admin_managed=True,
        active=True
    )
    db.session.add(internship)
    
    audit = AuditLog(
        admin_user_id=current_user.id,
        action=f"Created internship: {data['title']}",
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({'success': True, 'redirect': url_for('admin_internships')})


@app.route('/admin/applications')
@login_required
def admin_applications():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    applications = Application.query.order_by(Application.applied_at.desc()).all()
    return render_template('admin/applications.html', applications=applications)


@app.route('/admin/audit-logs')
@login_required
def admin_audit_logs():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)


# Super Admin Routes for Account Management
@app.route('/admin/manage-accounts')
@login_required
def admin_manage_accounts():
    if not current_user.is_admin or current_user.admin_role != 'super_admin':
        flash('Super admin access required', 'danger')
        return redirect(url_for('index'))

    companies = Company.query.order_by(Company.created_at.desc()).all()
    admins = User.query.filter_by(is_admin=True).order_by(User.created_at.desc()).all()

    return render_template('admin/manage_accounts.html', companies=companies, admins=admins)


@app.route('/admin/create-company', methods=['GET', 'POST'])
@login_required
def admin_create_company():
    if not current_user.is_admin or current_user.admin_role != 'super_admin':
        return jsonify({'error': 'Super admin access required'}), 403

    if request.method == 'POST':
        try:
            data = request.json

            # Check if company email already exists
            existing = Company.query.filter_by(email=data.get('email')).first()
            if existing:
                return jsonify({'success': False, 'message': 'Company with this email already exists'}), 400

            company = Company(
                email=data.get('email'),
                company_name=data.get('company_name'),
                website=data.get('website'),
                description=data.get('description'),
                industry=data.get('industry'),
                company_size=data.get('company_size'),
                is_verified=True  # Auto-verify admin-created companies
            )
            company.set_password(data.get('password'))

            db.session.add(company)
            db.session.commit()

            # Log the action
            log = AuditLog(
                admin_user_id=current_user.id,
                action=f'Created company account: {company.company_name} ({company.email})',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

            return jsonify({'success': True, 'message': 'Company created successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('admin/create_company.html')


@app.route('/admin/create-admin', methods=['GET', 'POST'])
@login_required
def admin_create_admin():
    if not current_user.is_admin or current_user.admin_role != 'super_admin':
        return jsonify({'error': 'Super admin access required'}), 403

    if request.method == 'POST':
        try:
            data = request.json

            # Check if user email already exists
            existing = User.query.filter_by(email=data.get('email')).first()
            if existing:
                return jsonify({'success': False, 'message': 'User with this email already exists'}), 400

            admin_role = data.get('admin_role')
            if admin_role not in ['super_admin', 'normal_admin', 'intern_admin']:
                return jsonify({'success': False, 'message': 'Invalid admin role'}), 400

            admin = User(
                email=data.get('email'),
                full_name=data.get('full_name'),
                department='Admin',
                year=1,
                college=data.get('college', 'Admin College'),
                is_verified=True,
                is_admin=True,
                admin_role=admin_role
            )
            admin.set_password(data.get('password'))

            db.session.add(admin)
            db.session.commit()

            # Log the action
            log = AuditLog(
                admin_user_id=current_user.id,
                action=f'Created {admin_role} account: {admin.full_name} ({admin.email})',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

            return jsonify({'success': True, 'message': f'{admin_role.replace("_", " ").title()} created successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('admin/create_admin.html')


# Enhanced student detail page with application history
@app.route('/admin/students/<int:id>/dashboard')
@login_required
def admin_student_dashboard(id):
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('index'))

    profile = db.get_or_404(StudentProfile, id)
    applications = Application.query.filter_by(student_profile_id=id).order_by(Application.applied_at.desc()).all()

    # Calculate statistics
    total_applications = len(applications)
    pending = sum(1 for app in applications if app.status == 'pending')
    shortlisted = sum(1 for app in applications if app.status == 'shortlisted')
    rejected = sum(1 for app in applications if app.status == 'rejected')
    accepted = sum(1 for app in applications if app.status == 'accepted')

    # Log the action
    log = AuditLog(
        admin_user_id=current_user.id,
        action=f'Viewed comprehensive dashboard for student: {profile.user.full_name} (ID: {profile.user.id})',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return render_template('admin/student_dashboard.html',
                          profile=profile,
                          applications=applications,
                          stats={
                              'total': total_applications,
                              'pending': pending,
                              'shortlisted': shortlisted,
                              'rejected': rejected,
                              'accepted': accepted
                          })


# Application Status Management Routes
@app.route('/admin/application/<int:application_id>/update-status', methods=['POST'])
@login_required
def admin_update_application_status(application_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    try:
        data = request.json
        new_status = data.get('status')
        notes = data.get('notes', '')

        # Validate status
        valid_statuses = ['pending', 'shortlisted', 'accepted', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400

        application = db.get_or_404(Application, application_id)
        old_status = application.status

        # Update application
        application.status = new_status
        if notes:
            application.notes = notes
        application.updated_at = datetime.utcnow()

        db.session.commit()

        # Log the action
        log = AuditLog(
            admin_user_id=current_user.id,
            action=f'Updated application #{application_id} status from "{old_status}" to "{new_status}" for student: {application.student_profile.user.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Application status updated to {new_status}',
            'new_status': new_status
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Student Approval/Feature Management
@app.route('/admin/students/<int:id>/toggle-approval', methods=['POST'])
@login_required
def admin_toggle_student_approval(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    try:
        profile = db.get_or_404(StudentProfile, id)
        profile.approved_by_admin = not profile.approved_by_admin
        db.session.commit()

        # Log the action
        log = AuditLog(
            admin_user_id=current_user.id,
            action=f'{"Approved" if profile.approved_by_admin else "Unapproved"} student profile: {profile.user.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'approved': profile.approved_by_admin,
            'message': f'Student {"approved" if profile.approved_by_admin else "unapproved"} successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/students/<int:id>/toggle-feature', methods=['POST'])
@login_required
def admin_toggle_student_feature(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    try:
        profile = db.get_or_404(StudentProfile, id)
        profile.featured = not profile.featured
        db.session.commit()

        # Log the action
        log = AuditLog(
            admin_user_id=current_user.id,
            action=f'{"Featured" if profile.featured else "Unfeatured"} student profile: {profile.user.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'featured': profile.featured,
            'message': f'Student {"featured" if profile.featured else "unfeatured"} successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/company/application/<int:application_id>/update-status', methods=['POST'])
@company_required
def company_update_application_status(application_id):
    try:
        company = db.session.get(Company, session['company_id'])
        data = request.json
        new_status = data.get('status')
        notes = data.get('notes', '')

        # Validate status
        valid_statuses = ['pending', 'shortlisted', 'accepted', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400

        application = db.get_or_404(Application, application_id)

        # Verify company owns this internship
        if application.internship.posted_by_company_id != company.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        old_status = application.status

        # Update application
        application.status = new_status
        if notes:
            application.notes = notes
        application.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Application status updated to {new_status}',
            'new_status': new_status
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== LISTING STATUS & ARCHIVE API ENDPOINTS ====================

@app.route('/api/listing/<int:listing_id>/status')
@login_required
def get_listing_status(listing_id):
    """Get listing sold and archived status"""
    try:
        print(f"\n[STATUS CHECK] Listing ID: {listing_id}")

        listing = Listing.query.get(listing_id)
        print(f"[STATUS CHECK] Listing exists: {listing is not None}")

        # Check if listing has been sold (even if listing is deleted)
        sold_item = SoldItem.query.filter_by(listing_id=listing_id).first()
        print(f"[STATUS CHECK] Sold item exists: {sold_item is not None}")

        # Check if messages for this listing are archived
        archived_message = MessageThread.query.filter_by(
            listing_id=listing_id,
            is_archived=True
        ).first()
        print(f"[STATUS CHECK] Archived message with listing_id: {archived_message is not None}")

        # IMPORTANT: Also check for archived messages where listing_id is NULL
        # (This happens when listing is deleted and FK constraint sets to NULL)
        archived_message_null = MessageThread.query.filter_by(
            listing_id=None,
            is_archived=True
        ).filter(
            db.or_(
                MessageThread.sender_id == current_user.id,
                MessageThread.receiver_id == current_user.id
            )
        ).first()
        print(f"[STATUS CHECK] Archived message with NULL listing_id: {archived_message_null is not None}")

        # Check if there are ANY messages for this listing (even if not archived)
        any_message = MessageThread.query.filter_by(listing_id=listing_id).first()
        print(f"[STATUS CHECK] Any message with listing_id: {any_message is not None}")
        if any_message:
            print(f"[STATUS CHECK] Message is_archived value: {any_message.is_archived}")

        # If no listing and no sold item and no messages, return 404
        if not listing and not sold_item and not any_message and not archived_message_null:
            print(f"[STATUS CHECK] Returning 404 - no data found")
            return jsonify({'error': 'Listing not found'}), 404

        # If listing is deleted but there are messages (even with NULL listing_id), treat it as sold
        is_sold = sold_item is not None or not listing or archived_message_null is not None
        is_archived = archived_message is not None or archived_message_null is not None

        print(f"[STATUS CHECK] Returning - is_sold: {is_sold}, is_archived: {is_archived}")

        return jsonify({
            'success': True,
            'is_sold': is_sold,
            'is_archived': is_archived
        })
    except Exception as e:
        print(f"[STATUS CHECK] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/messages/archive', methods=['POST'])
@login_required
def archive_messages():
    """Archive all messages for a specific listing and user"""
    try:
        data = request.json
        listing_id = data.get('listing_id')
        other_user_id = data.get('user_id')

        if not listing_id:
            return jsonify({'success': False, 'error': 'Listing ID required'}), 400

        # Archive all messages between current user and the other user for this listing
        MessageThread.query.filter(
            MessageThread.listing_id == listing_id,
            db.or_(
                db.and_(
                    MessageThread.sender_id == current_user.id,
                    MessageThread.receiver_id == other_user_id
                ),
                db.and_(
                    MessageThread.sender_id == other_user_id,
                    MessageThread.receiver_id == current_user.id
                )
            )
        ).update({'is_archived': True})

        db.session.commit()

        return jsonify({'success': True, 'message': 'Messages archived successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== NOTIFICATION API ENDPOINTS ====================

@app.route('/api/notifications/unread')
@login_required
def get_unread_notifications():
    """Get unread notifications for current user"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Notification.created_at.desc()).all()

        return jsonify({
            'success': True,
            'count': len(notifications),
            'notifications': [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'listing_id': n.listing_id,
                'sender_id': n.sender_id,
                'sender_name': n.sender.full_name if n.sender else None,
                'action_url': n.action_url,
                'created_at': n.created_at.isoformat(),
                'listing_title': n.listing.title if n.listing else None
            } for n in notifications]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()

        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404

        notification.is_read = True
        current_user.unread_notifications = max(0, current_user.unread_notifications - 1)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Notification marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})

        current_user.unread_notifications = 0
        db.session.commit()

        return jsonify({'success': True, 'message': 'All notifications marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/notifications')
@login_required
def notifications_page():
    """Render notifications page"""
    return render_template('notifications.html')


@app.route('/api/notifications/all')
@login_required
def get_all_notifications():
    """Get all notifications for current user (for notifications page)"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.is_read.asc(), Notification.created_at.desc()).all()

        return jsonify({
            'success': True,
            'notifications': [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'listing_id': n.listing_id,
                'sender_id': n.sender_id,
                'sender_name': n.sender.full_name if n.sender else None,
                'action_url': n.action_url,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'listing_title': n.listing.title if n.listing else None
            } for n in notifications]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


with app.app_context():
    db.create_all()

    # Auto-migration: Add new columns if they don't exist
    try:
        with db.engine.connect() as conn:
            # Add sender_id to notifications table
            result = conn.execute(text("SELECT COUNT(*) FROM pragma_table_info('notifications') WHERE name='sender_id'"))
            if result.scalar() == 0:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN sender_id INTEGER"))
                conn.commit()
                print("[✓] Added 'sender_id' column to notifications")

            # Add is_read to notifications table
            result = conn.execute(text("SELECT COUNT(*) FROM pragma_table_info('notifications') WHERE name='is_read'"))
            if result.scalar() == 0:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN is_read BOOLEAN DEFAULT 0"))
                conn.commit()
                print("[✓] Added 'is_read' column to notifications")

            # Add action_url to notifications table
            result = conn.execute(text("SELECT COUNT(*) FROM pragma_table_info('notifications') WHERE name='action_url'"))
            if result.scalar() == 0:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN action_url TEXT"))
                conn.commit()
                print("[✓] Added 'action_url' column to notifications")
    except Exception as e:
        print(f"[!] Migration error: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        create_admin_user()
    app.run(host="0.0.0.0", port=80,debug=True)
