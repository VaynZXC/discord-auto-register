"""JavaScript injection скрипты для антидетект."""

from __future__ import annotations


def get_webdriver_masking_js() -> str:
    """
    Скрипт для маскировки navigator.webdriver и других automation флагов.
    
    Returns:
        JavaScript код для инъекции
    """
    return """
// АГРЕССИВНАЯ маскировка navigator.webdriver
// Метод 1: Object.defineProperty
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
    enumerable: true
});

// Метод 2: Удаляем из prototype
delete Object.getPrototypeOf(navigator).webdriver;

// Метод 3: Переопределяем геттер на прототипе
Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {
    get: () => undefined,
    configurable: true,
    enumerable: true
});

// Маскируем automation flag в Chrome
if (window.navigator.chrome) {
    window.navigator.chrome = {
        ...window.navigator.chrome,
        runtime: {}
    };
}

// Переопределяем permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Создаем правильный PluginArray
const createPluginArray = () => {
    const plugins = [
        {
            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Plugin"
        },
        {
            0: {type: "application/pdf", suffixes: "pdf", description: ""},
            description: "",
            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
            length: 1,
            name: "Chrome PDF Viewer"
        },
        {
            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
            description: "",
            filename: "internal-nacl-plugin",
            length: 2,
            name: "Native Client"
        }
    ];
    
    // Добавляем length property
    Object.defineProperty(plugins, 'length', {
        get: () => 3,
        enumerable: false,
        configurable: true
    });
    
    // Делаем plugins похожим на PluginArray
    plugins.item = function(index) {
        return this[index];
    };
    
    plugins.namedItem = function(name) {
        for (let i = 0; i < this.length; i++) {
            if (this[i].name === name) {
                return this[i];
            }
        }
        return null;
    };
    
    plugins.refresh = function() {};
    
    // Переопределяем toString чтобы вернуть [object PluginArray]
    Object.defineProperty(plugins, Symbol.toStringTag, {
        get: () => 'PluginArray',
        configurable: true
    });
    
    return plugins;
};

// Применяем PluginArray
Object.defineProperty(navigator, 'plugins', {
    get: createPluginArray,
    configurable: true,
    enumerable: true
});

// Также создаем mimeTypes
const createMimeTypeArray = () => {
    const mimeTypes = [
        {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
        {type: "application/pdf", suffixes: "pdf", description: ""},
    ];
    
    Object.defineProperty(mimeTypes, 'length', {
        get: () => 2,
        enumerable: false,
        configurable: true
    });
    
    mimeTypes.item = function(index) {
        return this[index];
    };
    
    mimeTypes.namedItem = function(name) {
        for (let i = 0; i < this.length; i++) {
            if (this[i].type === name) {
                return this[i];
            }
        }
        return null;
    };
    
    Object.defineProperty(mimeTypes, Symbol.toStringTag, {
        get: () => 'MimeTypeArray',
        configurable: true
    });
    
    return mimeTypes;
};

Object.defineProperty(navigator, 'mimeTypes', {
    get: createMimeTypeArray,
    configurable: true,
    enumerable: true
});

// Маскируем languages (должен соответствовать locale)
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
    enumerable: true
});
""".strip()


def get_canvas_fingerprint_js() -> str:
    """
    Скрипт для добавления шума в canvas fingerprint.
    
    Returns:
        JavaScript код для рандомизации canvas
    """
    return """
// Добавляем шум в canvas toDataURL
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    // Добавляем минимальный шум (1 пиксель)
    const context = this.getContext('2d');
    const imageData = context.getImageData(0, 0, this.width, this.height);
    
    // Добавляем шум в случайный пикселл
    const randomIndex = Math.floor(Math.random() * imageData.data.length / 4) * 4;
    imageData.data[randomIndex] = Math.floor(Math.random() * 256);
    imageData.data[randomIndex + 1] = Math.floor(Math.random() * 256);
    imageData.data[randomIndex + 2] = Math.floor(Math.random() * 256);
    
    context.putImageData(imageData, 0, 0);
    
    return originalToDataURL.apply(this, arguments);
};

// Также модифицируем toBlob
const originalToBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
    const context = this.getContext('2d');
    const imageData = context.getImageData(0, 0, this.width, this.height);
    
    const randomIndex = Math.floor(Math.random() * imageData.data.length / 4) * 4;
    imageData.data[randomIndex] = Math.floor(Math.random() * 256);
    
    context.putImageData(imageData, 0, 0);
    
    return originalToBlob.apply(this, arguments);
};
""".strip()


def get_webgl_fingerprint_js() -> str:
    """
    Скрипт для маскировки WebGL fingerprint.
    
    Returns:
        JavaScript код для модификации WebGL
    """
    return """
// Маскируем WebGL параметры
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // UNMASKED_VENDOR_WEBGL
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    // UNMASKED_RENDERER_WEBGL  
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    
    return getParameter.apply(this, arguments);
};

// Также для WebGL2
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        
        return getParameter2.apply(this, arguments);
    };
}
""".strip()


def get_audio_fingerprint_js() -> str:
    """
    Скрипт для маскировки Audio Context fingerprint.
    
    Returns:
        JavaScript код для модификации Audio Context
    """
    return """
// Добавляем шум в AudioContext
const audioContext = window.AudioContext || window.webkitAudioContext;
if (audioContext) {
    const originalCreateOscillator = audioContext.prototype.createOscillator;
    audioContext.prototype.createOscillator = function() {
        const oscillator = originalCreateOscillator.apply(this, arguments);
        
        const originalStart = oscillator.start;
        oscillator.start = function() {
            // Добавляем минимальный шум в частоту
            if (arguments.length > 0) {
                arguments[0] = arguments[0] + Math.random() * 0.0001;
            }
            return originalStart.apply(this, arguments);
        };
        
        return oscillator;
    };
}
""".strip()


def get_font_fingerprint_js() -> str:
    """
    Скрипт для маскировки font fingerprinting.
    
    Returns:
        JavaScript код
    """
    return """
// Маскируем доступные шрифты (возвращаем стандартный набор)
// Это предотвращает font fingerprinting через измерение текста
const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
CanvasRenderingContext2D.prototype.measureText = function(text) {
    // Добавляем микро-шум в измерения
    const result = originalMeasureText.apply(this, arguments);
    const noise = Math.random() * 0.01;
    
    return {
        ...result,
        width: result.width + noise
    };
};
""".strip()


def get_chrome_runtime_js() -> str:
    """
    Скрипт для добавления chrome.runtime (если его нет).
    
    Returns:
        JavaScript код
    """
    return """
// Добавляем chrome.runtime если его нет (признак автоматизации)
if (!window.chrome) {
    window.chrome = {};
}

if (!window.chrome.runtime) {
    window.chrome.runtime = {
        connect: function() {},
        sendMessage: function() {},
        onMessage: {
            addListener: function() {},
            removeListener: function() {}
        }
    };
}
""".strip()


def get_stealth_js() -> str:
    """
    Возвращает полный набор stealth скриптов.
    
    Returns:
        Объединенный JavaScript код для инъекции
    """
    scripts = [
        get_webdriver_masking_js(),
        get_canvas_fingerprint_js(),
        get_webgl_fingerprint_js(),
        get_audio_fingerprint_js(),
        get_font_fingerprint_js(),
        get_chrome_runtime_js(),
    ]
    
    return '\n\n'.join(scripts)


def get_init_script_for_page() -> str:
    """
    Возвращает скрипт для инъекции через page.add_init_script().
    Выполняется ДО загрузки любого контента страницы.
    
    Returns:
        JavaScript код
    """
    return get_stealth_js()

