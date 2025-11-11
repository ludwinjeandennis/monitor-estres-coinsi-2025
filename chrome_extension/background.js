// background.js - Service Worker mejorado
// Monitor de Estrés Académico - COINSI 2025 UNAP

// ✅ CAMBIAR ESTA URL - Usar tu dominio de Render
const API_URL = 'https://monitor-estres-coinsi-2025.onrender.com/api';
const CHECK_INTERVAL_MINUTES = 2; // cada 2 minutos

const STRESS_CONFIG = {
    0: { title: 'Estrés Bajo', message: 'Continúa así, estás en tu zona óptima' },
    1: { title: 'Estrés Medio', message: 'Considera tomar una pausa breve' },
    2: { title: 'Estrés Alto', message: 'Toma un descanso de 10-15 minutos' }
};

let lastStressLevel = -1;
let lastNotificationTime = 0;
let intervalId = null;

// ---------------- FUNCIONES PRINCIPALES ----------------

// Verifica el nivel de estrés
async function checkStressLevel() {
    try {
        console.log('🔄 Conectando con API...');

        // ✅ CAMBIAR EL ENDPOINT - usar /api/stats o /api/test
        const response = await fetch(`${API_URL}/stats`, {
            method: 'GET',
            mode: 'cors',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

        const data = await response.json();
        
        // ✅ ADAPTAR A LA NUEVA ESTRUCTURA DE RESPUESTA
        let stressLevel = 1; // Default a MEDIO
        let probabilities = {};
        
        if (data.success && data.distribution) {
            // Calcular nivel basado en distribución o usar último análisis
            if (data.last_analysis) {
                stressLevel = data.last_analysis.stress_level || 1;
                probabilities = data.last_analysis.probabilities || {};
            } else {
                // Si no hay análisis, calcular basado en distribución
                const { bajo, medio, alto } = data.distribution;
                if (alto > medio && alto > bajo) stressLevel = 2;
                else if (bajo > medio && bajo > alto) stressLevel = 0;
                else stressLevel = 1;
            }
        }
        
        console.log(`✅ Nivel de estrés calculado: ${stressLevel}`);
        
        updateBadge(stressLevel);

        // Mostrar notificación si cambió y no está en cooldown
        const now = Date.now();
        const cooldownPassed = now - lastNotificationTime > CHECK_INTERVAL_MINUTES * 60 * 1000;
        if (stressLevel !== lastStressLevel && stressLevel >= 1 && cooldownPassed) {
            showNotification(stressLevel, { probabilities });
            lastStressLevel = stressLevel;
            lastNotificationTime = now;
        }

        // Guardar datos
        await chrome.storage.local.set({
            lastCheck: now,
            stressData: {
                stress_level: stressLevel,
                probabilities: probabilities,
                distribution: data.distribution,
                total_analyses: data.total_analyses
            }
        });

    } catch (error) {
        console.error('❌ Error de conexión:', error.message);
        console.log('🔧 Verifica que la API esté funcionando en:', API_URL);
        updateBadge(-1);
    }
}

// ---------------- INTERFAZ VISUAL ----------------

// Actualiza el icono del badge
function updateBadge(level) {
    const badges = {
        '-1': { text: '?', color: '#64748b' },
        '0': { text: '✓', color: '#4ade80' },
        '1': { text: '!', color: '#fbbf24' },
        '2': { text: '!!', color: '#f87171' }
    };
    const badge = badges[level.toString()] || badges['-1'];
    chrome.action.setBadgeText({ text: badge.text });
    chrome.action.setBadgeBackgroundColor({ color: badge.color });
}

// Muestra una notificación
function showNotification(level, data) {
    const config = STRESS_CONFIG[level];
    const probs = data?.probabilities || {};
    const confidence = probs.alto ? (probs.alto * 100).toFixed(0) : 
                      probs.medio ? (probs.medio * 100).toFixed(0) : '?';
    
    let message = config.message;
    if (confidence !== '?') message += ` (Confianza: ${confidence}%)`;

    chrome.notifications.create(`stress-${Date.now()}`, {
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: config.title,
        message,
        priority: level === 2 ? 2 : 1
    });
}

// ---------------- EVENTOS ----------------

// Inicia verificación periódica con setInterval
function startPeriodicCheck() {
    if (intervalId) clearInterval(intervalId); // evita duplicados
    console.log(`⏰ Iniciando verificación cada ${CHECK_INTERVAL_MINUTES} minutos`);
    console.log(`🌐 Conectando a: ${API_URL}`);
    
    // Verificación inmediata al iniciar
    checkStressLevel();
    
    // Luego cada intervalo
    intervalId = setInterval(() => {
        console.log('🔁 Verificando nivel de estrés...');
        checkStressLevel();
    }, CHECK_INTERVAL_MINUTES * 60 * 1000);
}

// Cuando se instala o inicia el navegador
chrome.runtime.onInstalled.addListener(() => {
    console.log('🎓 Monitor de Estrés instalado');
    console.log(`🌐 URL de API: ${API_URL}`);
    startPeriodicCheck();
});

chrome.runtime.onStartup.addListener(() => {
    console.log('🚀 Chrome iniciado - Monitor activo');
    startPeriodicCheck();
});

// Mensajes manuales desde popup o página
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'checkNow') {
        checkStressLevel()
            .then(() => sendResponse({ success: true }))
            .catch(() => sendResponse({ success: false }));
        return true;
    }
    if (request.action === 'getLastData') {
        chrome.storage.local.get(['stressData', 'lastCheck'])
            .then(result => sendResponse(result))
            .catch(() => sendResponse({}));
        return true;
    }
    if (request.action === 'getApiStatus') {
        // Verificar estado de la API
        fetch(`${API_URL}/health`)
            .then(response => response.json())
            .then(data => sendResponse({ success: true, data }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    }
});

console.log('✅ Background worker iniciado - Monitor de Estrés UNAP');
console.log(`🌐 Conectando a API: ${API_URL}`);