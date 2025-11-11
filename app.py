"""
Aplicación Web Completa - Monitor de Estrés Académico
Deploy en Render.com - COINSI 2025 - UNAP
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

# Almacenamiento temporal de sesiones
sessions = {}

def load_data():
    """Carga datos históricos"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_data(data):
    """Guarda datos históricos"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/start_session', methods=['POST'])
def start_session():
    """Inicia una nueva sesión de monitoreo"""
    try:
        data = request.get_json() or {}
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/record_events', methods=['POST'])
def record_events():
    """Registra eventos de teclado y mouse"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        events = data.get('events', [])
        
        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Sesión no encontrada'}), 404
        
        sessions[session_id]['events'].extend(events)
        
        return jsonify({
            'success': True,
            'events_recorded': len(events),
            'total_events': len(sessions[session_id]['events'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_stress():
    """Analiza el nivel de estrés basado en los eventos"""
    try:
        data = request.get_json() or {}
        features = data.get('features', {})
        
        if not model or not scaler:
            return jsonify({
                'success': False,
                'error': 'Modelo no disponible',
                'fallback_prediction': 1  # MEDIO como fallback
            })
        
        # Features por defecto si no vienen
        default_features = {
            'keys_per_minute': 45,
            'avg_key_latency': 150,
            'std_key_latency': 25,
            'error_rate': 0.02,
            'clicks_per_minute': 12,
            'total_mouse_distance': 1200,
            'avg_mouse_speed': 350
        }
        
        # Usar features proporcionadas o defaults
        for key, value in default_features.items():
            if key not in features:
                features[key] = value
        
        # Preparar features para el modelo
        feature_order = [
            'keys_per_minute', 'avg_key_latency', 'std_key_latency',
            'error_rate', 'clicks_per_minute', 'total_mouse_distance',
            'avg_mouse_speed'
        ]
        
        X = np.array([[features.get(f, 0) for f in feature_order]])
        
        # Normalizar y predecir
        X_scaled = scaler.transform(X)
        prediction = int(model.predict(X_scaled)[0])
        probabilities = model.predict_proba(X_scaled)[0]
        
        result = {
            'success': True,
            'stress_level': prediction,
            'stress_label': ['BAJO', 'MEDIO', 'ALTO'][prediction],
            'probabilities': {
                'bajo': float(probabilities[0]),
                'medio': float(probabilities[1]),
                'alto': float(probabilities[2])
            },
            'timestamp': datetime.now().isoformat(),
            'features_used': features
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
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback_prediction': 1,
            'fallback_label': 'MEDIO'
        })

@app.route('/api/test_analysis', methods=['POST'])
def test_analysis():
    """Endpoint de prueba para verificar que el análisis funciona"""
    test_features = {
        'keys_per_minute': 85,
        'avg_key_latency': 85,
        'std_key_latency': 35,
        'error_rate': 0.08,
        'clicks_per_minute': 25,
        'total_mouse_distance': 2800,
        'avg_mouse_speed': 650
    }
    
    return analyze_stress_with_features(test_features)

def analyze_stress_with_features(features):
    """Función auxiliar para análisis"""
    if not model or not scaler:
        return {
            'success': False,
            'error': 'Modelo no disponible',
            'stress_level': 1,
            'stress_label': 'MEDIO'
        }
    
    try:
        feature_order = [
            'keys_per_minute', 'avg_key_latency', 'std_key_latency',
            'error_rate', 'clicks_per_minute', 'total_mouse_distance',
            'avg_mouse_speed'
        ]
        
        X = np.array([[features.get(f, 0) for f in feature_order]])
        X_scaled = scaler.transform(X)
        prediction = int(model.predict(X_scaled)[0])
        probabilities = model.predict_proba(X_scaled)[0]
        
        return {
            'success': True,
            'stress_level': prediction,
            'stress_label': ['BAJO', 'MEDIO', 'ALTO'][prediction],
            'probabilities': {
                'bajo': float(probabilities[0]),
                'medio': float(probabilities[1]),
                'alto': float(probabilities[2])
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stress_level': 1,
            'stress_label': 'MEDIO'
        }

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene historial de análisis"""
    try:
        limit = request.args.get('limit', 10, type=int)
        history = load_data()
        return jsonify({
            'success': True,
            'data': history[-limit:],
            'total': len(history)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas generales"""
    try:
        history = load_data()
        
        if not history:
            return jsonify({
                'success': True,
                'total_analyses': 0,
                'distribution': {'bajo': 0, 'medio': 0, 'alto': 0}
            })
        
        distribution = {'bajo': 0, 'medio': 0, 'alto': 0}
        for item in history:
            if isinstance(item, dict) and 'stress_label' in item:
                level = item['stress_label'].lower()
                distribution[level] = distribution.get(level, 0) + 1
        
        return jsonify({
            'success': True,
            'total_analyses': len(history),
            'distribution': distribution,
            'model_loaded': model is not None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba"""
    return jsonify({
        'success': True,
        'message': 'API funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'model_loaded': model is not None,
        'total_sessions': len(sessions)
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check para el servidor"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'timestamp': datetime.now().isoformat(),
        'python_version': os.environ.get('PYTHON_VERSION', 'unknown')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)