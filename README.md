# 🧬 GenomePath — Clinical DNA Mutation Analyzer

A web-based clinical DNA mutation analysis platform built with **Python Flask** and **MySQL**. GenomePath allows medical professionals to analyze DNA sequences, detect mutations, assess disease risks, and generate detailed PDF reports.

---

## 📋 Table of Contents

- [About the Project](#about-the-project)
- [Tech Stack](#tech-stack)
- [Database Schema](#database-schema)
- [Features](#features)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [Disclaimer](#disclaimer)

---

## 📖 About the Project

GenomePath is a DBMS mini-project that demonstrates a full-stack clinical application for DNA sequence analysis. It allows doctors and researchers to:

- Upload and analyze DNA sequences
- Detect known mutations and assess risk levels
- Manage patient records and sample data
- Generate downloadable PDF reports
- Compare multiple analysis results side by side

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python 3, Flask |
| Database | MySQL (via XAMPP) |
| DNA Analysis | Biopython |
| Authentication | Flask-Login |
| PDF Generation | ReportLab |
| DB Connector | mysql-connector-python |
| Rate Limiting | Flask-Limiter |

---

## 🗃 Database Schema

The project uses **7 core tables**:

```
Genes ──────────── Sequences ──────────── Mutations
                       │                      │
                       └──────────────────────┘
                                               │
Patients ──── Samples ──── Patient_Analysis ───┘
                                │
                            Diseases
```

| Table | Primary Key | Description |
|---|---|---|
| Genes | gene_id | Gene information (name, chromosome, type) |
| Sequences | sequence_id | DNA sequence data linked to genes |
| Diseases | disease_id | Disease catalog with severity levels |
| Mutations | mutation_id | Mutation records linked to sequences |
| Patients | patient_id | Patient demographic information |
| Samples | sample_id | Biological samples collected from patients |
| Patient_Analysis | analysis_id | Analysis results linking all entities |

---

## ✨ Features

- 🔬 **DNA Sequence Analysis** — Detect mutations from raw or FASTA sequences
- 👤 **Patient Management** — Add, edit, and track patient records
- 🧫 **Mutation Library** — Browse and manage the mutation reference database
- 📊 **Dashboard** — Overview of patients, analyses, and risk distribution
- 📋 **Analysis History** — View and filter past analysis records
- ⚖️ **Compare Results** — Side-by-side comparison of two analyses
- 💊 **Pharmacogenomics** — Drug interaction warnings based on genetic variants
- ⬇️ **PDF Reports** — Downloadable clinical reports for each analysis
- 🔐 **Authentication** — Role-based access (Admin, Doctor, Researcher, Viewer)
- 🧬 **Zygosity Detection** — Homozygous vs Heterozygous mutation detection
- 🌍 **Population Risk** — Ethnicity-based risk modifiers

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- XAMPP (for MySQL)
- Git

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/YourUsername/dbms_project.git
cd dbms_project
```

**2. Create and activate virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install flask flask-login flask-limiter biopython reportlab python-dotenv mysql-connector-python
```

**4. Set up environment variables**

Create a `.env` file in the root directory:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=dna_analyzer
SECRET_KEY=your-secret-key-here
```

**5. Set up the database**

- Start XAMPP and ensure MySQL is running
- Open phpMyAdmin at `http://localhost/phpmyadmin`
- Create a database named `dna_analyzer`
- Run the SQL from `sample_data.sql` to create and populate tables

**6. Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

**7. Register your first account**

The first registered user is automatically granted **Admin** privileges.

---

## 📁 Project Structure

```
dbms_project/
├── app.py                  # Main Flask application & routes
├── analyzer.py             # DNA sequence analysis logic
├── database.py             # Database connection & queries
├── report_generator.py     # PDF report generation
├── .env                    # Environment variables (not in repo)
├── static/
│   ├── style.css           # Stylesheet
│   └── script.js           # Frontend JavaScript
└── templates/
    ├── base.html           # Base layout template
    ├── dashboard.html      # Dashboard page
    ├── analyze.html        # DNA analysis page
    ├── patients.html       # Patient list
    ├── patient_form.html   # Add/edit patient
    ├── patient_history.html# Patient analysis history
    ├── history.html        # All analysis history
    ├── history_details.html# Single analysis detail
    ├── mutations.html      # Mutation library
    ├── mutation_form.html  # Add mutation form
    ├── compare.html        # Compare analyses
    ├── admin_users.html    # User management
    ├── login.html          # Login page
    └── register.html       # Registration page
```

---

## ⚠️ Disclaimer

> This project is built for **educational and research purposes only** as part of a DBMS course project. It is **not intended for real clinical use**. Do not use this as a substitute for professional genetic testing or medical advice.

---

## 👨‍💻 Author

Built as a DBMS mini-project using Flask + MySQL + Biopython.