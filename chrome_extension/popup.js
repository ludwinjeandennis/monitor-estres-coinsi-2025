// popup.js - Lógica de la extensión de Chrome

const API_URL = 'https://monitor-estres-coinsi-2025.onrender.com/api';

// Configuración de iconos y textos por nivel de estrés
const STRESS_CONFIG = {
    0: {
        icon: '🟢',
        label: 'BAJO',
        className: 'bajo',
        color: '#4ade80',
        recommendation: '¡Excelente! Mantén este ritmo de trabajo. Estás en tu zona óptima de productividad.'
    },
    1: {
        icon: '🟡',
        label: 'MEDIO',
        className: 'medio',
        color: '#fbbf24',
        recommendation: 'Considera hacer una pausa breve de 5-10 minutos. Camina un poco o toma agua.'
    },
    2: {
        icon: '🔴',
        label: 'ALTO',
        className: 'alto',
        color: '#f87171',
        recommendation: '⚠️ TOMA UN DESCANSO AHORA. Date 10-15 minutos para relajarte. Tu bienestar es importante.'
    }
};

// Elementos del DOM
const elements = {
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    content: document.getElementById('content'),
    stressIcon: document.getElementById('stressIcon'),
    stressLabel: document.getElementById('stressLabel'),
    probBajo: document.getElementById('probBajo'),
    probMedio: document.getElementById('probMedio'),
    probAlto: document.getElementById('probAlto'),
    keysPerMin: document.getElementById('keysPerMin'),
    errorRate: document.getElementById('errorRate'),
    clicksPerMin: document.getElementById('clicksPerMin'),
    mouseSpeed: document.getElementById('mouseSpeed'),
    recommendation: document.getElementById('recommendation'),
    recommendationText: document.getElementById('recommendationText'),
    lastUpdate: document.getElementById('lastUpdate')
};

// Función para obtener el estado actual
async function fetchStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        
        if (!response.ok) {
            throw new Error('No se pudo obtener el estado');
        }
        
        const data = await response.json();
        updateUI(data);
        showContent();
        
    } catch (error) {
        console.error('Error:', error);
        showError();
    }
}

// Actualizar la interfaz con los datos
function updateUI(data) {
    const level = data.stress_level;
    const config = STRESS_CONFIG[level];
    const probs = data.probabilities;
    const features = data.features;
    
    // Actualizar indicador de estrés
    elements.stressIcon.textContent = config.icon;
    elements.stressLabel.textContent = config.label;
    elements.stressLabel.className = `stress-label ${config.className}`;
    
    // Actualizar probabilidades
    elements.probBajo.textContent = `${(probs.bajo * 100).toFixed(0)}%`;
    elements.probMedio.textContent = `${(probs.medio * 100).toFixed(0)}%`;
    elements.probAlto.textContent = `${(probs.alto * 100).toFixed(0)}%`;
    
    // Actualizar métricas
    elements.keysPerMin.textContent = features.keys_per_minute.toFixed(0);
    elements.errorRate.textContent = `${(features.error_rate * 100).toFixed(1)}%`;
    elements.clicksPerMin.textContent = features.clicks_per_minute.toFixed(0);
    elements.mouseSpeed.textContent = features.avg_mouse_speed.toFixed(0);
    
    // Mostrar recomendación
    if (level > 0) {
        elements.recommendation.style.display = 'block';
        elements.recommendation.style.borderLeftColor = config.color;
        elements.recommendationText.textContent = config.recommendation;
    } else {
        elements.recommendation.style.display = 'none';
    }
    
    // Actualizar timestamp
    const now = new Date();
    elements.lastUpdate.textContent = `Última actualización: ${now.toLocaleTimeString('es-PE')}`;
    
    // Mostrar notificación si el estrés es alto
    if (level === 2 && Notification.permission === 'granted') {
        showNotification(config);
    }
}

// Mostrar notificación del sistema
function showNotification(config) {
    chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: '⚠️ Nivel de Estrés Alto',
        message: config.recommendation,
        priority: 2
    });
}

// Funciones de visualización
function showLoading() {
    elements.loading.style.display = 'block';
    elements.error.style.display = 'none';
    elements.content.style.display = 'none';
}

function showError() {
    elements.loading.style.display = 'none';
    elements.error.style.display = 'block';
    elements.content.style.display = 'none';
}

function showContent() {
    elements.loading.style.display = 'none';
    elements.error.style.display = 'none';
    elements.content.style.display = 'block';
}

// Solicitar permiso para notificaciones
function requestNotificationPermission() {
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Inicializar cuando se abre el popup
document.addEventListener('DOMContentLoaded', () => {
    requestNotificationPermission();
    fetchStatus();
    
    // Actualizar cada 30 segundos mientras el popup está abierto
    setInterval(fetchStatus, 30000);
});

// Botón para forzar actualización (opcional, puedes agregarlo al HTML)
function refreshData() {
    showLoading();
    fetchStatus();
}

// Exportar para uso en background.js si es necesario
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { fetchStatus, updateUI };
}