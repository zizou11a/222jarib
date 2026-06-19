"""
وضيفة DZ | Wadifa DZ
منصة التوظيف الجزائرية
"""
import os, logging
from datetime import datetime, date
from functools import wraps

import bleach
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('wadifa')

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wadifa.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config.update(
    SECRET_KEY                     = os.environ.get('SECRET_KEY', 'wadifa-dz-dev-key-2024'),
    SQLALCHEMY_DATABASE_URI        = DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS = False,
    SQLALCHEMY_ENGINE_OPTIONS      = {'pool_pre_ping': True, 'pool_recycle': 300},
    WTF_CSRF_ENABLED               = True,
    WTF_CSRF_TIME_LIMIT            = 3600,
    SESSION_COOKIE_HTTPONLY        = True,
    SESSION_COOKIE_SAMESITE        = 'Lax',
    SESSION_COOKIE_SECURE          = False,
    MAX_CONTENT_LENGTH             = 5 * 1024 * 1024,
    UPLOAD_FOLDER                  = '/tmp/uploads',
    BASE_URL                       = os.environ.get('BASE_URL', 'https://web-production-dbe18.up.railway.app'),
    CACHE_TYPE                     = 'SimpleCache',
    CACHE_DEFAULT_TIMEOUT          = 300,
    DEBUG                          = False,
)

db      = SQLAlchemy(app)
csrf    = CSRFProtect(app)
cache   = Cache(app)
limiter = Limiter(get_remote_address, app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://")

WILAYAS = [
    'أدرار','الشلف','الأغواط','أم البواقي','باتنة','بجاية','بسكرة','بشار',
    'البليدة','البويرة','تمنراست','تبسة','تلمسان','تيارت','تيزي وزو','الجزائر',
    'الجلفة','جيجل','سطيف','سعيدة','سكيكدة','سيدي بلعباس','عنابة','قالمة',
    'قسنطينة','المدية','مستغانم','المسيلة','معسكر','ورقلة','وهران','البيض',
    'إليزي','برج بوعريريج','بومرداس','الطارف','تندوف','تيسمسيلت','الوادي',
    'خنشلة','سوق أهراس','تيبازة','ميلة','عين الدفلى','النعامة','عين تموشنت',
    'غرداية','غليزان'
]
CATEGORIES = ['تكنولوجيا','هندسة','طب وصحة','تسويق','مالية ومحاسبة','تعليم','نفط وغاز','بناء','إدارة أعمال','قانون','أخرى']
JOB_TYPES  = ['دوام كامل','دوام جزئي','عن بعد','عقد مؤقت','تدريب']
EXPERIENCE = ['بدون خبرة','أقل من سنة','1-3 سنوات','3-5 سنوات','5-10 سنوات','+10 سنوات']
SIZES      = ['1-10','10-50','50-200','200-1000','+1000']

# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='seeker', index=True)
    full_name     = db.Column(db.String(100), nullable=False)
    wilaya        = db.Column(db.String(50))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    company       = db.relationship('Company', backref='user', uselist=False)
    applications  = db.relationship('Application', backref='user', lazy='dynamic')

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)


class Company(db.Model):
    __tablename__ = 'companies'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    sector      = db.Column(db.String(50))
    wilaya      = db.Column(db.String(50))
    size        = db.Column(db.String(30))
    website     = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    jobs        = db.relationship('Job', backref='company', lazy='dynamic')


class Job(db.Model):
    __tablename__ = 'jobs'
    id           = db.Column(db.Integer, primary_key=True)
    company_id   = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    title        = db.Column(db.String(150), nullable=False)
    category     = db.Column(db.String(50), index=True)
    job_type     = db.Column(db.String(30), index=True)
    wilaya       = db.Column(db.String(50), index=True)
    experience   = db.Column(db.String(30))
    salary_min   = db.Column(db.Integer)
    salary_max   = db.Column(db.Integer)
    description  = db.Column(db.Text)
    requirements = db.Column(db.Text)
    benefits     = db.Column(db.Text)
    views        = db.Column(db.Integer, default=0)
    is_active    = db.Column(db.Boolean, default=True, index=True)
    is_featured  = db.Column(db.Boolean, default=False)
    is_approved  = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    applications = db.relationship('Application', backref='job', lazy='dynamic', cascade='all, delete-orphan')


class Application(db.Model):
    __tablename__ = 'applications'
    id           = db.Column(db.Integer, primary_key=True)
    job_id       = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    cover_letter = db.Column(db.Text)
    status       = db.Column(db.String(20), default='new')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('job_id','user_id', name='uq_application'),)


class Talent(db.Model):
    __tablename__ = 'talents'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    category   = db.Column(db.String(50))
    wilaya     = db.Column(db.String(50))
    experience = db.Column(db.String(30))
    bio        = db.Column(db.Text)
    skills     = db.Column(db.String(300))
    available  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='talent_profile')


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    slug         = db.Column(db.String(220), unique=True, index=True)
    content      = db.Column(db.Text)
    excerpt      = db.Column(db.String(300))
    is_published = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

# ─── HELPERS ──────────────────────────────────────────────

def clean(text, max_len=None):
    if not text: return ''
    t = bleach.clean(str(text), tags=[], strip=True).strip()
    return t[:max_len] if max_len else t

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

def role_required(*roles):
    def dec(f):
        @wraps(f)
        def inner(*a, **kw):
            if session.get('role') not in roles:
                flash('ليس لديك صلاحية', 'error')
                return redirect(url_for('index'))
            return f(*a, **kw)
        return inner
    return dec

@app.context_processor
def inject_globals():
    return dict(now=datetime.utcnow(), today=date.today(),
        BASE_URL=app.config['BASE_URL'], CATEGORIES=CATEGORIES, WILAYAS=WILAYAS)

@app.after_request
def security_headers(resp):
    resp.headers['X-Frame-Options']        = 'SAMEORIGIN'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    if request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'public, max-age=31536000'
    return resp

# ─── ERROR HANDLERS ───────────────────────────────────────

@app.errorhandler(CSRFError)
def csrf_error(e):
    flash('انتهت صلاحية الجلسة، حاول مجدداً', 'error')
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(404)
def e404(e): return render_template('errors/404.html'), 404

@app.errorhandler(403)
def e403(e): return render_template('errors/403.html'), 403

@app.errorhandler(500)
def e500(e):
    logger.error(f"500: {e}", exc_info=True)
    return render_template('errors/500.html'), 500

# ─── PUBLIC ROUTES ────────────────────────────────────────

@app.route('/')
def index():
    featured   = Job.query.filter_by(is_active=True, is_featured=True, is_approved=True).order_by(Job.created_at.desc()).limit(6).all()
    latest     = Job.query.filter_by(is_active=True, is_approved=True).order_by(Job.created_at.desc()).limit(9).all()
    total_jobs = Job.query.filter_by(is_active=True, is_approved=True).count()
    total_cos  = Company.query.filter_by(is_approved=True).count()
    total_apps = Application.query.count()
    return render_template('index.html', featured=featured, latest=latest,
        total_jobs=total_jobs, total_cos=total_cos, total_apps=total_apps)

@app.route('/jobs')
def jobs():
    q      = clean(request.args.get('q',''), 100)
    wilaya = clean(request.args.get('wilaya',''), 50)
    cat    = clean(request.args.get('cat',''), 50)
    jtype  = clean(request.args.get('type',''), 30)
    page   = request.args.get('page', 1, type=int)
    qr = Job.query.filter_by(is_active=True, is_approved=True)
    if q:      qr = qr.filter(Job.title.ilike(f'%{q}%'))
    if wilaya: qr = qr.filter_by(wilaya=wilaya)
    if cat:    qr = qr.filter_by(category=cat)
    if jtype:  qr = qr.filter_by(job_type=jtype)
    jobs_list = qr.order_by(Job.is_featured.desc(), Job.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs_list, job_types=JOB_TYPES,
        q=q, wilaya=wilaya, cat=cat, jtype=jtype)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    job.views = (job.views or 0) + 1
    db.session.commit()
    already_applied = False
    if 'user_id' in session:
        already_applied = Application.query.filter_by(job_id=job_id, user_id=session['user_id']).first() is not None
    related = Job.query.filter(Job.category==job.category, Job.id!=job.id, Job.is_active==True).limit(3).all()
    return render_template('job_detail.html', job=job, already_applied=already_applied, related=related)

@app.route('/job/<int:job_id>/apply', methods=['POST'])
@login_required
def apply(job_id):
    if session.get('role') != 'seeker':
        flash('الشركات لا يمكنها التقديم', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    if Application.query.filter_by(job_id=job_id, user_id=session['user_id']).first():
        flash('لقد قدّمت على هذه الوظيفة مسبقاً', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    db.session.add(Application(job_id=job_id, user_id=session['user_id'],
        cover_letter=clean(request.form.get('cover_letter',''), 2000)))
    db.session.commit()
    flash('✅ تم إرسال طلبك بنجاح!', 'success')
    return redirect(url_for('job_detail', job_id=job_id))

# ─── AUTH ─────────────────────────────────────────────────

@app.route('/register', methods=['GET','POST'])
@limiter.limit("10 per hour")
def register():
    if request.method == 'POST':
        email    = clean(request.form.get('email',''), 120).lower()
        password = request.form.get('password','')
        role     = request.form.get('role','seeker')
        name     = clean(request.form.get('full_name',''), 100)
        wilaya   = clean(request.form.get('wilaya',''), 50)
        if not email or '@' not in email:
            flash('بريد إلكتروني غير صحيح', 'error'); return redirect(url_for('register'))
        if len(password) < 8:
            flash('كلمة المرور 8 أحرف على الأقل', 'error'); return redirect(url_for('register'))
        if not name:
            flash('الاسم مطلوب', 'error'); return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('البريد مسجل مسبقاً', 'error'); return redirect(url_for('register'))
        user = User(email=email, role=role, full_name=name, wilaya=wilaya)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        if role == 'company':
            db.session.add(Company(user_id=user.id,
                name=clean(request.form.get('company_name', name), 100),
                sector=clean(request.form.get('sector',''), 50), wilaya=wilaya))
        db.session.commit()
        session.update({'user_id': user.id, 'role': user.role, 'name': user.full_name})
        flash(f'🎉 أهلاً بك {name}!', 'success')
        return redirect(url_for('dashboard') if role == 'company' else url_for('jobs'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
@limiter.limit("15 per minute")
def login():
    if request.method == 'POST':
        email    = clean(request.form.get('email',''), 120).lower()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('البريد أو كلمة المرور غير صحيحة', 'error')
            return redirect(url_for('login'))
        if not user.is_active:
            flash('حسابك موقوف', 'error'); return redirect(url_for('login'))
        session.permanent = True
        session.update({'user_id': user.id, 'role': user.role, 'name': user.full_name})
        flash(f'أهلاً بعودتك {user.full_name} 👋', 'success')
        if user.role == 'admin':   return redirect(url_for('admin_panel'))
        if user.role == 'company': return redirect(url_for('dashboard'))
        return redirect(url_for('jobs'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل خروجك', 'success')
    return redirect(url_for('index'))

# ─── DASHBOARD ────────────────────────────────────────────

@app.route('/dashboard')
@login_required
@role_required('company')
def dashboard():
    company   = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    jobs_list = company.jobs.order_by(Job.created_at.desc()).all()
    total_apps = sum(j.applications.count() for j in jobs_list)
    new_apps   = sum(j.applications.filter_by(status='new').count() for j in jobs_list)
    return render_template('dashboard.html', company=company, jobs=jobs_list,
        total_apps=total_apps, new_apps=new_apps, job_types=JOB_TYPES, EXPERIENCE=EXPERIENCE)

@app.route('/dashboard/post-job', methods=['POST'])
@login_required
@role_required('company')
def post_job():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    title   = clean(request.form.get('title',''), 150)
    if not title:
        flash('عنوان الوظيفة مطلوب', 'error'); return redirect(url_for('dashboard'))
    db.session.add(Job(
        company_id=company.id, title=title,
        category=clean(request.form.get('category',''), 50),
        job_type=clean(request.form.get('job_type',''), 30),
        wilaya=clean(request.form.get('wilaya',''), 50),
        experience=clean(request.form.get('experience',''), 30),
        salary_min=int(request.form.get('salary_min') or 0),
        salary_max=int(request.form.get('salary_max') or 0),
        description=clean(request.form.get('description',''), 5000),
        requirements=clean(request.form.get('requirements',''), 3000),
        benefits=clean(request.form.get('benefits',''), 2000),
    ))
    db.session.commit()
    flash('✅ تم نشر الوظيفة بنجاح', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/delete-job/<int:jid>', methods=['POST'])
@login_required
@role_required('company')
def delete_job(jid):
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    job = Job.query.filter_by(id=jid, company_id=company.id).first_or_404()
    db.session.delete(job); db.session.commit()
    flash('تم حذف الوظيفة', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/applications')
@login_required
@role_required('company')
def company_applications():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    apps = Application.query.join(Job).filter(Job.company_id==company.id).order_by(Application.created_at.desc()).all()
    return render_template('applications.html', applications=apps, company=company)

@app.route('/dashboard/application/<int:aid>/status', methods=['POST'])
@login_required
@role_required('company')
def update_app_status(aid):
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    app_obj = Application.query.join(Job).filter(Application.id==aid, Job.company_id==company.id).first_or_404()
    st = request.form.get('status','new')
    if st in ('new','reviewing','accepted','rejected'):
        app_obj.status = st; db.session.commit()
        flash('تم تحديث الطلب', 'success')
    return redirect(url_for('company_applications'))

@app.route('/dashboard/profile', methods=['GET','POST'])
@login_required
@role_required('company')
def company_profile():
    company = Company.query.filter_by(user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        company.name=clean(request.form.get('name',''),100)
        company.sector=clean(request.form.get('sector',''),50)
        company.wilaya=clean(request.form.get('wilaya',''),50)
        company.size=clean(request.form.get('size',''),30)
        company.website=clean(request.form.get('website',''),200)
        company.description=clean(request.form.get('description',''),2000)
        db.session.commit(); flash('✅ تم الحفظ', 'success')
        return redirect(url_for('company_profile'))
    return render_template('company_profile.html', company=company, SIZES=SIZES)

# ─── TALENTS ──────────────────────────────────────────────

@app.route('/talents')
def talents():
    q=clean(request.args.get('q',''),100); wilaya=clean(request.args.get('wilaya',''),50); cat=clean(request.args.get('cat',''),50)
    qr = Talent.query.filter_by(available=True)
    if q:      qr = qr.join(User).filter(User.full_name.ilike(f'%{q}%'))
    if wilaya: qr = qr.filter_by(wilaya=wilaya)
    if cat:    qr = qr.filter_by(category=cat)
    return render_template('talents.html', talents=qr.order_by(Talent.created_at.desc()).all(), q=q, wilaya=wilaya, cat=cat)

@app.route('/talent/profile', methods=['GET','POST'])
@login_required
@role_required('seeker')
def talent_profile():
    talent = Talent.query.filter_by(user_id=session['user_id']).first()
    if request.method == 'POST':
        if not talent:
            talent = Talent(user_id=session['user_id']); db.session.add(talent)
        talent.category=clean(request.form.get('category',''),50)
        talent.wilaya=clean(request.form.get('wilaya',''),50)
        talent.experience=clean(request.form.get('experience',''),30)
        talent.bio=clean(request.form.get('bio',''),1000)
        talent.skills=clean(request.form.get('skills',''),300)
        talent.available=bool(request.form.get('available'))
        db.session.commit(); flash('✅ تم حفظ ملفك المهني!', 'success')
        return redirect(url_for('talent_profile'))
    return render_template('talent_profile.html', talent=talent, EXPERIENCE=EXPERIENCE)

# ─── STATIC PAGES ─────────────────────────────────────────

@app.route('/about')
def about(): return render_template('pages/about.html')

@app.route('/contact', methods=['GET','POST'])
@limiter.limit("5 per hour")
def contact():
    if request.method == 'POST':
        flash('✅ تم إرسال رسالتك!', 'success')
        return redirect(url_for('contact'))
    return render_template('pages/contact.html')

@app.route('/faq')
def faq(): return render_template('pages/faq.html')

@app.route('/privacy')
def privacy(): return render_template('pages/privacy.html')

@app.route('/terms')
def terms(): return render_template('pages/terms.html')

@app.route('/blog')
def blog():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(12).all()
    return render_template('pages/blog.html', posts=posts)

# ─── ADMIN ────────────────────────────────────────────────

@app.route('/admin')
@login_required
@role_required('admin')
def admin_panel():
    stats = {'jobs':Job.query.count(),'users':User.query.count(),'cos':Company.query.count(),'apps':Application.query.count()}
    return render_template('admin.html', stats=stats,
        pending_jobs=Job.query.filter_by(is_approved=False).all(),
        recent_users=User.query.order_by(User.created_at.desc()).limit(10).all(),
        all_jobs=Job.query.order_by(Job.created_at.desc()).limit(20).all(),
        all_users=User.query.order_by(User.created_at.desc()).all())

@app.route('/admin/job/<int:jid>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_job(jid):
    j=Job.query.get_or_404(jid); j.is_approved=True; db.session.commit()
    flash('✅ تمت الموافقة', 'success'); return redirect(url_for('admin_panel'))

@app.route('/admin/job/<int:jid>/feature', methods=['POST'])
@login_required
@role_required('admin')
def feature_job(jid):
    j=Job.query.get_or_404(jid); j.is_featured=not j.is_featured; db.session.commit()
    flash('⭐ تم التحديث', 'success'); return redirect(url_for('admin_panel'))

@app.route('/admin/user/<int:uid>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(uid):
    u=User.query.get_or_404(uid)
    if u.role=='admin': flash('لا يمكن تعطيل المشرف','error'); return redirect(url_for('admin_panel'))
    u.is_active=not u.is_active; db.session.commit()
    flash('تم التحديث','success'); return redirect(url_for('admin_panel'))

# ─── SEO ──────────────────────────────────────────────────

@app.route('/sitemap.xml')
def sitemap():
    base = app.config['BASE_URL']
    jobs_list = Job.query.filter_by(is_active=True, is_approved=True).all()
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, freq, pri in [('/', 'daily', '1.0'),('/jobs','hourly','0.95'),('/talents','daily','0.85'),('/about','monthly','0.6'),('/faq','monthly','0.6'),('/blog','weekly','0.7'),('/contact','monthly','0.5')]:
        xml += f'  <url><loc>{base}{path}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>\n'
    for job in jobs_list:
        xml += f'  <url><loc>{base}/job/{job.id}</loc><lastmod>{job.created_at.strftime("%Y-%m-%d")}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    base = app.config['BASE_URL']
    return Response(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /dashboard\nDisallow: /logout\nSitemap: {base}/sitemap.xml", mimetype='text/plain')

@app.route('/manifest.json')
def manifest():
    return Response('{"name":"وضيفة DZ","short_name":"وضيفة","start_url":"/","display":"standalone","background_color":"#0a0e1a","theme_color":"#10b981","lang":"ar","dir":"rtl"}', mimetype='application/json')

# ─── INIT ─────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@wadifa.dz').first():
        admin = User(email='admin@wadifa.dz', role='admin', full_name='المشرف العام', is_active=True)
        admin.set_password('admin2024')
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin created: admin@wadifa.dz")

if __name__ == '__main__':
    os.makedirs('/tmp/uploads', exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
