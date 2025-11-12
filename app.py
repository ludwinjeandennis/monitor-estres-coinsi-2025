"""
Aplicación Web Completa - Monitor de Estrés Académico
Deploy en Render.com - COINSI 2025 - UNAP
Versión mejorada con carga flexible de modelos
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
from datetime import datetime
import json
import os
import traceback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuración
MODEL_PATH = 'stress_detection_model.pkl'
DATA_FILE = 'stress_data.json'

# Variables globales para el modelo
model = None
scaler = None

# Cargar modelo ML con manejo robusto
print("🤖 Cargando modelo de Machine Learning...")
try:
    loaded_object = joblib.load(MODEL_PATH)
    
    # Detectar estructura del modelo automáticamente
    if isinstance(loaded_object, dict):
        if 'model' in loaded_object and 'scaler' in loaded_object:
            # Formato: {'model': ..., 'scaler': ...}
            model = loaded_object['model']
            scaler = loaded_object['scaler']
            print("✅ Modelo cargado: formato diccionario con model + scaler")
        elif 'pipeline' in loaded_object:
            # Formato: {'pipeline': ...}
            model = loaded_object['pipeline']
            scaler = None
            print("✅ Modelo cargado: formato pipeline")
        else:
            # Otro formato de diccionario, intentar usar como modelo directo
            model = loaded_object
            scaler = None
            print("✅ Modelo cargado: formato diccionario genérico")
    else:
        # El objeto es directamente el modelo/pipeline
        model = loaded_object
        scaler = None
        print("✅ Modelo cargado: objeto directo")
    
    print(f"   Tipo de modelo: {type(model).__name__}")
    if scaler:
        print(f"   Tipo de scaler: {type(scaler).__name__}")
    else:
        print("   Scaler: No separado (puede estar incluido en el modelo)")
    
except FileNotFoundError:
    print(f"⚠️ Archivo de modelo no encontrado: {MODEL_PATH}")
    print("   La aplicación funcionará en modo fallback")
except Exception as e:
    print(f"⚠️ Error al cargar modelo: {e}")
    print("   Stack trace completo:")
    traceback.print_exc()
    print("   La aplicación funcionará en modo fallback")

# Almacenamiento temporal de sesiones
sessions = {}

def load_data():
    """Carga datos históricos"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error al cargar datos históricos: {e}")
    return []

def save_data(data):
    """Guarda datos históricos"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar datos históricos: {e}")

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
            'message': 'Sesión iniciada',
            'model_available': model is not None
        })
    except Exception as e:
        print(f"Error en start_session: {e}")
        traceback.print_exc()
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
        print(f"Error en record_events: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_stress():
    """Analiza el nivel de estrés basado en los eventos"""
    try:
        data = request.get_json() or {}
        features = data.get('features', {})
        session_id = data.get('session_id')
        
        if not model:
            print("⚠️ Análisis solicitado pero modelo no disponible, usando fallback")
            return jsonify({
                'success': True,
                'stress_level': 1,
                'stress_label': 'MEDIO',
                'probabilities': {
                    'bajo': 0.33,
                    'medio': 0.34,
                    'alto': 0.33
                },
                'timestamp': datetime.now().isoformat(),
                'warning': 'Modelo no disponible, usando predicción por defecto',
                'features_used': features
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
        
        # Realizar predicción
        result = analyze_stress_with_features(features)
        
        if not result.get('success'):
            print(f"⚠️ Error en análisis: {result.get('error')}")
        
        result['timestamp'] = datetime.now().isoformat()
        result['features_used'] = features
        
        # Guardar análisis en sesión
        if session_id and session_id in sessions:
            sessions[session_id]['analyses'].append(result)
        
        # Guardar en historial
        if result.get('success'):
            history = load_data()
            history.append(result)
            save_data(history[-100:])  # Mantener solo últimos 100
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error en analyze_stress: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'stress_level': 1,
            'stress_label': 'MEDIO',
            'timestamp': datetime.now().isoformat()
        })

def analyze_stress_with_features(features):
    """Función auxiliar para análisis con manejo robusto"""
    if not model:
        return {
            'success': False,
            'error': 'Modelo no disponible',
            'stress_level': 1,
            'stress_label': 'MEDIO',
            'probabilities': {
                'bajo': 0.33,
                'medio': 0.34,
                'alto': 0.33
            }
        }
    
    try:
        # Orden esperado de features
        feature_order = [
            'keys_per_minute', 
            'avg_key_latency', 
            'std_key_latency',
            'error_rate', 
            'clicks_per_minute', 
            'total_mouse_distance',
            'avg_mouse_speed'
        ]
        
        # Preparar datos de entrada
        X = np.array([[features.get(f, 0) for f in feature_order]])
        
        # Realizar predicción según la estructura del modelo
        if scaler:
            # Scaler separado: normalizar primero
            X_scaled = scaler.transform(X)
            prediction = int(model.predict(X_scaled)[0])
            probabilities = model.predict_proba(X_scaled)[0]
        else:
            # Pipeline o modelo directo: aplicar directamente
            prediction = int(model.predict(X)[0])
            probabilities = model.predict_proba(X)[0]
        
        # Asegurar que prediction esté en rango válido
        if prediction < 0 or prediction > 2:
            print(f"⚠️ Predicción fuera de rango: {prediction}, ajustando a MEDIO")
            prediction = 1
        
        return {
            'success': True,
            'stress_level': prediction,
            'stress_label': ['BAJO', 'MEDIO', 'ALTO'][prediction],
            'probabilities': {
                'bajo': float(probabilities[0]),
                'medio': float(probabilities[1]),
                'alto': float(probabilities[2])
            }
        }
        
    except Exception as e:
        print(f"Error en predicción: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'stress_level': 1,
            'stress_label': 'MEDIO',
            'probabilities': {
                'bajo': 0.33,
                'medio': 0.34,
                'alto': 0.33
            }
        }

@app.route('/api/test_analysis', methods=['POST', 'GET'])
def test_analysis():
    """Endpoint de prueba para verificar que el análisis funciona"""
    # Features de prueba simulando estrés alto
    test_features = {
        'keys_per_minute': 85,
        'avg_key_latency': 85,
        'std_key_latency': 35,
        'error_rate': 0.08,
        'clicks_per_minute': 25,
        'total_mouse_distance': 2800,
        'avg_mouse_speed': 650
    }
    
    result = analyze_stress_with_features(test_features)
    result['test_mode'] = True
    result['test_features'] = test_features
    result['timestamp'] = datetime.now().isoformat()
    
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene historial de análisis"""
    try:
        limit = request.args.get('limit', 10, type=int)
        history = load_data()
        return jsonify({
            'success': True,
            'data': history[-limit:] if limit > 0 else history,
            'total': len(history)
        })
    except Exception as e:
        print(f"Error en get_history: {e}")
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
                'distribution': {'bajo': 0, 'medio': 0, 'alto': 0},
                'model_loaded': model is not None
            })
        
        distribution = {'bajo': 0, 'medio': 0, 'alto': 0}
        for item in history:
            if isinstance(item, dict) and 'stress_label' in item:
                level = item['stress_label'].lower()
                if level in distribution:
                    distribution[level] += 1
        
        return jsonify({
            'success': True,
            'total_analyses': len(history),
            'distribution': distribution,
            'model_loaded': model is not None,
            'has_scaler': scaler is not None
        })
    except Exception as e:
        print(f"Error en get_stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Estado del sistema"""
    return jsonify({
        'success': True,
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'active_sessions': len(sessions),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba general"""
    return jsonify({
        'success': True,
        'message': 'API funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'total_sessions': len(sessions),
        'model_type': type(model).__name__ if model else None
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check para el servidor"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'timestamp': datetime.now().isoformat(),
        'python_version': os.environ.get('PYTHON_VERSION', 'unknown')
    })

@app.errorhandler(404)
def not_found(e):
    """Manejo de errores 404"""
    return jsonify({
        'error': 'Endpoint no encontrado',
        'path': request.path
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Manejo de errores 500"""
    return jsonify({
        'error': 'Error interno del servidor',
        'message': str(e)
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"🚀 Iniciando Monitor de Estrés Académico")
    print(f"{'='*60}")
    print(f"Puerto: {port}")
    print(f"Modelo cargado: {'✅ Sí' if model else '❌ No'}")
    print(f"Scaler cargado: {'✅ Sí' if scaler else '❌ No'}")
    print(f"Debug: {debug_mode}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)