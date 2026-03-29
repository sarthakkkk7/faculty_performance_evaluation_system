#!/usr/bin/env python3
"""
Data Loader Utility
Handles CSV loading and JSON parsing for faculty performance data.
"""

import pandas as pd
import json
import ast
from typing import Dict, List, Any, Optional

class FacultyDataLoader:
    """Load and parse faculty performance data with JSON fields."""
    
    def __init__(self, csv_path: str = 'faculty_performance_complete_v2.csv'):
        """Initialize data loader with CSV path."""
        self.csv_path = csv_path
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """Load CSV data and parse JSON columns."""
        print(f"Loading data from {self.csv_path}...")
        self.df = pd.read_csv(self.csv_path)
        print(f"✓ Loaded {len(self.df)} records for {self.df['Faculty_ID'].nunique()} faculty members")
        return self.df
    
    def parse_json_field(self, value: Any) -> Any:
        """Safely parse JSON or Python literal string."""
        if pd.isna(value):
            return None
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                # Try parsing as JSON first
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    # Try Python literal eval for array strings
                    return ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return value
        return value
    
    def parse_subjects(self, value: Any) -> List[str]:
        """Parse Subjects_Handled field."""
        parsed = self.parse_json_field(value)
        if isinstance(parsed, list):
            return parsed
        return []
    
    def parse_certifications(self, value: Any) -> List[str]:
        """Parse Certifications field."""
        parsed = self.parse_json_field(value)
        if isinstance(parsed, list):
            return parsed
        return []
    
    def parse_workshops(self, value: Any) -> List[str]:
        """Parse Workshops field."""
        parsed = self.parse_json_field(value)
        if isinstance(parsed, list):
            return parsed
        return []
    
    def parse_institutional_activities(self, value: Any) -> Dict:
        """Parse Institutional_Activities field."""
        parsed = self.parse_json_field(value)
        if isinstance(parsed, dict):
            return parsed
        return {
            'committee_memberships': [],
            'administrative_roles': [],
            'event_organization': []
        }
    
    def get_faculty_by_id(self, faculty_id: str) -> pd.DataFrame:
        """Get all records for a specific faculty member."""
        if self.df is None:
            self.load_data()
        return self.df[self.df['Faculty_ID'] == faculty_id].copy()
    
    def get_faculty_by_year(self, year: int) -> pd.DataFrame:
        """Get all faculty records for a specific year."""
        if self.df is None:
            self.load_data()
        return self.df[self.df['Year'] == year].copy()
    
    def get_faculty_by_department(self, department: str) -> pd.DataFrame:
        """Get all records for a specific department."""
        if self.df is None:
            self.load_data()
        return self.df[self.df['Department'] == department].copy()
    
    def get_unique_faculty(self) -> List[Dict]:
        """Get unique faculty members with their latest info."""
        if self.df is None:
            self.load_data()
        
        # Get latest record for each faculty
        latest = self.df.sort_values('Year', ascending=False).groupby('Faculty_ID').first().reset_index()
        
        faculty_list = []
        for _, row in latest.iterrows():
            faculty_list.append({
                'faculty_id': row['Faculty_ID'],
                'name': row['Name'],
                'department': row['Department'],
                'designation': row['Designation'],
                'experience_years': int(row['Experience_Years'])
            })
        
        return faculty_list
    
    def get_departments(self) -> List[str]:
        """Get unique departments."""
        if self.df is None:
            self.load_data()
        return sorted(self.df['Department'].unique().tolist())
    
    def get_years(self) -> List[int]:
        """Get available years."""
        if self.df is None:
            self.load_data()
        return sorted(self.df['Year'].unique().tolist())
    
    def get_performance_stats(self, faculty_id: Optional[str] = None, 
                             year: Optional[int] = None,
                             department: Optional[str] = None) -> Dict:
        """Get performance statistics with optional filters."""
        if self.df is None:
            self.load_data()
        
        # Apply filters
        filtered_df = self.df.copy()
        if faculty_id:
            filtered_df = filtered_df[filtered_df['Faculty_ID'] == faculty_id]
        if year:
            filtered_df = filtered_df[filtered_df['Year'] == year]
        if department:
            filtered_df = filtered_df[filtered_df['Department'] == department]
        
        if len(filtered_df) == 0:
            return {
                'count': 0,
                'avg_overall_score': 0,
                'avg_teaching_rating': 0,
                'avg_research_score': 0,
                'avg_administration_score': 0
            }
        
        return {
            'count': len(filtered_df),
            'avg_overall_score': round(filtered_df['Overall_Score'].mean(), 2),
            'avg_teaching_rating': round(filtered_df['Teaching_Rating'].mean(), 2),
            'avg_research_score': round(filtered_df['Research_Score'].mean(), 2),
            'avg_administration_score': round(filtered_df['Administration_Score'].mean(), 2),
            'total_publications': int(filtered_df['Publications'].sum()),
            'total_citations': int(filtered_df['Citations'].sum()),
            'total_projects': int(filtered_df['Projects_Completed'].sum()),
            'total_students_mentored': int(filtered_df['Students_Mentored'].sum())
        }
    
    def get_performance_trends(self, faculty_id: str) -> Dict:
        """Get performance trends for a faculty member over years."""
        if self.df is None:
            self.load_data()
        
        faculty_data = self.df[self.df['Faculty_ID'] == faculty_id].sort_values('Year')
        
        if len(faculty_data) == 0:
            return {
                'years': [],
                'overall_scores': [],
                'teaching_ratings': [],
                'research_scores': [],
                'publications': []
            }
        
        return {
            'years': faculty_data['Year'].tolist(),
            'overall_scores': faculty_data['Overall_Score'].tolist(),
            'teaching_ratings': faculty_data['Teaching_Rating'].tolist(),
            'research_scores': faculty_data['Research_Score'].tolist(),
            'administration_scores': faculty_data['Administration_Score'].tolist(),
            'publications': faculty_data['Publications'].tolist(),
            'citations': faculty_data['Citations'].tolist(),
            'projects': faculty_data['Projects_Completed'].tolist(),
            'students_mentored': faculty_data['Students_Mentored'].tolist()
        }
    
    def export_to_dict(self, include_json_fields: bool = False) -> List[Dict]:
        """Export data as list of dictionaries."""
        if self.df is None:
            self.load_data()
        
        records = []
        for _, row in self.df.iterrows():
            record = {
                'faculty_id': row['Faculty_ID'],
                'name': row['Name'],
                'department': row['Department'],
                'designation': row['Designation'],
                'year': int(row['Year']),
                'teaching_hours': float(row['Teaching_Hours']),
                'student_feedback': float(row['Student_Feedback']),
                'publications': int(row['Publications']),
                'citations': int(row['Citations']),
                'research_score': float(row['Research_Score']),
                'projects_completed': int(row['Projects_Completed']),
                'experience_years': int(row['Experience_Years']),
                'teaching_rating': float(row['Teaching_Rating']),
                'students_mentored': int(row['Students_Mentored']),
                'administration_score': float(row['Administration_Score']),
                'overall_score': float(row['Overall_Score']),
                'performance_label': row['Performance_Label']
            }
            
            if include_json_fields:
                record['subjects_handled'] = self.parse_subjects(row['Subjects_Handled'])
                record['certifications'] = self.parse_certifications(row['Certifications'])
                record['workshops'] = self.parse_workshops(row['Workshops'])
                record['institutional_activities'] = self.parse_institutional_activities(row['Institutional_Activities'])
            
            records.append(record)
        
        return records


def main():
    """Demo usage of FacultyDataLoader."""
    print("="*60)
    print("🔍 Faculty Data Loader Demo")
    print("="*60)
    
    # Initialize loader
    loader = FacultyDataLoader()
    
    # Load data
    df = loader.load_data()
    
    # Get unique faculty
    faculty_list = loader.get_unique_faculty()
    print(f"\n👥 Unique Faculty Members: {len(faculty_list)}")
    print(f"   Sample: {faculty_list[0]['name']} ({faculty_list[0]['department']})")
    
    # Get departments
    departments = loader.get_departments()
    print(f"\n🏢 Departments: {', '.join(departments)}")
    
    # Get years
    years = loader.get_years()
    print(f"\n📅 Years: {years[0]} - {years[-1]}")
    
    # Get performance stats
    stats = loader.get_performance_stats()
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Records: {stats['count']}")
    print(f"   Avg Overall Score: {stats['avg_overall_score']}")
    print(f"   Total Publications: {stats['total_publications']}")
    
    # Get trends for first faculty
    first_faculty_id = faculty_list[0]['faculty_id']
    trends = loader.get_performance_trends(first_faculty_id)
    print(f"\n📈 Trends for {faculty_list[0]['name']}:")
    print(f"   Years: {trends['years']}")
    print(f"   Overall Scores: {trends['overall_scores']}")
    
    print("\n" + "="*60)
    print("✅ Data Loader working perfectly!")
    print("="*60)


if __name__ == '__main__':
    main()
