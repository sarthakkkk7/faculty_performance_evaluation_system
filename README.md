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