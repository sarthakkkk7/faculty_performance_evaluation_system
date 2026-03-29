# 📊 Faculty Performance Evaluation System

A web-based platform for evaluating faculty performance with AI-driven insights, interactive dashboards, and secure authentication.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3-lightgrey)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)

---

## 🆕 Version 3.0 Features
* User Registration with Email OTP Verification
* Yearly & Department Comparison Charts
* AI Improvement Suggestions
* Strengths & Missing Data Detection
* Faculty Detail Modal with Charts
* CSV Export

---

## 📁 Project Structure

```text
faculty_system/
├── app.py # Main Flask backend
├── requirements.txt # Python dependencies
├── .env.example # Environment template
├── SCHEMA_V3.sql # Database schema
├── train_ml_model.py # Train ML model
├── import_data.py # Import CSV data
├── faculty_performance_complete_v2.csv
└── templates/
    ├── index.html
    ├── admin_dashboard.html
    └── faculty_dashboard.html
```
--- 

## 🚀 Quick Setup

### 1. Prerequisites
* Python 3.10+
* Supabase account (free)

### 2. Database Setup
* Create a Supabase project
* Run `SCHEMA_V3.sql` in the SQL Editor

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your Supabase URL and key
```

### 4. Install & Run
```bash
pip install -r requirements.txt
python train_ml_model.py
python import_data.py
python app.py
```
Access at: http://localhost:5000
---

## 🔐 Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Faculty | faculty1 | faculty123 |

---

## 📝 Registration

* Click "Register here"
* Fill in the details and submit
* Enter the OTP (emailed or shown in the terminal)
* Login with your new credentials

---

## 👨‍💼 Admin Features

* **Overview:** Key metrics, yearly trends, distribution charts
* **Yearly Reports:** Year-wise score breakdowns
* **Departments:** Cross-department comparisons
* **Faculty List:** Search, filter, view details, AI suggestions
* **Performance Data:** Filter, export to CSV
* **ML Predictor:** Predict performance category from metrics

---

## 👩‍🏫 Faculty Features

* Personal dashboard with career stats
* Score trend charts and radar chart
* Year-by-year performance records
* Personal AI suggestions

---

## ❓ Common Issues

| Issue | Solution |
|-------|----------|
| Missing .env variables | Copy .env.example to .env and fill in the values |
| ML model not loaded | Run `python train_ml_model.py` |
| No data | Run `python import_data.py` |
| OTP not received | Check terminal console (dev mode) or configure SMTP |

---

## 🏗️ Tech Stack

* **Backend:** Python Flask
* **Database:** Supabase (PostgreSQL)
* **ML:** Random Forest (93% accuracy)
* **Charts:** Chart.js
* **Auth:** Session-based + OTP

---

Happy evaluating! 🎓

