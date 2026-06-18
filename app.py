"""
وضيفة DZ | Wadifa DZ
منصة التوظيف الجزائرية الأولى
Production-ready Flask Application
"""
import os
import logging
from datetime import datetime
from functools import wraps

import bleach
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, jsonify, Response, g)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import Index

# ─── LOGGING ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('wadifa-dz')

# ─── APP FACTORY ──────────────────────────────────────────
app = Flask(__name__)

# Load config
env = os.environ.get('FLASK_ENV', 'production')
from config import config as app_config
try:
    app.config.from_object(app_config.get(env, app_config['default']))
except ValueError as e:
    # Fallback for Railway — use env directly
    app.secret_key = os.environ.get('SECRET_KEY', 'wadifa-dz-fallback-2024')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wadifa-dz.db')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://web-production-dbe18.up.railway.app')

# ─── EXTENSIONS ───────────────────────────────────────────
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ─── CONSTANTS ────────────────────────────────────────────
WILAYAS = [
    'أدرار','الشلف','الأغواط','أم البواقي','باتنة','بجاية','بسكرة','بشار',
    'البليدة','البويرة','تمنراست','تبسة','تلمسان','تيارت','تيزي وزو','الجزائر',
    'الجلفة','جيجل','سطيف','سعيدة','سكيكدة','سيدي بلعباس','عنابة','قالمة',
    'قسنطينة','المدية','مستغانم','المسيلة','معسكر','ورقلة','وهران','البيض',
    'إليزي','برج بوعريريج','بومرداس','الطارف','تندوف','تيسمسيلت','الوادي',
    'خنشلة','سوق أهراس','تيبازة','ميلة','عين الدفلى','النعامة','عين تموشنت',
    'غرداية','غليزان'
]
CATEGORIES = [
    'تكنولوجيا','هندسة','طب وصحة','تسويق','مالية ومحاسبة',
    'تعليم','نفط وغاز','بناء','إدارة أعمال','أخرى'
]
JOB_TYPES = ['دوام كامل','دوام جزئي','عن بعد','عقد']

# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'user'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='seeker', index=True)
    full_name     = db.Column(db.String(100))
    phone         = db.Column(db.String(20))
    wilaya        = db.Column(db.String(50))
    is_active     = db.Column(db.Boolean, default=True, index=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    company       = db.relationship('Company', backref='user', uselist=False)
    applications  = db.relationship('Application', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    __tablename__ = 'company'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    sector      = db.Column(db.String(50))
    wilaya      = db.Column(db.String(50), index=True)
    size        = db.Column(db.String(30))
    website     = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    jobs        = db.relationship('Job', backref='company', lazy='dynamic')


class Job(db.Model):
    __tablename__ = 'job'
    id           = db.Column(db.Integer, primary_key=True)
    company_id   = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    title        = db.Column(db.String(150), nullable=False)
    category     = db.Column(db.String(50), index=True)
    job_type     = db.Column(db.String(30), index=True)
    wilaya       = db.Column(db.String(50), index=True)
    salary_min   = db.Column(db.Integer)
    salary_max   = db.Column(db.Integer)
    description  = db.Column(db.Text)
    requirements = db.Column(db.Text)
    benefits     = db.Column(db.Text)
    is_active    = db.Column(db.Boolean, default=True, index=True)
    is_featured  = db.Column(db.Boolean, default=False, index=True)
    is_approved  = db.Column(db.Boolean, default=True, index=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    applications = db.relationship('Application', backref='job', lazy='dynamic')


class Application(db.Model):
    __tablename__ = 'application'
    id           = db.Column(db.Integer, primary_key=True)
    job_id       = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    cover_letter = db.Column(db.Text)
    cv_filename  = db.Column(db.String(200))
    status       = db.Column(db.String(20), default='new', index=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('job_id', 'user_id', name='unique_application'),
    )


class Talent(db.Model):
    __tablename__ = 'talent'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    category   = db.Column(db.String(50), index=True)
    wilaya     = db.Column(db.String(50), index=True)
    experience = db.Column(db.String(30))
    bio        = db.Column(db.Text)
    skills     = db.Column(db.String(200))
    available  = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='talent_profile')

# ─── HELPERS ──────────────────────────────────────────────

def sanitize(text, max_length=None):
    """Sanitize user input to prevent XSS."""
    if not text:
        return ''
    cleaned = bleach.clean(str(text), tags=[], strip=True).strip()
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def allowed_file(filename):
    ext = {'pdf', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ext


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'company':
            flash('هذه الصفحة للشركات فقط', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            logger.warning(f"Unauthorized admin access attempt from {request.remote_addr}")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── SECURITY HEADERS ─────────────────────────────────────

@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    return response

# ─── ERROR HANDLERS ───────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}", exc_info=True)
    return render_template('500.html'), 500

@app.errorhandler(429)
def rate_limit_handler(e):
    flash('طلبات كثيرة جداً، حاول مجدداً بعد قليل', 'error')
    return redirect(url_for('login')), 429

# ─── PUBLIC ROUTES ────────────────────────────────────────

@app.route('/')
def index():
    featured = (Job.query
        .filter_by(is_active=True, is_featured=True, is_approved=True)
        .order_by(Job.created_at.desc())
        .limit(6).all())
    latest = (Job.query
        .filter_by(is_active=True, is_approved=True)
        .order_by(Job.created_at.desc())
        .limit(8).all())
    total_jobs = Job.query.filter_by(is_active=True, is_approved=True).count()
    total_cos  = Company.query.filter_by(is_approved=True).count()
    total_apps = Application.query.count()
    return render_template('index.html',
        featured=featured, latest=latest,
        total_jobs=total_jobs, total_cos=total_cos, total_apps=total_apps,
        wilayas=WILAYAS, categories=CATEGORIES)


@app.route('/jobs')
def jobs():
    q      = sanitize(request.args.get('q', ''), 100)
    wilaya = sanitize(request.args.get('wilaya', ''), 50)
    cat    = sanitize(request.args.get('cat', ''), 50)
    jtype  = sanitize(request.args.get('type', ''), 30)
    page   = request.args.get('page', 1, type=int)

    query = Job.query.filter_by(is_active=True, is_approved=True)
    if q:      query = query.filter(Job.title.ilike(f'%{q}%'))
    if wilaya: query = query.filter_by(wilaya=wilaya)
    if cat:    query = query.filter_by(category=cat)
    if jtype:  query = query.filter_by(job_type=jtype)

    jobs_list = query.order_by(Job.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs_list,
        wilayas=WILAYAS, categories=CATEGORIES, job_types=JOB_TYPES,
        q=q, wilaya=wilaya, cat=cat, jtype=jtype)


@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    already_applied = False
    if 'user_id' in session:
        already_applied = Application.query.filter_by(
            job_id=job_id, user_id=session['user_id']).first() is not None
    return render_template('job_detail.html', job=job, already_applied=already_applied)


@app.route('/job/<int:job_id>/apply', methods=['POST'])
@login_required
def apply(job_id):
    if session.get('role') != 'seeker':
        flash('الشركات لا يمكنها التقديم على الوظائف', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    if Application.query.filter_by(job_id=job_id, user_id=session['user_id']).first():
        flash('لقد قدّمت على هذه الوظيفة مسبقاً', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    cover_letter = sanitize(request.form.get('cover_letter', ''), 2000)
    app_obj = Application(
        job_id=job_id,
        user_id=session['user_id'],
        cover_letter=cover_letter,
    )
    db.session.add(app_obj)
    db.session.commit()
    logger.info(f"New application: user={session['user_id']} job={job_id}")
    flash('تم إرسال طلبك بنجاح ✅ سيتواصل معك صاحب العمل قريباً', 'success')
    return redirect(url_for('job_detail', job_id=job_id))

# ─── AUTH ─────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def register():
    if request.method == 'POST':
        email    = sanitize(request.form.get('email', ''), 120).lower()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'seeker')
        name     = sanitize(request.form.get('full_name', ''), 100)
        wilaya   = sanitize(request.form.get('wilaya', ''), 50)

        if not email or not password or not name:
            flash('يرجى ملء جميع الحقول المطلوبة', 'error')
            return redirect(url_for('register'))
        if role not in ('seeker', 'company'):
            flash('نوع الحساب غير صحيح', 'error')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash('كلمة المرور يجب أن تكون 8 أحرف على الأقل', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مسجل مسبقاً', 'error')
            return redirect(url_for('register'))

        user = User(email=email, role=role, full_name=name, wilaya=wilaya)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'company':
            company_name = sanitize(request.form.get('company_name', name), 100)
            sector = sanitize(request.form.get('sector', ''), 50)
            company = Company(user_id=user.id, name=company_name,
                              sector=sector, wilaya=wilaya)
            db.session.add(company)

        db.session.commit()
        session['user_id'] = user.id
        session['role']    = user.role
        session['name']    = user.full_name
        logger.info(f"New user registered: {email} role={role}")
        flash(f'أهلاً بك {name}! تم إنشاء حسابك بنجاح 🎉', 'success')
        return redirect(url_for('dashboard') if role == 'company' else url_for('jobs'))
    return render_template('register.html', wilayas=WILAYAS, categories=CATEGORIES)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        email    = sanitize(request.form.get('email', ''), 120).lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for {email} from {request.remote_addr}")
            flash('البريد أو كلمة المرور غير صحيحة', 'error')
            return redirect(url_for('login'))
        if not user.is_active:
            flash('حسابك موقوف، تواصل مع الإدارة', 'error')
            return redirect(url_for('login'))
        session.permanent = True
        session['user_id'] = user.id
        session['role']    = user.role
        session['name']    = user.full_name
        logger.info(f"User logged in: {email}")
        flash(f'أهلاً بعودتك {user.full_name} 👋', 'success')
        if user.role == 'admin':   return redirect(url_for('admin_panel'))
        if user.role == 'company': return redirect(url_for('dashboard'))
        return redirect(url_for('jobs'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    user_email = session.get('name', 'unknown')
    session.clear()
    logger.info(f"User logged out: {user_email}")
    flash('تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('index'))

# ─── COMPANY DASHBOARD ────────────────────────────────────

@app.route('/dashboard')
@login_required
@company_required
def dashboard():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    jobs_list = (Job.query.filter_by(company_id=company.id)
                 .order_by(Job.created_at.desc()).all())
    total_apps = sum(j.applications.count() for j in jobs_list)
    new_apps   = sum(j.applications.filter_by(status='new').count() for j in jobs_list)
    return render_template('dashboard.html', company=company, jobs=jobs_list,
        total_apps=total_apps, new_apps=new_apps,
        wilayas=WILAYAS, categories=CATEGORIES, job_types=JOB_TYPES)


@app.route('/dashboard/post-job', methods=['POST'])
@login_required
@company_required
def post_job():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    title   = sanitize(request.form.get('title', ''), 150)
    if not title:
        flash('عنوان الوظيفة مطلوب', 'error')
        return redirect(url_for('dashboard') + '?tab=post')
    job = Job(
        company_id   = company.id,
        title        = title,
        category     = sanitize(request.form.get('category', ''), 50),
        job_type     = sanitize(request.form.get('job_type', ''), 30),
        wilaya       = sanitize(request.form.get('wilaya', ''), 50),
        salary_min   = int(request.form.get('salary_min') or 0),
        salary_max   = int(request.form.get('salary_max') or 0),
        description  = sanitize(request.form.get('description', ''), 5000),
        requirements = sanitize(request.form.get('requirements', ''), 3000),
        benefits     = sanitize(request.form.get('benefits', ''), 2000),
    )
    db.session.add(job)
    db.session.commit()
    logger.info(f"New job posted: {title} by company={company.id}")
    flash('تم نشر الوظيفة بنجاح ✅', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard/delete-job/<int:job_id>', methods=['POST'])
@login_required
@company_required
def delete_job(job_id):
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    job = Job.query.filter_by(id=job_id, company_id=company.id).first_or_404()
    db.session.delete(job)
    db.session.commit()
    flash('تم حذف الوظيفة', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard/applications')
@login_required
@company_required
def company_applications():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    apps = (Application.query
            .join(Job).filter(Job.company_id == company.id)
            .order_by(Application.created_at.desc()).all())
    return render_template('applications.html', applications=apps, company=company)


@app.route('/dashboard/application/<int:app_id>/status', methods=['POST'])
@login_required
@company_required
def update_app_status(app_id):
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    app_obj = (Application.query.join(Job)
               .filter(Application.id == app_id, Job.company_id == company.id)
               .first_or_404())
    new_status = request.form.get('status', 'new')
    if new_status in ('new', 'reviewing', 'accepted', 'rejected'):
        app_obj.status = new_status
        db.session.commit()
        flash('تم تحديث حالة الطلب', 'success')
    return redirect(url_for('company_applications'))


@app.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
@company_required
def company_profile():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        company.name        = sanitize(request.form.get('name', ''), 100)
        company.sector      = sanitize(request.form.get('sector', ''), 50)
        company.wilaya      = sanitize(request.form.get('wilaya', ''), 50)
        company.size        = sanitize(request.form.get('size', ''), 30)
        company.website     = sanitize(request.form.get('website', ''), 200)
        company.description = sanitize(request.form.get('description', ''), 2000)
        db.session.commit()
        flash('تم حفظ الملف بنجاح ✅', 'success')
        return redirect(url_for('company_profile'))
    return render_template('company_profile.html', company=company,
        wilayas=WILAYAS, categories=CATEGORIES)

# ─── TALENTS ──────────────────────────────────────────────

@app.route('/talents')
def talents():
    q      = sanitize(request.args.get('q', ''), 100)
    wilaya = sanitize(request.args.get('wilaya', ''), 50)
    cat    = sanitize(request.args.get('cat', ''), 50)
    query  = Talent.query.filter_by(available=True)
    if q:      query = query.join(User).filter(User.full_name.ilike(f'%{q}%'))
    if wilaya: query = query.filter_by(wilaya=wilaya)
    if cat:    query = query.filter_by(category=cat)
    talents_list = query.order_by(Talent.created_at.desc()).all()
    return render_template('talents.html', talents=talents_list,
        wilayas=WILAYAS, categories=CATEGORIES, q=q, wilaya=wilaya, cat=cat)


@app.route('/talent/profile', methods=['GET', 'POST'])
@login_required
def talent_profile():
    if session.get('role') != 'seeker':
        flash('هذه الصفحة للباحثين عن عمل فقط', 'error')
        return redirect(url_for('index'))
    talent = Talent.query.filter_by(user_id=session['user_id']).first()
    if request.method == 'POST':
        if not talent:
            talent = Talent(user_id=session['user_id'])
            db.session.add(talent)
        talent.category   = sanitize(request.form.get('category', ''), 50)
        talent.wilaya     = sanitize(request.form.get('wilaya', ''), 50)
        talent.experience = sanitize(request.form.get('experience', ''), 30)
        talent.bio        = sanitize(request.form.get('bio', ''), 1000)
        talent.skills     = sanitize(request.form.get('skills', ''), 200)
        talent.available  = bool(request.form.get('available'))
        db.session.commit()
        flash('تم حفظ ملفك المهني ✅ الشركات يمكنها الآن إيجادك!', 'success')
        return redirect(url_for('talent_profile'))
    return render_template('talent_profile.html', talent=talent,
        wilayas=WILAYAS, categories=CATEGORIES)

# ─── ADMIN ────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    stats = {
        'jobs':  Job.query.count(),
        'users': User.query.count(),
        'cos':   Company.query.count(),
        'apps':  Application.query.count(),
    }
    pending_jobs = Job.query.filter_by(is_approved=False).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    all_jobs     = Job.query.order_by(Job.created_at.desc()).limit(20).all()
    all_users    = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', stats=stats,
        pending_jobs=pending_jobs, recent_users=recent_users,
        all_jobs=all_jobs, all_users=all_users)


@app.route('/admin/job/<int:job_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = True
    db.session.commit()
    logger.info(f"Admin approved job {job_id}")
    flash('تمت الموافقة على الوظيفة ✅', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/job/<int:job_id>/feature', methods=['POST'])
@login_required
@admin_required
def feature_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_featured = not job.is_featured
    db.session.commit()
    flash('تم تحديث تمييز الوظيفة ⭐', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/user/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('لا يمكن تعطيل حساب المشرف', 'error')
        return redirect(url_for('admin_panel'))
    user.is_active = not user.is_active
    db.session.commit()
    logger.info(f"Admin toggled user {user_id} active={user.is_active}")
    flash('تم تحديث حالة المستخدم', 'success')
    return redirect(url_for('admin_panel'))

# ─── SEO ROUTES ───────────────────────────────────────────

@app.route('/sitemap.xml')
def sitemap():
    base = app.config.get('BASE_URL', 'https://web-production-dbe18.up.railway.app')
    jobs_list = Job.query.filter_by(is_active=True, is_approved=True).all()
    xml  = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, freq, pri in [
        ('/', 'daily', '1.0'), ('/jobs', 'hourly', '0.9'),
        ('/talents', 'daily', '0.8'), ('/register', 'monthly', '0.6'),
    ]:
        xml += f'<url><loc>{base}{path}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>\n'
    for job in jobs_list:
        xml += f'<url><loc>{base}/job/{job.id}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>\n'
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    base = app.config.get('BASE_URL', 'https://web-production-dbe18.up.railway.app')
    txt = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /dashboard
Disallow: /logout
Sitemap: {base}/sitemap.xml"""
    return Response(txt, mimetype='text/plain')

# ─── INIT DB ──────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@wadifa.dz').first():
            admin = User(
                email='admin@wadifa.dz', role='admin',
                full_name='المشرف العام', is_active=True
            )
            admin.set_password('admin2024')
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin account created: admin@wadifa.dz")


init_db()

if __name__ == '__main__':
    os.makedirs('/tmp/uploads', exist_ok=True)
    app.run(
        debug=os.environ.get('FLASK_ENV') == 'development',
        port=int(os.environ.get('PORT', 5000)),
        host='0.0.0.0'
    )
