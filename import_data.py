#!/usr/bin/env python3
"""
Batch Import Script for Faculty Performance Data
Imports complete dataset into Supabase database.
"""

from supabase import create_client, Client
from dotenv import load_dotenv
from data_loader import FacultyDataLoader
import os
import sys
from tqdm import tqdm

# Load environment variables
load_dotenv()

def init_supabase() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    return create_client(supabase_url, supabase_key)


def clear_existing_data(supabase: Client, confirm: bool = False):
    """Clear existing performance and faculty data."""
    if not confirm:
        response = input("⚠️  This will delete all existing data. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Import cancelled.")
            sys.exit(0)
    
    print("\n🗑️  Clearing existing data...")
    try:
        # Delete performance records first (foreign key constraint)
        supabase.table('performance').delete().neq('id', 0).execute()
        print("   ✓ Cleared performance records")
        
        # Delete faculty records
        supabase.table('faculty').delete().neq('id', 0).execute()
        print("   ✓ Cleared faculty records")
    except Exception as e:
        print(f"   ⚠️  Note: {str(e)[:100]}")


def import_faculty(supabase: Client, loader: FacultyDataLoader) -> dict:
    """Import unique faculty members."""
    print("\n👥 Importing faculty members...")
    
    faculty_list = loader.get_unique_faculty()
    success = 0
    errors = []
    
    for faculty in tqdm(faculty_list, desc="Faculty"):
        try:
            supabase.table('faculty').upsert({
                'faculty_id': faculty['faculty_id'],
                'name': faculty['name'],
                'department': faculty['department'],
                'designation': faculty['designation'],
                'email': f"{faculty['name'].lower().replace(' ', '.')}@university.edu",
                'hire_date': str(2019 - faculty['experience_years']) + '-01-01'
            }, on_conflict='faculty_id').execute()
            success += 1
        except Exception as e:
            errors.append(f"{faculty['faculty_id']}: {str(e)[:50]}")
    
    return {'total': len(faculty_list), 'success': success, 'errors': errors}


def import_performance(supabase: Client, loader: FacultyDataLoader) -> dict:
    """Import performance records."""
    print("\n📊 Importing performance records...")
    
    records = loader.export_to_dict(include_json_fields=False)
    success = 0
    errors = []
    
    # Batch import for better performance
    batch_size = 50
    for i in tqdm(range(0, len(records), batch_size), desc="Performance"):
        batch = records[i:i+batch_size]
        batch_data = []
        
        for record in batch:
            try:
                batch_data.append({
                    'faculty_id': record['faculty_id'],
                    'year': record['year'],
                    'teaching_hours': record['teaching_hours'],
                    'student_feedback': record['student_feedback'],
                    'publications': record['publications'],
                    'citations': record['citations'],
                    'research_score': record['research_score'],
                    'projects_completed': record['projects_completed'],
                    'experience_years': record['experience_years'],
                    'teaching_rating': record['teaching_rating'],
                    'students_mentored': record['students_mentored'],
                    'administration_score': record['administration_score'],
                    'overall_score': record['overall_score'],
                    'performance_category': record['performance_label']
                })
            except Exception as e:
                errors.append(f"{record.get('faculty_id', 'unknown')}: {str(e)[:50]}")
        
        # Insert batch
        if batch_data:
            try:
                supabase.table('performance').upsert(batch_data).execute()
                success += len(batch_data)
            except Exception as e:
                errors.append(f"Batch {i}: {str(e)[:50]}")
    
    return {'total': len(records), 'success': success, 'errors': errors}


def verify_import(supabase: Client, loader: FacultyDataLoader):
    """Verify imported data."""
    print("\n✅ Verifying import...")
    
    # Check faculty count
    fac_response = supabase.table('faculty').select('faculty_id').execute()
    faculty_count = len(fac_response.data or [])
    expected_faculty = loader.df['Faculty_ID'].nunique()
    
    # Check performance count
    perf_response = supabase.table('performance').select('id').execute()
    perf_count = len(perf_response.data or [])
    expected_perf = len(loader.df)
    
    print(f"\n📊 Import Verification:")
    print(f"   Faculty Members:")
    print(f"      Expected: {expected_faculty}")
    print(f"      Imported: {faculty_count}")
    print(f"      Status: {'✓ Match' if faculty_count == expected_faculty else '⚠ Mismatch'}")
    
    print(f"   Performance Records:")
    print(f"      Expected: {expected_perf}")
    print(f"      Imported: {perf_count}")
    print(f"      Status: {'✓ Match' if perf_count == expected_perf else '⚠ Mismatch'}")


def main():
    """Main import function."""
    print("="*70)
    print("📥 FACULTY PERFORMANCE DATA IMPORT")
    print("="*70)
    
    # Initialize
    print("\n🔧 Initializing...")
    supabase = init_supabase()
    print("   ✓ Supabase connected")
    
    loader = FacultyDataLoader()
    loader.load_data()
    
    # Clear existing data
    clear_existing_data(supabase, confirm=False)
    
    # Import faculty
    faculty_result = import_faculty(supabase, loader)
    print(f"\n   ✅ Faculty Import Complete:")
    print(f"      Success: {faculty_result['success']}/{faculty_result['total']}")
    if faculty_result['errors']:
        print(f"      Errors: {len(faculty_result['errors'])}")
        for err in faculty_result['errors'][:3]:
            print(f"         - {err}")
    
    # Import performance
    perf_result = import_performance(supabase, loader)
    print(f"\n   ✅ Performance Import Complete:")
    print(f"      Success: {perf_result['success']}/{perf_result['total']}")
    if perf_result['errors']:
        print(f"      Errors: {len(perf_result['errors'])}")
        for err in perf_result['errors'][:3]:
            print(f"         - {err}")
    
    # Verify
    verify_import(supabase, loader)
    
    print("\n" + "="*70)
    print("✨ IMPORT COMPLETE!")
    print("="*70)


if __name__ == '__main__':
    main()
