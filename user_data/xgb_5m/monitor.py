#!/usr/bin/env python3
"""
XGBoost Learning Progress Monitor
Simple Flask server to display training metrics and progress
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / 'models'

def get_model_metadata():
    """Get metadata from the latest trained model"""
    try:
        metadata_files = sorted(MODELS_DIR.glob('*_metadata.json'), key=os.path.getmtime, reverse=True)
        if metadata_files:
            with open(metadata_files[0], 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading model metadata: {e}")
    return None

@app.route('/api/training')
def training_data():
    """Get current training data"""
    metadata = get_model_metadata()

    if not metadata:
        return jsonify({
            'status': 'no_model',
            'message': 'No trained model found. Run: make train'
        })

    return jsonify({
        'status': 'success',
        'data': metadata
    })

@app.route('/')
def dashboard():
    """Serve the dashboard HTML"""
    return send_from_directory('.', 'learning_dashboard.html')

if __name__ == '__main__':
    MODELS_DIR.mkdir(exist_ok=True)
    print(f"🚀 XGBoost Learning Monitor starting on http://localhost:5001")
    print(f"📊 Reading model data from: {MODELS_DIR}")
    app.run(host='0.0.0.0', port=5001, debug=False)
