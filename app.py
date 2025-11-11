"""
Aplicación Web Completa - Monitor de Estrés Académico
Deploy en Render.com o Railway.app
COINSI 2025 - UNAP
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# Configuración
MODEL_PATH = 'stress_detection_model.pkl'
DATA_FILE = 'stress_data.json'

# Cargar modelo ML
print("🤖 Cargando modelo de Machine Learning...")
try:
    model_data = joblib.load(MODEL_PATH)
    model = model_data['model']
    scaler = model_data['scaler']
    print("✅ Modelo cargado exitosamente")
except Exception as e:
    print(f"⚠️ Error al cargar modelo: {e}")
    model = None
    scaler = None

# Almacenamiento temporal de sesiones (en producción usar base de datos)
sessions = {}

def load_data():
    """Carga datos históricos"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    """Guarda datos históricos"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/start_session', methods=['POST'])
def start_session():
    """Inicia una nueva sesión de monitoreo"""
    data = request.json
    session_id = data.get('session_id', str(datetime.now().timestamp()))
    
    sessions[session_id] = {
        'start_time': datetime.now().isoformat(),
        'events': [],
        'analyses': []
    }
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Sesión iniciada'
    })

@app.route('/api/record_events', methods=['POST'])
def record_events():
    """Registra eventos de teclado y mouse"""
    data = request.json
    session_id = data.get('session_id')
    events = data.get('events', [])
    
    if session_id not in sessions:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    sessions[session_id]['events'].extend(events)
    
    return jsonify({
        'success': True,
        'events_recorded': len(events)
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_stress():
    """Analiza el nivel de estrés basado en los eventos"""
    data = request.json
    features = data.get('features')
    
    if not model or not scaler:
        return jsonify({'error': 'Modelo no disponible'}), 500
    
    if not features:
        return jsonify({'error': 'Features requeridas'}), 400
    
    # Preparar features para el modelo
    feature_order = [
        'keys_per_minute', 'avg_key_latency', 'std_key_latency',
        'error_rate', 'clicks_per_minute', 'total_mouse_distance',
        'avg_mouse_speed'
    ]
    
    try:
        X = np.array([[features[f] for f in feature_order]])
        
        # Normalizar y predecir
        X_scaled = scaler.transform(X)
        prediction = int(model.predict(X_scaled)[0])
        probabilities = model.predict_proba(X_scaled)[0]
        
        result = {
            'stress_level': prediction,
            'stress_label': ['BAJO', 'MEDIO', 'ALTO'][prediction],
            'probabilities': {
                'bajo': float(probabilities[0]),
                'medio': float(probabilities[1]),
                'alto': float(probabilities[2])
            },
            'timestamp': datetime.now().isoformat(),
            'features': features
        }
        
        # Guardar análisis
        session_id = data.get('session_id')
        if session_id and session_id in sessions:
            sessions[session_id]['analyses'].append(result)
        
        # Guardar en historial
        history = load_data()
        history.append(result)
        save_data(history[-100:])  # Mantener solo últimos 100
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene historial de análisis"""
    limit = request.args.get('limit', 10, type=int)
    history = load_data()
    return jsonify(history[-limit:])

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Obtiene datos de una sesión"""
    if session_id not in sessions:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    return jsonify(sessions[session_id])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas generales"""
    history = load_data()
    
    if not history:
        return jsonify({
            'total_analyses': 0,
            'distribution': {'bajo': 0, 'medio': 0, 'alto': 0}
        })
    
    distribution = {'bajo': 0, 'medio': 0, 'alto': 0}
    for item in history:
        level = item['stress_label'].lower()
        distribution[level] = distribution.get(level, 0) + 1
    
    return jsonify({
        'total_analyses': len(history),
        'distribution': distribution,
        'last_analysis': history[-1] if history else None
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check para el servidor"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)