from flask import (Flask, render_template, request, jsonify,
                   send_file, redirect, url_for, flash, session)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os, json, io
from datetime import datetime

from analyzer import analyze_dna, parse_fasta
from database import (
    init_db, get_connection,
    # users
    create_user, get_user_by_username, get_user_by_id, update_last_login,
    get_all_users, toggle_user_active,
    # patients
    create_patient, get_all_patients, get_patient_by_id,
    update_patient, delete_patient,
    # genes
    create_gene, get_all_genes, get_gene_by_id,
    # sequences
    create_sequence, get_all_sequences, get_sequence_by_id,
    # diseases
    create_disease, get_all_diseases, get_disease_by_id,
    # mutations
    create_mutation, get_all_mutations, get_mutation_by_id,
    get_mutations_paginated, get_mutation_categories,
    # samples
    create_sample, get_all_samples, get_sample_by_id,
    get_samples_by_patient, update_sample_status,
    # patient analysis
    create_analysis, get_all_analyses, get_analysis_by_id,
    get_analyses_by_patient,
    # results (history)
    save_result, fetch_all_results, get_result_by_id, delete_result,
    # stats
    get_dashboard_stats,
)
from report_generator import generate_pdf_report

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-me')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads')

ALLOWED_EXT = {'fasta', 'fa', 'txt'}

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, app=app,
                  default_limits=["200 per day", "50 per hour"])

# ── Login Manager ─────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access GenomePath.'


class User(UserMixin):
    def __init__(self, data):
        self.id         = data['id']
        self.username   = data['username']
        self.email      = data['email']
        self.role       = data['role']
        self.department = data.get('department')

    def is_admin(self):
        return self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    data = get_user_by_id(int(user_id))
    return User(data) if data else None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def stringify_datetimes(obj):
    """Recursively convert all datetime objects in a dict/list to strings."""
    import datetime as dt
    if isinstance(obj, dict):
        return {k: stringify_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_datetimes(i) for i in obj]
    elif isinstance(obj, (dt.datetime, dt.date)):
        return str(obj)
    return obj


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username  = request.form.get('username', '').strip()
        password  = request.form.get('password', '')
        user_data = get_user_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user, remember=request.form.get('remember') == 'on')
            update_last_login(user.id)
            return redirect(request.args.get('next') or url_for('dashboard'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = get_connection()
    user_count = 0
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
        finally:
            conn.close()

    error = None
    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        email      = request.form.get('email', '').strip()
        password   = request.form.get('password', '')
        password2  = request.form.get('password2', '')
        department = request.form.get('department', '').strip()

        if not all([username, email, password]):
            error = 'All fields are required.'
        elif password != password2:
            error = 'Passwords do not match.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        else:
            role = 'admin' if user_count == 0 else 'doctor'
            uid  = create_user(username, email,
                               generate_password_hash(password),
                               role, department or None)
            if uid:
                flash(f'Account created! {"You are the system admin." if role=="admin" else ""}', 'success')
                return redirect(url_for('login'))
            error = 'Username or email already exists.'

    return render_template('register.html', error=error, first_user=(user_count == 0))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    stats = get_dashboard_stats()
    stats = stringify_datetimes(stats)
    recent = fetch_all_results(limit=5)
    for r in recent:
        try:
            r['results']     = json.loads(r['results'])
            r['analyzed_at'] = str(r['analyzed_at'])
        except Exception:
            pass
    recent = stringify_datetimes(recent)
    return render_template('dashboard.html', stats=stats, recent=recent,
                           now=datetime.now().strftime('%Y-%m-%d %H:%M'))


# ── Analysis ──────────────────────────────────────────────────────────────────

@app.route('/analyze-page')
@login_required
def analyze_page():
    patients = get_all_patients()
    patients = stringify_datetimes(patients)
    return render_template('analyze.html', patients=patients)


@app.route('/analyze', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
def analyze():
    data         = request.get_json()
    patient_name = data.get('patient_name', 'Anonymous').strip()
    raw_sequence = data.get('dna_sequence', '').strip()
    is_fasta     = data.get('is_fasta', False)
    ethnicity    = data.get('ethnicity', None)
    notes        = data.get('notes', '')
    patient_id   = data.get('patient_id') or None

    raw_sequence = ''.join(ch for ch in raw_sequence.upper()
                           if ch in 'ATCGNR\n> ')

    if not raw_sequence:
        return jsonify({"error": "No DNA sequence provided."}), 400

    sequence = parse_fasta(raw_sequence) if is_fasta else raw_sequence
    result   = analyze_dna(sequence, ethnicity=ethnicity)

    if "error" in result:
        return jsonify(result), 400

    save_result(
        patient_name, sequence[:500], json.dumps(result),
        patient_id=patient_id,
        notes=notes,
        analyzed_by=current_user.id
    )

    return jsonify({"patient_name": patient_name, **result})


@app.route('/upload-fasta', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def upload_fasta():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided."}), 400
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type. Upload .fasta, .fa, or .txt"}), 400
    content  = f.read().decode('utf-8', errors='ignore')
    sequence = parse_fasta(content)
    return jsonify({"sequence": sequence, "filename": secure_filename(f.filename)})


@app.route('/sample')
@login_required
def sample():
    sample_seq = (
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        "GTGCACCTGACTCCTGAGGAG"
        "ATCGATCGATCGATCGATCG"
        "AGGACGGTGCGGTGAGAGTGG"
        "ATCGATCGATCGATCGATCGATCG"
    )
    return jsonify({"sample_sequence": sample_seq})


@app.route('/report', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def report():
    data         = request.get_json()
    patient_name = data.get('patient_name', 'Anonymous').strip()
    raw_sequence = data.get('dna_sequence', '').strip()
    is_fasta     = data.get('is_fasta', False)
    ethnicity    = data.get('ethnicity')
    doctor_notes = data.get('notes', '')

    if not raw_sequence:
        return jsonify({"error": "No DNA sequence provided."}), 400

    sequence = parse_fasta(raw_sequence) if is_fasta else raw_sequence
    result   = analyze_dna(sequence, ethnicity=ethnicity)
    if "error" in result:
        return jsonify(result), 400

    result['patient_name']     = patient_name
    result['sequence_snippet'] = sequence[:120]
    result['doctor_notes']     = doctor_notes
    result['analyst']          = current_user.username
    result['department']       = current_user.department or 'Genomic Medicine'

    pdf_bytes = generate_pdf_report(result)
    safe_name = "".join(c for c in patient_name if c.isalnum() or c in ' _').strip().replace(' ', '_')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"DNA_Report_{safe_name}.pdf"
    )


# ── History ───────────────────────────────────────────────────────────────────

@app.route('/history')
@login_required
def history():
    records = fetch_all_results(
        analyzed_by=None if current_user.is_admin() else current_user.id
    )
    for r in records:
        try:
            r['results']     = json.loads(r['results'])
            r['analyzed_at'] = str(r['analyzed_at'])
        except Exception:
            pass
    records = stringify_datetimes(records)
    return render_template('history.html', records=records)


@app.route('/history/<int:rid>')
@login_required
def history_detail(rid):
    record = get_result_by_id(rid)
    if not record:
        flash('Record not found.', 'error')
        return redirect(url_for('history'))
    try:
        record['results']     = json.loads(record['results'])
        record['analyzed_at'] = str(record['analyzed_at'])
    except Exception:
        pass
    record = stringify_datetimes(record)
    return render_template('history_details.html', record=record)


@app.route('/history/<int:rid>/delete', methods=['POST'])
@login_required
def delete_history(rid):
    delete_result(rid)
    flash('Analysis record deleted.', 'success')
    return redirect(url_for('history'))


# ── Patients ──────────────────────────────────────────────────────────────────

@app.route('/patients')
@login_required
def patients():
    all_patients = get_all_patients()
    all_patients = stringify_datetimes(all_patients)
    return render_template('patients.html', patients=all_patients)


@app.route('/patients/new', methods=['GET', 'POST'])
@login_required
def new_patient():
    error = None
    if request.method == 'POST':
        f         = request.form
        full_name = f.get('full_name', '').strip()
        age       = f.get('age') or None
        gender    = f.get('gender') or None
        contact   = f.get('contact_info') or None

        if not full_name:
            error = 'Full name is required.'
        else:
            db_id = create_patient(
                full_name=full_name,
                age=int(age) if age else None,
                gender=gender,
                contact_info=contact,
            )
            if db_id:
                flash(f'Patient "{full_name}" added successfully.', 'success')
                return redirect(url_for('patients'))
            error = 'Could not save patient.'
    return render_template('patient_form.html', patient=None, error=error)


@app.route('/patients/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(pid):
    patient = get_patient_by_id(pid)
    if not patient:
        flash('Patient not found.', 'error')
        return redirect(url_for('patients'))
    patient = stringify_datetimes(patient)
    error = None
    if request.method == 'POST':
        f = request.form
        ok = update_patient(
            pid,
            f.get('full_name'),
            int(f.get('age')) if f.get('age') else None,
            f.get('gender') or None,
            f.get('contact_info') or None,
        )
        if ok:
            flash('Patient updated.', 'success')
            return redirect(url_for('patients'))
        error = 'Update failed.'
    return render_template('patient_form.html', patient=patient, error=error)


@app.route('/patients/<int:pid>/delete', methods=['POST'])
@login_required
def del_patient(pid):
    delete_patient(pid)
    flash('Patient deleted.', 'success')
    return redirect(url_for('patients'))


@app.route('/patients/<int:pid>/history')
@login_required
def patient_history(pid):
    patient = get_patient_by_id(pid)
    if not patient:
        flash('Patient not found.', 'error')
        return redirect(url_for('patients'))
    patient = stringify_datetimes(patient)
    records = get_analyses_by_patient(pid)
    records = stringify_datetimes(records)
    samples = get_samples_by_patient(pid)
    samples = stringify_datetimes(samples)
    return render_template('patient_history.html',
                           patient=patient, records=records, samples=samples)


# ── Samples ───────────────────────────────────────────────────────────────────

@app.route('/samples')
@login_required
def samples():
    all_samples = get_all_samples()
    all_samples = stringify_datetimes(all_samples)
    return render_template('samples.html', samples=all_samples)


@app.route('/samples/new', methods=['GET', 'POST'])
@login_required
def new_sample():
    error    = None
    patients = get_all_patients()
    if request.method == 'POST':
        f = request.form
        sid = create_sample(
            patient_id=f.get('patient_id') or None,
            sample_type=f.get('sample_type') or None,
            collection_date=f.get('collection_date') or None,
            file_name=f.get('file_name') or None,
            status=f.get('status', 'Pending'),
        )
        if sid:
            flash('Sample added.', 'success')
            return redirect(url_for('samples'))
        error = 'Could not save sample.'
    return render_template('sample_form.html', sample=None,
                           patients=patients, error=error)


# ── Genes ─────────────────────────────────────────────────────────────────────

@app.route('/genes')
@login_required
def genes():
    all_genes = get_all_genes()
    return render_template('genes.html', genes=all_genes)


@app.route('/genes/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_gene():
    error = None
    if request.method == 'POST':
        f   = request.form
        gid = create_gene(
            f.get('gene_name', '').strip(),
            f.get('chromosome') or None,
            f.get('gene_type') or None,
            f.get('description') or None,
        )
        if gid:
            flash('Gene added.', 'success')
            return redirect(url_for('genes'))
        error = 'Could not save gene.'
    return render_template('gene_form.html', gene=None, error=error)


# ── Diseases ──────────────────────────────────────────────────────────────────

@app.route('/diseases')
@login_required
def diseases():
    all_diseases = get_all_diseases()
    return render_template('diseases.html', diseases=all_diseases)


@app.route('/diseases/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_disease():
    error = None
    if request.method == 'POST':
        f   = request.form
        did = create_disease(
            f.get('disease_name', '').strip(),
            f.get('disease_type') or None,
            f.get('severity') or None,
            f.get('description') or None,
        )
        if did:
            flash('Disease added.', 'success')
            return redirect(url_for('diseases'))
        error = 'Could not save disease.'
    return render_template('disease_form.html', disease=None, error=error)


# ── Mutations ─────────────────────────────────────────────────────────────────

@app.route('/mutations')
@login_required
def mutation_library():
    page      = int(request.args.get('page', 1))
    search    = request.args.get('search', '')
    category  = request.args.get('category', '')
    mutations, total = get_mutations_paginated(page, 20, search, category=category)
    mutations  = stringify_datetimes(mutations)
    categories = get_mutation_categories()
    pages      = (total + 19) // 20
    return render_template('mutations.html',
        mutations=mutations, total=total, page=page, pages=pages,
        search=search, risk='', category=category, categories=categories)


@app.route('/mutations/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_mutation_route():
    error     = None
    sequences = get_all_sequences()
    if request.method == 'POST':
        f   = request.form
        mid = create_mutation(
            sequence_id=f.get('sequence_id') or None,
            mutation_type=f.get('mutation_type') or None,
            position=int(f['position']) if f.get('position') else None,
            original_base=f.get('original_base') or None,
            mutated_base=f.get('mutated_base') or None,
        )
        if mid:
            flash('Mutation added.', 'success')
            return redirect(url_for('mutation_library'))
        error = 'Could not add mutation.'
    return render_template('mutation_form.html', mutation=None,
                           sequences=sequences, error=error, categories=[])


@app.route('/mutations/<int:mid>/delete', methods=['POST'])
@login_required
@admin_required
def del_mutation(mid):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM Mutations WHERE mutation_id=%s", (mid,))
            conn.commit()
        finally:
            conn.close()
    flash('Mutation deleted.', 'success')
    return redirect(url_for('mutation_library'))


# ── Patient Analysis ──────────────────────────────────────────────────────────

@app.route('/analyses')
@login_required
def analyses():
    all_analyses = get_all_analyses()
    all_analyses = stringify_datetimes(all_analyses)
    return render_template('analyses.html', analyses=all_analyses)


@app.route('/analyses/new', methods=['GET', 'POST'])
@login_required
def new_analysis():
    error     = None
    samples   = get_all_samples()
    sequences = get_all_sequences()
    mutations = get_all_mutations()
    diseases  = get_all_diseases()
    if request.method == 'POST':
        f   = request.form
        aid = create_analysis(
            sample_id=f.get('sample_id') or None,
            sequence_id=f.get('sequence_id') or None,
            mutation_id=f.get('mutation_id') or None,
            disease_id=f.get('disease_id') or None,
            prediction_confidence=float(f['prediction_confidence']) if f.get('prediction_confidence') else None,
            result_summary=f.get('result_summary') or None,
        )
        if aid:
            flash('Analysis record created.', 'success')
            return redirect(url_for('analyses'))
        error = 'Could not save analysis.'
    return render_template('analysis_form.html',
        sample=None, samples=samples, sequences=sequences,
        mutations=mutations, diseases=diseases, error=error)


@app.route('/analyses/<int:aid>')
@login_required
def analysis_detail(aid):
    record = get_analysis_by_id(aid)
    if not record:
        flash('Analysis not found.', 'error')
        return redirect(url_for('analyses'))
    record = stringify_datetimes(record)
    return render_template('analysis_detail.html', record=record)


# ── Compare ───────────────────────────────────────────────────────────────────

@app.route('/compare')
@login_required
def compare():
    records = fetch_all_results(
        analyzed_by=None if current_user.is_admin() else current_user.id,
        limit=200
    )
    for r in records:
        try:
            r['results']     = json.loads(r['results'])
            r['analyzed_at'] = str(r['analyzed_at'])
        except Exception:
            pass
    records = stringify_datetimes(records)
    return render_template('compare.html', records=records)


# ── User Admin ────────────────────────────────────────────────────────────────

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = get_all_users()
    users = stringify_datetimes(users)
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(uid):
    if uid == current_user.id:
        flash("You can't deactivate your own account.", 'error')
    else:
        user = get_user_by_id(uid)
        toggle_user_active(uid, not user['is_active'])
        flash('User status updated.', 'success')
    return redirect(url_for('admin_users'))


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=os.getenv('FLASK_DEBUG', 'True') == 'True', port=5000)