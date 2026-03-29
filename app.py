#!/usr/bin/env python3
"""
Faculty Performance Evaluation System v3.0
Enhanced with: Registration, Email Verification, Yearly Graphs,
               Improvement Suggestions, Document Verification (base64 DB storage)
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import json
import os
import joblib
import smtplib
import random
import string
import csv
import base64
import uuid as uuid_lib
from datetime import datetime, timedelta
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'faculty-perf-2026-ultra-secret')
CORS(app, supports_credentials=True)

# ─────────────────────────── SUPABASE ────────────────────────────
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    raise ValueError('❌ Set SUPABASE_URL and SUPABASE_KEY in .env file')

supabase: Client = create_client(supabase_url, supabase_key)
print('✓ Supabase connected')

# ─────────────────────────── ML MODEL ────────────────────────────
ml_model = ml_scaler = ml_encoder = ml_metadata = None

def load_ml_model():
    global ml_model, ml_scaler, ml_encoder, ml_metadata
    try:
        if os.path.exists('ml_model.pkl'):
            ml_model    = joblib.load('ml_model.pkl')
            ml_scaler   = joblib.load('scaler.pkl')
            ml_encoder  = joblib.load('label_encoder.pkl')
            with open('model_metadata.json') as f:
                ml_metadata = json.load(f)
            print(f'✓ ML Model loaded — Accuracy: {ml_metadata.get("accuracy",0)*100:.1f}%')
    except Exception as e:
        print(f'⚠ ML load error: {e}')

load_ml_model()

# ─────────────────────────── EMAIL ───────────────────────────────
SMTP_HOST    = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT    = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER    = os.environ.get('SMTP_USER', '')
SMTP_PASS    = os.environ.get('SMTP_PASS', '')
SMTP_FROM    = os.environ.get('SMTP_FROM', SMTP_USER)
SMTP_ENABLED = bool(SMTP_USER and SMTP_PASS)

# In-memory OTP store  {email: {otp, expires, pending_user}}
otp_store = {}

def send_otp_email(to_email: str, otp: str, name: str = '') -> bool:
    if not SMTP_ENABLED:
        print(f'[DEV MODE] OTP for {to_email}: {otp}')
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🎓 Verify Your Email — Faculty Performance System'
        msg['From']    = SMTP_FROM
        msg['To']      = to_email
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:30px;
                    background:#f9fafb;border-radius:12px;">
          <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:25px;
                      border-radius:10px;text-align:center;">
            <h2 style="color:#e94560;margin:0;">📊 Faculty Performance System</h2>
          </div>
          <div style="background:white;padding:30px;border-radius:10px;margin-top:15px;">
            <p style="color:#333;">Hello <strong>{name}</strong>,</p>
            <p style="color:#555;">Your email verification code is:</p>
            <div style="background:#1a1a2e;color:#e94560;font-size:36px;font-weight:bold;
                        text-align:center;padding:20px;border-radius:8px;letter-spacing:8px;
                        margin:20px 0;">{otp}</div>
            <p style="color:#888;font-size:13px;">This code expires in <strong>10 minutes</strong>.</p>
            <p style="color:#888;font-size:12px;">If you didn't request this, ignore this email.</p>
          </div>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

# ─────────────────────────── DECORATORS ──────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        if session['user'].get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        return f(*a, **kw)
    return d

def faculty_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        if session['user'].get('role') != 'faculty':
            return jsonify({'error': 'Faculty only'}), 403
        return f(*a, **kw)
    return d

# ─────────────────────────── HELPERS ─────────────────────────────
def calculate_overall_score(teaching_rating, student_feedback, research_score, administration_score):
    score = (float(teaching_rating)     * 0.35 +
             float(student_feedback)    * 0.20 +
             float(research_score)      * 0.25 +
             float(administration_score)* 0.20)
    return round(score, 2)

def get_performance_category(overall_score):
    s = float(overall_score)
    if s >= 4.0:   return 'Excellent'
    elif s >= 3.0: return 'Good'
    elif s >= 2.0: return 'Average'
    else:          return 'Needs Improvement'

def append_to_csv(faculty_data, perf_data):
    csv_path = 'faculty_performance_complete_v2.csv'
    row = {
        'Faculty_ID':               faculty_data['faculty_id'],
        'Name':                     faculty_data['name'],
        'Department':               faculty_data['department'],
        'Designation':              faculty_data.get('designation', ''),
        'Year':                     perf_data['year'],
        'Teaching_Hours':           perf_data['teaching_hours'],
        'Student_Feedback':         perf_data['student_feedback'],
        'Subjects_Handled':         '[]',
        'Publications':             perf_data['publications'],
        'Citations':                perf_data['citations'],
        'Research_Score':           perf_data['research_score'],
        'Projects_Completed':       perf_data['projects_completed'],
        'Certifications':           '[]',
        'Workshops':                '[]',
        'Experience_Years':         perf_data['experience_years'],
        'Teaching_Rating':          perf_data['teaching_rating'],
        'Students_Mentored':        perf_data['students_mentored'],
        'Institutional_Activities': '{}',
        'Administration_Score':     perf_data['administration_score'],
        'Overall_Score':            perf_data['overall_score'],
        'Performance_Label':        perf_data['performance_category']
    }
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"   ✓ CSV updated: {faculty_data['faculty_id']}")

# ─────────────────────────── INIT DEMO USERS ─────────────────────
def init_demo_users():
    try:
        chk = supabase.table('users').select('id').eq('username', 'admin').execute()
        if not chk.data:
            supabase.table('users').insert({
                'username': 'admin', 'password': generate_password_hash('admin123'),
                'email': 'admin@university.edu', 'role': 'admin',
                'full_name': 'System Administrator', 'department': 'Administration',
                'email_verified': True
            }).execute()
            supabase.table('users').insert({
                'username': 'faculty1', 'password': generate_password_hash('faculty123'),
                'email': 'faculty1@university.edu', 'role': 'faculty',
                'faculty_id': 'FAC0001', 'full_name': 'Dr. Rajesh Sharma',
                'department': 'Computer Science', 'email_verified': True
            }).execute()
            print('✓ Demo users created')
        else:
            print('✓ Demo users exist')
    except Exception as e:
        print(f'Init note: {str(e)[:80]}')

with app.app_context():
    init_demo_users()

# ═══════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    res = supabase.table('users').select('*').eq('username', username).execute()
    if not res.data:
        return jsonify({'error': 'Invalid credentials'}), 401
    user = res.data[0]
    if not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user.get('email_verified', False):
        return jsonify({'error': 'Please verify your email first. Check your inbox.'}), 403
    session['user'] = {
        'id': user.get('id'), 'username': user.get('username'),
        'role': user.get('role'), 'email': user.get('email'),
        'faculty_id': user.get('faculty_id'), 'full_name': user.get('full_name'),
        'department': user.get('department')
    }
    return jsonify({'success': True, 'user': session['user']}), 200


@app.route('/api/auth/register', methods=['POST'])
def register():
    data      = request.get_json()
    username  = data.get('username', '').strip()
    email     = data.get('email', '').strip().lower()
    password  = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role      = data.get('role', 'faculty')
    dept      = data.get('department', '')
    faculty_id = data.get('faculty_id', '')

    if not all([username, email, password, full_name]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if role not in ('admin', 'faculty'):
        return jsonify({'error': 'Invalid role'}), 400

    if supabase.table('users').select('id').eq('username', username).execute().data:
        return jsonify({'error': 'Username already taken'}), 409
    if supabase.table('users').select('id').eq('email', email).execute().data:
        return jsonify({'error': 'Email already registered'}), 409

    otp = generate_otp()
    otp_store[email] = {
        'otp': otp,
        'expires': datetime.now() + timedelta(minutes=10),
        'pending_user': {
            'username': username, 'password': generate_password_hash(password),
            'email': email, 'role': role, 'full_name': full_name,
            'department': dept,
            'faculty_id': faculty_id if role == 'faculty' else None,
            'email_verified': False
        }
    }
    sent = send_otp_email(email, otp, full_name)
    msg  = 'OTP sent to your email!' if sent else f'[DEV] OTP: {otp} (email disabled)'
    return jsonify({'success': True, 'message': msg,
                    'dev_otp': otp if not SMTP_ENABLED else None}), 200


@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    otp   = data.get('otp', '').strip()
    if email not in otp_store:
        return jsonify({'error': 'No pending registration for this email'}), 400
    record = otp_store[email]
    if datetime.now() > record['expires']:
        del otp_store[email]
        return jsonify({'error': 'OTP expired. Please register again'}), 400
    if record['otp'] != otp:
        return jsonify({'error': 'Invalid OTP'}), 400
    user_data = record['pending_user']
    user_data['email_verified'] = True
    supabase.table('users').insert(user_data).execute()
    del otp_store[email]
    return jsonify({'success': True, 'message': 'Account created! You can now login.'}), 200


@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    if email not in otp_store:
        return jsonify({'error': 'No pending registration'}), 400
    otp = generate_otp()
    otp_store[email]['otp']     = otp
    otp_store[email]['expires'] = datetime.now() + timedelta(minutes=10)
    name = otp_store[email]['pending_user']['full_name']
    send_otp_email(email, otp, name)
    return jsonify({'success': True, 'message': 'New OTP sent!',
                    'dev_otp': otp if not SMTP_ENABLED else None}), 200


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True}), 200


@app.route('/api/auth/user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({'user': session.get('user')}), 200


# ═══════════════════════════════════════════════════════
#  FACULTY PROFILE & PERFORMANCE
# ═══════════════════════════════════════════════════════

@app.route('/api/faculty/check-profile', methods=['GET'])
@faculty_required
def check_profile():
    fid = session['user'].get('faculty_id')
    if not fid:
        return jsonify({'needs_setup': True}), 200
    fac = supabase.table('faculty').select('faculty_id').eq('faculty_id', fid).execute()
    return jsonify({'needs_setup': not bool(fac.data)}), 200


@app.route('/api/faculty/setup-profile', methods=['POST'])
@faculty_required
def setup_profile():
    try:
        data = request.get_json()
        user = session['user']

        fac_res    = supabase.table('faculty').select('faculty_id').execute()
        fac_num    = len(fac_res.data or []) + 1
        faculty_id = f"FAC{str(fac_num).zfill(4)}"

        overall  = calculate_overall_score(
            data.get('teaching_rating', 3), data.get('student_feedback', 3),
            data.get('research_score', 3),  data.get('administration_score', 3))
        category = get_performance_category(overall)

        faculty_data = {
            'faculty_id':  faculty_id,
            'name':        data.get('name', user.get('full_name')),
            'department':  data.get('department', ''),
            'designation': data.get('designation', ''),
            'email':       user.get('email', '')
        }
        supabase.table('faculty').insert(faculty_data).execute()

        perf_data = {
            'faculty_id':           faculty_id,
            'year':                 int(data.get('year', datetime.now().year)),
            'teaching_hours':       float(data.get('teaching_hours', 0)),
            'student_feedback':     float(data.get('student_feedback', 3)),
            'teaching_rating':      float(data.get('teaching_rating', 3)),
            'publications':         int(data.get('publications', 0)),
            'citations':            int(data.get('citations', 0)),
            'research_score':       float(data.get('research_score', 3)),
            'projects_completed':   int(data.get('projects_completed', 0)),
            'experience_years':     int(data.get('experience_years', 0)),
            'students_mentored':    int(data.get('students_mentored', 0)),
            'administration_score': float(data.get('administration_score', 3)),
            'overall_score':        overall,
            'performance_category': category
        }
        supabase.table('performance').insert(perf_data).execute()
        supabase.table('users').update({'faculty_id': faculty_id}).eq('id', user['id']).execute()
        session['user']['faculty_id'] = faculty_id
        append_to_csv(faculty_data, perf_data)

        return jsonify({
            'success': True, 'faculty_id': faculty_id,
            'overall_score': overall, 'category': category,
            'message': f'Profile created! Your Faculty ID is {faculty_id}'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty/add-performance', methods=['POST'])
@faculty_required
def add_performance_record():
    try:
        data = request.get_json()
        fid  = session['user'].get('faculty_id')
        if not fid:
            return jsonify({'error': 'Profile not set up yet'}), 400

        overall  = calculate_overall_score(
            data.get('teaching_rating', 3), data.get('student_feedback', 3),
            data.get('research_score', 3),  data.get('administration_score', 3))
        category = get_performance_category(overall)

        perf_data = {
            'faculty_id':           fid,
            'year':                 int(data.get('year', datetime.now().year)),
            'teaching_hours':       float(data.get('teaching_hours', 0)),
            'student_feedback':     float(data.get('student_feedback', 3)),
            'teaching_rating':      float(data.get('teaching_rating', 3)),
            'publications':         int(data.get('publications', 0)),
            'citations':            int(data.get('citations', 0)),
            'research_score':       float(data.get('research_score', 3)),
            'projects_completed':   int(data.get('projects_completed', 0)),
            'experience_years':     int(data.get('experience_years', 0)),
            'students_mentored':    int(data.get('students_mentored', 0)),
            'administration_score': float(data.get('administration_score', 3)),
            'overall_score':        overall,
            'performance_category': category
        }
        supabase.table('performance').upsert(perf_data).execute()

        fac_res = supabase.table('faculty').select('*').eq('faculty_id', fid).execute()
        if fac_res.data:
            append_to_csv(fac_res.data[0], perf_data)

        return jsonify({'success': True, 'overall_score': overall, 'category': category}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty/profile', methods=['GET'])
@faculty_required
def get_faculty_profile():
    fid = session['user'].get('faculty_id')
    if not fid:
        return jsonify({'error': 'No faculty ID linked'}), 400
    try:
        fac  = supabase.table('faculty').select('*').eq('faculty_id', fid).execute()
        perf = supabase.table('performance').select('*').eq('faculty_id', fid).order('year').execute()
        return jsonify({'faculty': fac.data[0] if fac.data else {}, 'performance': perf.data or []}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty/performance', methods=['GET'])
@faculty_required
def get_faculty_performance():
    fid = session['user'].get('faculty_id')
    try:
        res = supabase.table('performance').select('*').eq('faculty_id', fid).order('year').execute()
        return jsonify({'performance': res.data or []}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════
#  DOCUMENT UPLOAD & RETRIEVAL  (base64 stored in DB)
# ═══════════════════════════════════════════════════════

@app.route('/api/faculty/upload-document', methods=['POST'])
@login_required
def upload_document():
    """Store document metadata + base64 file data directly in Supabase DB."""
    try:
        data        = request.get_json()
        fid         = session['user'].get('faculty_id')
        doc_type    = data.get('doc_type')
        title       = data.get('title', '')
        description = data.get('description', '')
        journal     = data.get('journal_name', '')
        pub_date    = data.get('publication_date', '')
        year        = int(data.get('year', datetime.now().year))
        file_b64    = data.get('file_b64', '')
        file_name   = data.get('file_name', '')
        file_type   = data.get('file_type', '')

        if not fid:
            return jsonify({'error': 'Profile not set up yet'}), 400
        if not doc_type or not title:
            return jsonify({'error': 'Document type and title are required'}), 400

        doc_data = {
            'faculty_id':       fid,
            'year':             year,
            'doc_type':         doc_type,
            'title':            title,
            'description':      description,
            'journal_name':     journal,
            'publication_date': pub_date,
            'file_name':        file_name,
            'file_data':        file_b64 if file_b64 else None,
            'file_type':        file_type if file_type else None,
            'file_url':         None,
            'verified_status':  'pending'
        }
        res = supabase.table('faculty_documents').insert(doc_data).execute()

        return jsonify({
            'success': True,
            'doc_id':  res.data[0]['id'] if res.data else None,
            'message': 'Document submitted for admin verification'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<int:doc_id>/file', methods=['GET'])
@login_required
def get_document_file(doc_id):
    """Return base64 file data so admin/faculty can view the file."""
    try:
        u   = session['user']
        res = supabase.table('faculty_documents').select('*').eq('id', doc_id).execute()
        if not res.data:
            return jsonify({'error': 'Document not found'}), 404

        doc = res.data[0]

        # Faculty can only view their own docs
        if u['role'] == 'faculty' and u.get('faculty_id') != doc['faculty_id']:
            return jsonify({'error': 'Access denied'}), 403

        if not doc.get('file_data'):
            return jsonify({'error': 'No file uploaded for this document'}), 404

        return jsonify({
            'file_data': doc['file_data'],
            'file_type': doc.get('file_type', 'application/pdf'),
            'file_name': doc.get('file_name', 'document')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty/documents/<faculty_id>', methods=['GET'])
@login_required
def get_faculty_documents(faculty_id):
    u = session['user']
    if u['role'] == 'faculty' and u.get('faculty_id') != faculty_id:
        return jsonify({'error': 'Access denied'}), 403
    try:
        year = request.args.get('year')
        q = supabase.table('faculty_documents').select(
            'id,faculty_id,year,doc_type,title,description,journal_name,'
            'publication_date,file_name,file_type,file_url,verified_status,admin_remark,created_at,file_data'
        ).eq('faculty_id', faculty_id).order('created_at', desc=True)
        if year:
            q = q.eq('year', int(year))
        res = q.execute()
        docs = []
        for d in (res.data or []):
            # has_file = True only if file_data actually has content
            d['has_file'] = bool(d.get('file_data'))
            # Don't send file_data in list view (too heavy) — only flag
            d.pop('file_data', None)
            docs.append(d)
        return jsonify({'documents': docs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/faculty/documents/<int:doc_id>', methods=['DELETE'])
@faculty_required
def delete_document(doc_id):
    try:
        fid = session['user'].get('faculty_id')
        supabase.table('faculty_documents').delete().eq('id', doc_id).eq('faculty_id', fid).execute()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════
#  ADMIN — DOCUMENT VERIFICATION
# ═══════════════════════════════════════════════════════

@app.route('/api/admin/documents', methods=['GET'])
@admin_required
def get_all_documents():
    try:
        status   = request.args.get('status', '')
        fid      = request.args.get('faculty_id', '')
        doc_type = request.args.get('doc_type', '')

        # Select file_data to check has_file, but we'll strip it before returning
        q = supabase.table('faculty_documents').select(
            'id,faculty_id,year,doc_type,title,description,journal_name,'
            'publication_date,file_name,file_type,file_url,verified_status,admin_remark,created_at,file_data'
        ).order('created_at', desc=True)
        if status:   q = q.eq('verified_status', status)
        if fid:      q = q.eq('faculty_id', fid)
        if doc_type: q = q.eq('doc_type', doc_type)
        res  = q.execute()
        docs = res.data or []

        fac_res = supabase.table('faculty').select('faculty_id,name,department').execute()
        fac_map = {f['faculty_id']: f for f in (fac_res.data or [])}

        result = []
        for d in docs:
            # Set has_file based on actual file_data content
            d['has_file'] = bool(d.get('file_data'))
            # Strip file_data from list response (send it only via /api/documents/<id>/file)
            d.pop('file_data', None)
            fac = fac_map.get(d['faculty_id'], {})
            d['faculty_name'] = fac.get('name', 'Unknown')
            d['department']   = fac.get('department', '—')
            result.append(d)

        return jsonify({'documents': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/documents/<int:doc_id>/verify', methods=['POST'])
@admin_required
def verify_document(doc_id):
    try:
        data   = request.get_json()
        status = data.get('status')
        remark = data.get('remark', '')
        if status not in ('verified', 'rejected'):
            return jsonify({'error': 'Status must be verified or rejected'}), 400
        supabase.table('faculty_documents').update({
            'verified_status': status, 'admin_remark': remark
        }).eq('id', doc_id).execute()
        return jsonify({'success': True, 'status': status}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/documents/stats', methods=['GET'])
@admin_required
def document_stats():
    try:
        res  = supabase.table('faculty_documents').select('verified_status').execute()
        docs = res.data or []
        return jsonify({
            'pending':  sum(1 for d in docs if d['verified_status'] == 'pending'),
            'verified': sum(1 for d in docs if d['verified_status'] == 'verified'),
            'rejected': sum(1 for d in docs if d['verified_status'] == 'rejected'),
            'total':    len(docs)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════
#  ADMIN — FACULTY MANAGEMENT
# ═══════════════════════════════════════════════════════

@app.route('/api/admin/faculty', methods=['GET'])
@admin_required
def get_faculty_list():
    try:
        dept = request.args.get('department')
        q    = supabase.table('faculty').select('*').order('name')
        if dept: q = q.eq('department', dept)
        res  = q.execute()
        return jsonify({'faculty': res.data or []}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/faculty/<faculty_id>', methods=['GET'])
@admin_required
def get_faculty_detail(faculty_id):
    try:
        fac  = supabase.table('faculty').select('*').eq('faculty_id', faculty_id).execute()
        perf = supabase.table('performance').select('*').eq('faculty_id', faculty_id).order('year').execute()
        if not fac.data:
            return jsonify({'error': 'Faculty not found'}), 404
        return jsonify({'faculty': fac.data[0], 'performance': perf.data or []}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    try:
        fac   = supabase.table('faculty').select('faculty_id').execute()
        perf  = supabase.table('performance').select('overall_score,performance_category,year').execute()
        perfs = perf.data or []
        scores = [p['overall_score'] for p in perfs if p.get('overall_score')]
        cats   = {}
        for p in perfs:
            c = p.get('performance_category', 'Unknown')
            cats[c] = cats.get(c, 0) + 1
        year_data = {}
        for p in perfs:
            yr, sc = p.get('year'), p.get('overall_score')
            if yr and sc:
                year_data.setdefault(yr, []).append(sc)
        yearly_avg = {yr: round(sum(v)/len(v), 2) for yr, v in year_data.items()}
        return jsonify({
            'total_faculty': len(fac.data or []),
            'total_records': len(perfs),
            'avg_score':     round(sum(scores)/len(scores), 2) if scores else 0,
            'category_distribution': cats,
            'yearly_averages': yearly_avg
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/yearly-report', methods=['GET'])
@admin_required
def yearly_report():
    try:
        perf = supabase.table('performance').select(
            'faculty_id,year,overall_score,teaching_rating,research_score,'
            'administration_score,publications,citations,students_mentored,performance_category'
        ).execute()
        perfs  = perf.data or []
        by_year = {}
        for p in perfs:
            yr = p.get('year')
            if not yr: continue
            if yr not in by_year:
                by_year[yr] = {'overall':[], 'teaching':[], 'research':[],
                               'admin':[], 'publications':0, 'citations':0,
                               'students_mentored':0, 'categories':{}}
            d = by_year[yr]
            if p.get('overall_score'):        d['overall'].append(p['overall_score'])
            if p.get('teaching_rating'):      d['teaching'].append(p['teaching_rating'])
            if p.get('research_score'):       d['research'].append(p['research_score'])
            if p.get('administration_score'): d['admin'].append(p['administration_score'])
            d['publications']      += p.get('publications', 0) or 0
            d['citations']         += p.get('citations', 0) or 0
            d['students_mentored'] += p.get('students_mentored', 0) or 0
            cat = p.get('performance_category', 'Unknown')
            d['categories'][cat]   = d['categories'].get(cat, 0) + 1

        def avg(lst): return round(sum(lst)/len(lst), 2) if lst else 0
        report = {yr: {
            'avg_overall':     avg(d['overall']),
            'avg_teaching':    avg(d['teaching']),
            'avg_research':    avg(d['research']),
            'avg_admin':       avg(d['admin']),
            'total_pubs':      d['publications'],
            'total_citations': d['citations'],
            'total_mentored':  d['students_mentored'],
            'categories':      d['categories'],
            'count':           len(d['overall'])
        } for yr, d in sorted(by_year.items())}
        return jsonify({'report': report}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/department-report', methods=['GET'])
@admin_required
def department_report():
    try:
        fac  = supabase.table('faculty').select('faculty_id,department').execute()
        perf = supabase.table('performance').select(
            'faculty_id,overall_score,research_score,teaching_rating,publications').execute()
        fac_map = {f['faculty_id']: f['department'] for f in (fac.data or [])}
        by_dept = {}
        for p in (perf.data or []):
            dept = fac_map.get(p['faculty_id'], 'Unknown')
            by_dept.setdefault(dept, {'scores':[], 'research':[], 'teaching':[], 'pubs':0})
            if p.get('overall_score'):   by_dept[dept]['scores'].append(p['overall_score'])
            if p.get('research_score'):  by_dept[dept]['research'].append(p['research_score'])
            if p.get('teaching_rating'): by_dept[dept]['teaching'].append(p['teaching_rating'])
            by_dept[dept]['pubs'] += p.get('publications', 0) or 0

        def avg(lst): return round(sum(lst)/len(lst), 2) if lst else 0
        result = {dept: {
            'avg_overall':  avg(d['scores']),
            'avg_research': avg(d['research']),
            'avg_teaching': avg(d['teaching']),
            'total_pubs':   d['pubs'],
            'count':        len(d['scores'])
        } for dept, d in by_dept.items()}
        return jsonify({'departments': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/performance', methods=['GET'])
@admin_required
def get_all_performance():
    try:
        year = request.args.get('year')
        dept = request.args.get('department')
        fac  = supabase.table('faculty').select('faculty_id,name,department,designation').execute()
        fac_map = {f['faculty_id']: f for f in (fac.data or [])}
        q = supabase.table('performance').select('*')
        if year: q = q.eq('year', int(year))
        res  = q.execute()
        rows = []
        for p in (res.data or []):
            fi = fac_map.get(p.get('faculty_id'), {})
            if dept and fi.get('department') != dept: continue
            rows.append({**p, **fi})
        return jsonify({'performance': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/performance', methods=['POST'])
@admin_required
def add_performance():
    try:
        data = request.get_json()
        supabase.table('performance').upsert(data).execute()
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════
#  AI SUGGESTIONS ENGINE
# ═══════════════════════════════════════════════════════

def generate_suggestions(perf_records: list) -> dict:
    if not perf_records:
        return {'suggestions': [], 'missing_data': [], 'strengths': []}
    latest      = max(perf_records, key=lambda x: x.get('year', 0))
    suggestions = []
    missing     = []
    strengths   = []

    tr = latest.get('teaching_rating', 0) or 0
    sf = latest.get('student_feedback', 0) or 0
    th = latest.get('teaching_hours', 0)   or 0
    if tr == 0:    missing.append('Teaching Rating is not recorded')
    elif tr >= 4.0: strengths.append(f'Excellent teaching rating ({tr}/5)')
    elif tr < 3.0:  suggestions.append({'area':'Teaching','priority':'High',
        'issue':f'Teaching rating is low ({tr}/5)',
        'suggestion':'Attend pedagogy workshops, use interactive teaching methods.'})
    elif tr < 3.5:  suggestions.append({'area':'Teaching','priority':'Medium',
        'issue':f'Teaching rating needs improvement ({tr}/5)',
        'suggestion':'Consider peer teaching reviews and incorporate more case studies.'})
    if sf < 3.0 and sf > 0:
        suggestions.append({'area':'Student Feedback','priority':'High',
            'issue':f'Low student feedback score ({sf}/5)',
            'suggestion':'Conduct end-of-module surveys, hold extra doubt-clearing sessions.'})
    if th < 12 and th > 0:
        suggestions.append({'area':'Teaching Hours','priority':'Medium',
            'issue':f'Teaching hours below standard ({th} hrs/week)',
            'suggestion':'Review workload allocation with department head.'})

    pub = latest.get('publications', 0) or 0
    cit = latest.get('citations', 0)    or 0
    rs  = latest.get('research_score', 0) or 0
    pc  = latest.get('projects_completed', 0) or 0
    if pub == 0:    missing.append('No publications this year')
    elif pub >= 3:  strengths.append(f'Strong publication record ({pub} publications)')
    elif pub == 1:  suggestions.append({'area':'Research','priority':'Medium',
        'issue':'Only 1 publication this year',
        'suggestion':'Target 2–3 publications per year.'})
    if cit == 0 and pub > 0:
        suggestions.append({'area':'Research Impact','priority':'Low',
            'issue':'Publications have no citations yet',
            'suggestion':'Share work on ResearchGate / Academia.edu.'})
    if rs < 2.5 and rs > 0:
        suggestions.append({'area':'Research Score','priority':'High',
            'issue':f'Research score is critical ({rs}/5)',
            'suggestion':'Apply for funded research projects, join research groups.'})
    if pc == 0:     missing.append('No completed projects recorded')
    elif pc >= 2:   strengths.append(f'{pc} projects completed')

    adm = latest.get('administration_score', 0) or 0
    sm  = latest.get('students_mentored', 0)    or 0
    if adm == 0:    missing.append('Administration score not recorded')
    elif adm >= 4.0: strengths.append(f'Strong administrative contribution ({adm}/5)')
    elif adm < 2.5:  suggestions.append({'area':'Administration','priority':'Medium',
        'issue':f'Low administration score ({adm}/5)',
        'suggestion':'Take on committee roles, help organize department events.'})
    if sm == 0:     missing.append('No students mentored this year')
    elif sm >= 20:  strengths.append(f'Excellent mentoring ({sm} students)')
    elif sm < 5:    suggestions.append({'area':'Mentoring','priority':'Low',
        'issue':f'Few students mentored ({sm})',
        'suggestion':'Take up formal mentoring roles, guide project students.'})

    if len(perf_records) >= 2:
        srt  = sorted(perf_records, key=lambda x: x.get('year', 0))
        prev, curr = srt[-2], srt[-1]
        if (curr.get('overall_score') or 0) < (prev.get('overall_score') or 0) - 0.3:
            suggestions.insert(0, {'area':'Trend Alert','priority':'High',
                'issue':'Overall score has declined compared to last year',
                'suggestion':'Review all metrics carefully. Schedule a performance review meeting.'})

    return {
        'suggestions':         suggestions,
        'missing_data':        missing,
        'strengths':           strengths,
        'year_analyzed':       latest.get('year'),
        'overall_score':       latest.get('overall_score'),
        'performance_category':latest.get('performance_category')
    }


@app.route('/api/faculty/suggestions/<faculty_id>', methods=['GET'])
@login_required
def get_suggestions(faculty_id):
    u = session['user']
    if u['role'] == 'faculty' and u.get('faculty_id') != faculty_id:
        return jsonify({'error': 'Access denied'}), 403
    try:
        res  = supabase.table('performance').select('*').eq('faculty_id', faculty_id).execute()
        data = generate_suggestions(res.data or [])
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════
#  ML PREDICTION
# ═══════════════════════════════════════════════════════

@app.route('/api/ml/predict', methods=['POST'])
@login_required
def predict():
    if not ml_model:
        return jsonify({'error': 'ML model not loaded'}), 503
    try:
        d     = request.get_json()
        feats = [
            float(d.get('publications', 0)),
            float(d.get('citations', 0)),
            float(d.get('projects_completed', 0)),
            float(d.get('students_mentored', 0)),
            float(d.get('teaching_rating', 3)),
            float(d.get('research_score', 3)),
            float(d.get('administration_score', 3)),
            float(d.get('teaching_hours', 15)),
            float(d.get('student_feedback', 3)),
            float(d.get('experience_years', 5))
        ]
        scaled = ml_scaler.transform([feats])
        enc    = ml_model.predict(scaled)[0]
        proba  = ml_model.predict_proba(scaled)[0]
        label  = ml_encoder.inverse_transform([enc])[0]
        probs  = {cls: round(float(p)*100, 1) for cls, p in zip(ml_encoder.classes_, proba)}
        return jsonify({
            'prediction':    label,
            'confidence':    round(float(max(proba))*100, 1),
            'probabilities': probs
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/model-info', methods=['GET'])
def model_info():
    if not ml_metadata:
        return jsonify({'loaded': False}), 200
    return jsonify({
        'loaded':             True,
        'model_type':         ml_metadata.get('model_type'),
        'accuracy':           ml_metadata.get('accuracy'),
        'classes':            ml_metadata.get('classes'),
        'feature_importance': ml_metadata.get('feature_importance')
    }), 200


# ═══════════════════════════════════════════════════════
#  UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.route('/api/departments', methods=['GET'])
def get_departments():
    try:
        res   = supabase.table('faculty').select('department').execute()
        depts = sorted(set(f['department'] for f in (res.data or []) if f.get('department')))
        return jsonify({'departments': depts}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/years', methods=['GET'])
def get_years():
    try:
        res   = supabase.table('performance').select('year').execute()
        years = sorted(set(p['year'] for p in (res.data or []) if p.get('year')), reverse=True)
        return jsonify({'years': years}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok', 'version': '3.0',
        'ml_loaded':    ml_model is not None,
        'smtp_enabled': SMTP_ENABLED,
        'timestamp':    datetime.now().isoformat()
    }), 200


# ═══════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/faculty')
def faculty_page():
    if 'user' not in session or session['user']['role'] != 'faculty':
        return redirect('/')
    return render_template('faculty_dashboard.html')

@app.errorhandler(404)
def not_found(e):  return jsonify({'error': 'Not found'}), 404
@app.errorhandler(500)
def server_err(e): return jsonify({'error': 'Server error'}), 500


if __name__ == '__main__':
    print('\n' + '='*60)
    print('🎓 FACULTY PERFORMANCE SYSTEM v3.0')
    print('='*60)
    print('✓ Registration + OTP Email Verification')
    print('✓ Yearly Charts & Graphs')
    print('✓ AI Improvement Suggestions')
    print('✓ Document Upload & Verification (base64 DB storage)')
    print(f'✓ SMTP Email: {"Enabled" if SMTP_ENABLED else "Dev Mode (OTP printed to console)"}')
    print('='*60)
    app.run(debug=True, host='0.0.0.0', port=5000)