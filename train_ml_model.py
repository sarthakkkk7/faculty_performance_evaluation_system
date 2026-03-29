#!/usr/bin/env python3
"""
Machine Learning Model Training
Trains Random Forest model for faculty performance prediction.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import json
from datetime import datetime

def prepare_data():
    """Load and prepare data for training."""
    
    # Load the complete dataset
    df = pd.read_csv('faculty_performance_complete_v2.csv')
    
    print(f"Loaded {len(df)} records")
    print(f"Unique Faculty: {df['Faculty_ID'].nunique()}")
    print(f"Years covered: {df['Year'].min()} - {df['Year'].max()}")
    
    # Use the existing Performance_Label column
    df['Performance_Category'] = df['Performance_Label']
    
    # Features for ML model - using the actual column names
    feature_columns = [
        'Publications', 'Citations', 'Projects_Completed', 
        'Students_Mentored', 'Teaching_Rating', 'Research_Score',
        'Administration_Score', 'Teaching_Hours', 'Student_Feedback',
        'Experience_Years'
    ]
    
    # Ensure all columns exist and handle missing values
    for col in feature_columns:
        if col not in df.columns:
            print(f"Warning: {col} not found in dataset")
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    X = df[feature_columns].values
    y = df['Performance_Category'].values
    
    # Encode target variable
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    print(f"\nPerformance Categories:")
    for i, cls in enumerate(le.classes_):
        count = sum(y == cls)
        print(f"  {cls}: {count} records ({count/len(y)*100:.1f}%)")
    
    return X, y_encoded, le, feature_columns, df

def train_model(X, y, feature_names):
    """Train Random Forest model."""
    
    # Check class distribution
    unique, counts = np.unique(y, return_counts=True)
    min_count = min(counts)
    
    # Only use stratify if each class has at least 2 samples
    use_stratify = min_count >= 2
    
    # Split data
    if use_stratify:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    else:
        print(f"⚠️  Skipping stratification (min class size: {min_count})")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model with optimized parameters
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    print("\nTraining Random Forest model...")
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    train_accuracy = accuracy_score(y_train, y_pred_train)
    test_accuracy = accuracy_score(y_test, y_pred_test)
    
    print(f"Training accuracy: {train_accuracy:.4f}")
    print(f"Test accuracy: {test_accuracy:.4f}")
    
    return model, scaler, test_accuracy, y_test, y_pred_test

def save_model(model, scaler, label_encoder, feature_names, accuracy):
    """Save model and metadata."""
    
    # Save model
    joblib.dump(model, 'ml_model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    joblib.dump(label_encoder, 'label_encoder.pkl')
    
    print("\n✅ Model files saved:")
    print("   - ml_model.pkl")
    print("   - scaler.pkl")
    print("   - label_encoder.pkl")
    
    # Feature importance
    feature_importance = dict(zip(feature_names, model.feature_importances_))
    feature_importance = {k: round(v, 4) for k, v in 
                         sorted(feature_importance.items(), 
                               key=lambda x: x[1], reverse=True)}
    
    # Metadata
    metadata = {
        'model_type': 'Random Forest Classifier',
        'algorithm': 'sklearn.ensemble.RandomForestClassifier',
        'accuracy': round(accuracy, 4),
        'n_estimators': 200,
        'max_depth': 15,
        'min_samples_split': 5,
        'min_samples_leaf': 2,
        'classes': label_encoder.classes_.tolist(),
        'n_classes': len(label_encoder.classes_),
        'feature_names': feature_names,
        'n_features': len(feature_names),
        'feature_importance': feature_importance,
        'created_at': datetime.now().isoformat(),
        'dataset': 'faculty_performance_complete_v2.csv',
        'scaler_params': {
            'mean': scaler.mean_.tolist(),
            'scale': scaler.scale_.tolist()
        }
    }
    
    with open('model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("   - model_metadata.json")
    
    return feature_importance, metadata

def main():
    print("="*60)
    print("🤖 Faculty Performance ML Model Trainer v2.0")
    print("="*60)
    
    # Prepare data
    print("\n📊 Step 1: Loading and preparing data...")
    X, y, le, features, df = prepare_data()
    
    # Train model
    print("\n🔧 Step 2: Training Random Forest model...")
    model, scaler, accuracy, y_test, y_pred = train_model(X, y, features)
    
    # Save model
    print("\n💾 Step 3: Saving model and metadata...")
    feature_imp, metadata = save_model(model, scaler, le, features, accuracy)
    
    # Display results
    print("\n" + "="*60)
    print("✅ MODEL TRAINING COMPLETE!")
    print("="*60)
    print(f"🎯 Test Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"📁 Dataset: faculty_performance_complete_v2.csv")
    print(f"📊 Total Records: {len(df)}")
    print(f"👥 Unique Faculty: {df['Faculty_ID'].nunique()}")
    print(f"📅 Years: {df['Year'].min()} - {df['Year'].max()}")
    
    print(f"\n🏆 Top 5 Most Important Features:")
    for i, (feature, importance) in enumerate(list(feature_imp.items())[:5], 1):
        bar = "█" * int(importance * 50)
        print(f"   {i}. {feature:25s} {bar} {importance:.4f}")
    
    print(f"\n🎓 Performance Categories:")
    for cls in le.classes_:
        count = sum(y == le.transform([cls])[0])
        pct = count / len(y) * 100
        print(f"   {cls:20s}: {count:3d} records ({pct:5.1f}%)")
    
    print("\n" + "="*60)
    print("✨ Model is ready for deployment!")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
