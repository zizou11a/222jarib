from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'wazifati2024')
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wazifati.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'

db = SQLAlchemy(app)

WILAYAS = ['أدرار','الشلف','الأغواط','أم البواقي','باتنة','بجاية','بسكرة','بشار','البليدة','البويرة','تمنراست','تبسة','تلمسان','تيارت','تيزي وزو','الجزائر','الجلفة','جيجل','سطيف','سعيدة','سكيكدة','سيدي بلعباس','عنابة','قالمة','قسنطينة','المدية','مستغانم','المسيلة','معسكر','ورقلة','وهران','البيض','إليزي','برج بوعريريج','بومرداس','الطارف','تندوف','تيسمسيلت','الوادي','خنشلة','سوق أهراس','تيبازة','ميلة','عين الدفلى','النعامة','عين تموشنت','غرداية','غليزان']
CATEGORIES = ['تكنولوجيا','هندسة','طب وصحة','تسويق','مالية ومحاسبة','تعليم','نفط وغاز','بناء','إدارة أعمال','أخرى']
JOB_TYPES = ['دوام كامل','دوام جزئي','عن بعد','عقد']

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='seeker')
    full_name = db.Column(db.String(100))
    wilaya = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship('Company', backref='user', uselist=False)
    applications = db.relationship('Application', backref='user', lazy=True)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50))
    wilaya = db.Column(db.String(50))
    size = db.Column(db.String(30))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    jobs = db.relationship('Job', backref='company', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50))
    job_type = db.Column(db.String(30))
    wilaya = db.Column(db.String(50))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    benefits = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    applications = db.relationship('Application', backref='job', lazy=True)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    cv_filename = db.Column(db.String(200))
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    featured = Job.query.filter_by(is_active=True, is_featured=True, is_approved=True).limit(6).all()
    latest = Job.query.filter_by(is_active=True, is_approved=True).order_by(Job.created_at.desc()).limit(8).all()
    total_jobs = Job.query.filter_by(is_active=True, is_approved=True).count()
    total_cos = Company.query.filter_by(is_approved=True).count()
    total_apps = Application.query.count()
    return render_template('index.html', featured=featured, latest=latest,
        total_jobs=total_jobs, total_cos=total_cos, total_apps=total_apps,
        wilayas=WILAYAS, categories=CATEGORIES)

@app.route('/jobs')
def jobs():
    q = request.args.get('q', '')
    wilaya = request.args.get('wilaya', '')
    cat = request.args.get('cat', '')
    jtype = request.args.get('type', '')
    query = Job.query.filter_by(is_active=True, is_approved=True)
    if q: query = query.filter(Job.title.ilike(f'%{q}%'))
    if wilaya: query = query.filter_by(wilaya=wilaya)
    if cat: query = query.filter_by(category=cat)
    if jtype: query = query.filter_by(job_type=jtype)
    jobs_list = query.order_by(Job.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs_list,
        wilayas=WILAYAS, categories=CATEGORIES, job_types=JOB_TYPES,
        q=q, wilaya=wilaya, cat=cat, jtype=jtype)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    already_applied = False
    if 'user_id' in session:
        already_applied = Application.query.filter_by(job_id=job_id, user_id=session['user_id']).first() is not None
    return render_template('job_detail.html', job=job, already_applied=already_applied)

@app.route('/job/<int:job_id>/apply', methods=['POST'])
@login_required
def apply(job_id):
    if session.get('role') != 'seeker':
        flash('الشركات لا يمكنها التقديم', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    existing = Application.query.filter_by(job_id=job_id, user_id=session['user_id']).first()
    if existing:
        flash('لقد قدّمت على هذه الوظيفة مسبقاً', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    app_obj = Application(job_id=job_id, user_id=session['user_id'],
        cover_letter=request.form.get('cover_letter', ''))
    db.session.add(app_obj)
    db.session.commit()
    flash('تم إرسال طلبك بنجاح ✅', 'success')
    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form['role']
        name = request.form['full_name'].strip()
        if User.query.filter_by(email=email).first():
            flash('البريد مسجل مسبقاً', 'error')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash('كلمة المرور 8 أحرف على الأقل', 'error')
            return redirect(url_for('register'))
        user = User(email=email, password_hash=generate_password_hash(password),
            role=role, full_name=name, wilaya=request.form.get('wilaya', ''))
        db.session.add(user)
        db.session.flush()
        if role == 'company':
            company = Company(user_id=user.id,
                name=request.form.get('company_name', name),
                sector=request.form.get('sector', ''),
                wilaya=request.form.get('wilaya', ''))
            db.session.add(company)
        db.session.commit()
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.full_name
        flash(f'أهلاً بك {name} 🎉', 'success')
        return redirect(url_for('dashboard') if role == 'company' else url_for('jobs'))
    return render_template('register.html', wilayas=WILAYAS, categories=CATEGORIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('البريد أو كلمة المرور غير صحيحة', 'error')
            return redirect(url_for('login'))
        if not user.is_active:
            flash('حسابك موقوف', 'error')
            return redirect(url_for('login'))
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.full_name
        flash(f'أهلاً بعودتك {user.full_name} 👋', 'success')
        if user.role == 'admin': return redirect(url_for('admin_panel'))
        if user.role == 'company': return redirect(url_for('dashboard'))
        return redirect(url_for('jobs'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
@company_required
def dashboard():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    jobs_list = Job.query.filter_by(company_id=company.id).order_by(Job.created_at.desc()).all()
    total_apps = sum(len(j.applications) for j in jobs_list)
    new_apps = sum(1 for j in jobs_list for a in j.applications if a.status == 'new')
    return render_template('dashboard.html', company=company, jobs=jobs_list,
        total_apps=total_apps, new_apps=new_apps,
        wilayas=WILAYAS, categories=CATEGORIES, job_types=JOB_TYPES)

@app.route('/dashboard/post-job', methods=['POST'])
@login_required
@company_required
def post_job():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    job = Job(company_id=company.id, title=request.form['title'],
        category=request.form['category'], job_type=request.form['job_type'],
        wilaya=request.form['wilaya'],
        salary_min=int(request.form.get('salary_min') or 0),
        salary_max=int(request.form.get('salary_max') or 0),
        description=request.form['description'],
        requirements=request.form.get('requirements', ''),
        benefits=request.form.get('benefits', ''))
    db.session.add(job)
    db.session.commit()
    flash('تم نشر الوظيفة ✅', 'success')
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
    apps = Application.query.join(Job).filter(Job.company_id == company.id).order_by(Application.created_at.desc()).all()
    return render_template('applications.html', applications=apps, company=company)

@app.route('/dashboard/application/<int:app_id>/status', methods=['POST'])
@login_required
@company_required
def update_app_status(app_id):
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    app_obj = Application.query.join(Job).filter(Application.id == app_id, Job.company_id == company.id).first_or_404()
    app_obj.status = request.form['status']
    db.session.commit()
    flash('تم تحديث الطلب', 'success')
    return redirect(url_for('company_applications'))

@app.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
@company_required
def company_profile():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        company.name = request.form['name']
        company.sector = request.form['sector']
        company.wilaya = request.form['wilaya']
        company.size = request.form['size']
        company.website = request.form.get('website', '')
        company.description = request.form.get('description', '')
        db.session.commit()
        flash('تم الحفظ ✅', 'success')
        return redirect(url_for('company_profile'))
    return render_template('company_profile.html', company=company, wilayas=WILAYAS, categories=CATEGORIES)

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    stats = {'jobs': Job.query.count(), 'users': User.query.count(),
             'cos': Company.query.count(), 'apps': Application.query.count()}
    pending_jobs = Job.query.filter_by(is_approved=False).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    all_jobs = Job.query.order_by(Job.created_at.desc()).limit(20).all()
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', stats=stats, pending_jobs=pending_jobs,
        recent_users=recent_users, all_jobs=all_jobs, all_users=all_users)

@app.route('/admin/job/<int:job_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = True
    db.session.commit()
    flash('تمت الموافقة ✅', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/job/<int:job_id>/feature', methods=['POST'])
@login_required
@admin_required
def feature_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_featured = not job.is_featured
    db.session.commit()
    flash('تم تحديث التمييز ⭐', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash('تم تحديث المستخدم', 'success')
    return redirect(url_for('admin_panel'))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@wazifati.dz').first():
        admin = User(email='admin@wazifati.dz',
            password_hash=generate_password_hash('admin2024'),
            role='admin', full_name='المشرف العام', is_active=True)
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    os.makedirs('/tmp/uploads', exist_ok=True)
    app.run(debug=False, port=int(os.environ.get('PORT', 5000)))
