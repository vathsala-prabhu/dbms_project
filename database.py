import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

DB_CONFIG = {
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     int(os.getenv('DB_PORT', 3306)),
    'user':     os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'dna_analyzer'),
}

# ── Helpers ───────────────────────────────────────────────────

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"[DB] Connection error: {e}")
    return None


def convert_datetimes(row):
    if not row:
        return row
    for key, val in row.items():
        if isinstance(val, (datetime.datetime, datetime.date)):
            row[key] = str(val)
    return row


def convert_datetimes_list(rows):
    return [convert_datetimes(row) for row in rows]


# ── Init DB ───────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    if not conn:
        print("[DB] Could not initialise — check DB_CONFIG in .env")
        return
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                username      VARCHAR(80)  NOT NULL UNIQUE,
                email         VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(256) NOT NULL,
                role          ENUM('admin','doctor','researcher','viewer') DEFAULT 'doctor',
                department    VARCHAR(100),
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login    TIMESTAMP NULL,
                is_active     BOOLEAN DEFAULT TRUE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Genes (
                gene_id     INT AUTO_INCREMENT PRIMARY KEY,
                gene_name   VARCHAR(100) NOT NULL,
                chromosome  VARCHAR(10),
                gene_type   VARCHAR(50),
                description TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Sequences (
                sequence_id     INT AUTO_INCREMENT PRIMARY KEY,
                gene_id         INT,
                sequence_data   LONGTEXT NOT NULL,
                sequence_length INT,
                gc_content      FLOAT,
                FOREIGN KEY (gene_id) REFERENCES Genes(gene_id) ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Diseases (
                disease_id   INT AUTO_INCREMENT PRIMARY KEY,
                disease_name VARCHAR(150) NOT NULL,
                disease_type VARCHAR(80),
                severity     ENUM('Low','Medium','High','Critical'),
                description  TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Mutations (
                mutation_id   INT AUTO_INCREMENT PRIMARY KEY,
                sequence_id   INT,
                mutation_type VARCHAR(50),
                position      INT,
                original_base VARCHAR(10),
                mutated_base  VARCHAR(10),
                FOREIGN KEY (sequence_id) REFERENCES Sequences(sequence_id) ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Patients (
                patient_id      INT AUTO_INCREMENT PRIMARY KEY,
                full_name       VARCHAR(150) NOT NULL,
                age             INT,
                gender          ENUM('Male','Female','Other','Prefer not to say'),
                contact_info    VARCHAR(255),
                date_registered DATE DEFAULT (CURRENT_DATE)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Samples (
                sample_id       INT AUTO_INCREMENT PRIMARY KEY,
                patient_id      INT,
                sample_type     VARCHAR(80),
                collection_date DATE,
                file_name       VARCHAR(255),
                status          ENUM('Pending','Processing','Completed','Failed') DEFAULT 'Pending',
                FOREIGN KEY (patient_id) REFERENCES Patients(patient_id) ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Patient_Analysis (
                analysis_id           INT AUTO_INCREMENT PRIMARY KEY,
                sample_id             INT,
                sequence_id           INT,
                mutation_id           INT,
                disease_id            INT,
                analysis_date         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                prediction_confidence FLOAT,
                result_summary        TEXT,
                FOREIGN KEY (sample_id)   REFERENCES Samples(sample_id)     ON DELETE SET NULL,
                FOREIGN KEY (sequence_id) REFERENCES Sequences(sequence_id) ON DELETE SET NULL,
                FOREIGN KEY (mutation_id) REFERENCES Mutations(mutation_id) ON DELETE SET NULL,
                FOREIGN KEY (disease_id)  REFERENCES Diseases(disease_id)   ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                patient_id   INT,
                patient_name VARCHAR(150) NOT NULL,
                dna_sequence TEXT         NOT NULL,
                filename     VARCHAR(255),
                results      LONGTEXT     NOT NULL,
                notes        TEXT,
                analyzed_by  INT,
                analyzed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (analyzed_by) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        conn.commit()
        print("[DB] All tables created/verified.")
    except Error as e:
        print(f"[DB] Init error: {e}")
    finally:
        conn.close()


# ── Users ─────────────────────────────────────────────────────

def create_user(username, email, password_hash, role='doctor', department=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role, department) VALUES (%s,%s,%s,%s,%s)",
            (username, email, password_hash, role, department)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_user: {e}")
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND is_active=TRUE", (username,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def update_last_login(user_id):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def get_all_users():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, username, email, role, department, created_at, last_login, is_active FROM users ORDER BY created_at DESC")
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def toggle_user_active(user_id, active):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active=%s WHERE id=%s", (active, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Genes ─────────────────────────────────────────────────────

def create_gene(gene_name, chromosome=None, gene_type=None, description=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Genes (gene_name, chromosome, gene_type, description) VALUES (%s,%s,%s,%s)",
            (gene_name, chromosome, gene_type, description)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_gene: {e}")
        return None
    finally:
        conn.close()


def get_all_genes():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Genes ORDER BY gene_name")
        return cur.fetchall()
    finally:
        conn.close()


def get_gene_by_id(gene_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Genes WHERE gene_id=%s", (gene_id,))
        return cur.fetchone()
    finally:
        conn.close()


# ── Sequences ─────────────────────────────────────────────────

def create_sequence(sequence_data, gene_id=None, sequence_length=None, gc_content=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Sequences (gene_id, sequence_data, sequence_length, gc_content) VALUES (%s,%s,%s,%s)",
            (gene_id, sequence_data, sequence_length, gc_content)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_sequence: {e}")
        return None
    finally:
        conn.close()


def get_all_sequences():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT s.*, g.gene_name FROM Sequences s
            LEFT JOIN Genes g ON s.gene_id = g.gene_id
            ORDER BY s.sequence_id DESC
        """)
        return cur.fetchall()
    finally:
        conn.close()


def get_sequence_by_id(sequence_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Sequences WHERE sequence_id=%s", (sequence_id,))
        return cur.fetchone()
    finally:
        conn.close()


# ── Diseases ──────────────────────────────────────────────────

def create_disease(disease_name, disease_type=None, severity=None, description=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Diseases (disease_name, disease_type, severity, description) VALUES (%s,%s,%s,%s)",
            (disease_name, disease_type, severity, description)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_disease: {e}")
        return None
    finally:
        conn.close()


def get_all_diseases():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Diseases ORDER BY disease_name")
        return cur.fetchall()
    finally:
        conn.close()


def get_disease_by_id(disease_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Diseases WHERE disease_id=%s", (disease_id,))
        return cur.fetchone()
    finally:
        conn.close()


# ── Mutations ─────────────────────────────────────────────────

def create_mutation(sequence_id=None, mutation_type=None, position=None,
                    original_base=None, mutated_base=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Mutations (sequence_id, mutation_type, position, original_base, mutated_base) VALUES (%s,%s,%s,%s,%s)",
            (sequence_id, mutation_type, position, original_base, mutated_base)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_mutation: {e}")
        return None
    finally:
        conn.close()


def get_all_mutations():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT m.*, s.gc_content, s.sequence_length
            FROM Mutations m
            LEFT JOIN Sequences s ON m.sequence_id = s.sequence_id
            ORDER BY m.mutation_id DESC
        """)
        return cur.fetchall()
    finally:
        conn.close()


def get_mutation_by_id(mutation_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Mutations WHERE mutation_id=%s", (mutation_id,))
        return cur.fetchone()
    finally:
        conn.close()


def get_mutations_paginated(page=1, per_page=20, search='', risk='', category=''):
    conn = get_connection()
    if not conn: return [], 0
    try:
        cur = conn.cursor(dictionary=True)
        where, params = [], []
        if search:
            where.append("(m.mutation_type LIKE %s OR m.original_base LIKE %s OR m.mutated_base LIKE %s)")
            s = f"%{search}%"
            params += [s, s, s]
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        cur.execute(f"SELECT COUNT(*) as cnt FROM Mutations m {clause}", params)
        total = cur.fetchone()['cnt']
        offset = (page - 1) * per_page
        cur.execute(f"""
            SELECT m.*, s.gc_content, s.sequence_length
            FROM Mutations m
            LEFT JOIN Sequences s ON m.sequence_id = s.sequence_id
            {clause} ORDER BY m.mutation_id DESC LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        return cur.fetchall(), total
    finally:
        conn.close()


def get_mutation_categories():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT mutation_type FROM Mutations WHERE mutation_type IS NOT NULL ORDER BY mutation_type")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


# ── Patients ──────────────────────────────────────────────────

def create_patient(full_name, age=None, gender=None,
                   contact_info=None, date_registered=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Patients (full_name, age, gender, contact_info, date_registered) VALUES (%s,%s,%s,%s,%s)",
            (full_name, age, gender, contact_info,
             date_registered or datetime.date.today())
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_patient: {e}")
        return None
    finally:
        conn.close()


def get_all_patients(created_by=None):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p.*,
              (SELECT COUNT(*) FROM Samples s WHERE s.patient_id = p.patient_id) as sample_count,
              (SELECT COUNT(*) FROM Patient_Analysis pa
               JOIN Samples s ON pa.sample_id = s.sample_id
               WHERE s.patient_id = p.patient_id) as analysis_count
            FROM Patients p ORDER BY p.date_registered DESC
        """)
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def get_patient_by_id(pid):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Patients WHERE patient_id=%s", (pid,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def update_patient(pid, full_name, age, gender, contact_info):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE Patients SET full_name=%s, age=%s, gender=%s, contact_info=%s WHERE patient_id=%s",
            (full_name, age, gender, contact_info, pid)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_patient(pid):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM Patients WHERE patient_id=%s", (pid,))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Samples ───────────────────────────────────────────────────

def create_sample(patient_id, sample_type=None, collection_date=None,
                  file_name=None, status='Pending'):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Samples (patient_id, sample_type, collection_date, file_name, status) VALUES (%s,%s,%s,%s,%s)",
            (patient_id, sample_type, collection_date, file_name, status)
        )
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_sample: {e}")
        return None
    finally:
        conn.close()


def get_samples_by_patient(patient_id):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Samples WHERE patient_id=%s ORDER BY collection_date DESC", (patient_id,))
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def get_all_samples():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT s.*, p.full_name as patient_name
            FROM Samples s
            LEFT JOIN Patients p ON s.patient_id = p.patient_id
            ORDER BY s.collection_date DESC
        """)
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def get_sample_by_id(sample_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Samples WHERE sample_id=%s", (sample_id,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def update_sample_status(sample_id, status):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Samples SET status=%s WHERE sample_id=%s", (status, sample_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Patient Analysis ──────────────────────────────────────────

def create_analysis(sample_id=None, sequence_id=None, mutation_id=None,
                    disease_id=None, prediction_confidence=None,
                    result_summary=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Patient_Analysis
              (sample_id, sequence_id, mutation_id, disease_id,
               prediction_confidence, result_summary)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (sample_id, sequence_id, mutation_id, disease_id,
              prediction_confidence, result_summary))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] create_analysis: {e}")
        return None
    finally:
        conn.close()


def get_all_analyses():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT pa.*,
              p.full_name as patient_name,
              s.sample_type, s.status as sample_status,
              d.disease_name, d.severity,
              m.mutation_type, m.position
            FROM Patient_Analysis pa
            LEFT JOIN Samples s    ON pa.sample_id   = s.sample_id
            LEFT JOIN Patients p   ON s.patient_id   = p.patient_id
            LEFT JOIN Diseases d   ON pa.disease_id  = d.disease_id
            LEFT JOIN Mutations m  ON pa.mutation_id = m.mutation_id
            ORDER BY pa.analysis_date DESC
        """)
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def get_analysis_by_id(analysis_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT pa.*,
              p.full_name as patient_name,
              s.sample_type, s.file_name,
              d.disease_name, d.severity, d.disease_type,
              m.mutation_type, m.position, m.original_base, m.mutated_base,
              seq.sequence_length, seq.gc_content
            FROM Patient_Analysis pa
            LEFT JOIN Samples s     ON pa.sample_id   = s.sample_id
            LEFT JOIN Patients p    ON s.patient_id   = p.patient_id
            LEFT JOIN Diseases d    ON pa.disease_id  = d.disease_id
            LEFT JOIN Mutations m   ON pa.mutation_id = m.mutation_id
            LEFT JOIN Sequences seq ON pa.sequence_id = seq.sequence_id
            WHERE pa.analysis_id=%s
        """, (analysis_id,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def get_analyses_by_patient(patient_id):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT pa.*, d.disease_name, d.severity, m.mutation_type
            FROM Patient_Analysis pa
            LEFT JOIN Samples s   ON pa.sample_id  = s.sample_id
            LEFT JOIN Diseases d  ON pa.disease_id = d.disease_id
            LEFT JOIN Mutations m ON pa.mutation_id = m.mutation_id
            WHERE s.patient_id=%s
            ORDER BY pa.analysis_date DESC
        """, (patient_id,))
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


# ── analysis_results (app history) ───────────────────────────

def fetch_all_mutations():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Mutations ORDER BY mutation_id")
        return cur.fetchall()
    finally:
        conn.close()


def save_result(patient_name, dna_sequence, results_json,
                patient_id=None, filename=None, notes=None, analyzed_by=None):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO analysis_results
              (patient_id, patient_name, dna_sequence, filename, results, notes, analyzed_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (patient_id, patient_name, dna_sequence[:500],
              filename, results_json, notes, analyzed_by))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"[DB] save_result: {e}")
        return None
    finally:
        conn.close()


def fetch_all_results(analyzed_by=None, patient_id=None, limit=100):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        where, params = [], []
        if analyzed_by:
            where.append("r.analyzed_by=%s"); params.append(analyzed_by)
        if patient_id:
            where.append("r.patient_id=%s"); params.append(patient_id)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        cur.execute(f"""
            SELECT r.*, u.username as analyst_name
            FROM analysis_results r
            LEFT JOIN users u ON r.analyzed_by=u.id
            {clause}
            ORDER BY r.analyzed_at DESC LIMIT %s
        """, params + [limit])
        return convert_datetimes_list(cur.fetchall())
    finally:
        conn.close()


def get_result_by_id(rid):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM analysis_results WHERE id=%s", (rid,))
        return convert_datetimes(cur.fetchone())
    finally:
        conn.close()


def delete_result(rid):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis_results WHERE id=%s", (rid,))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Dashboard Stats ───────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    if not conn: return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as c FROM Patients");         patients  = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM Patient_Analysis"); analyses  = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM Mutations");        mutations = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM users WHERE is_active=TRUE"); users = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM Genes");            genes     = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM Diseases");         diseases  = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM Samples");          samples   = cur.fetchone()['c']

        cur.execute("""
            SELECT JSON_EXTRACT(results, '$.risk_summary.overall_risk') as risk,
                   COUNT(*) as cnt
            FROM analysis_results GROUP BY risk
        """)
        risk_dist = {
            r['risk'].strip('"') if r['risk'] else 'Unknown': r['cnt']
            for r in cur.fetchall()
        }

        cur.execute("""
            SELECT patient_name, analyzed_at,
              JSON_EXTRACT(results,'$.risk_summary.overall_risk') as risk
            FROM analysis_results ORDER BY analyzed_at DESC LIMIT 5
        """)
        recent = convert_datetimes_list(cur.fetchall())

        return {
            'patients': patients, 'analyses': analyses,
            'mutations': mutations, 'users': users,
            'genes': genes, 'diseases': diseases, 'samples': samples,
            'risk_distribution': risk_dist, 'recent_analyses': recent,
        }
    finally:
        conn.close()
