// API Configuration
const config = {
    API_BASE_URL: 'http://127.0.0.1:5000',  // Flask server URL
    ENDPOINTS: {
        UPLOAD: '/api/upload',
        LIST_FOLDERS: '/api/folders',
        FOLDER_EXISTS: '/api/folder-exists',
        FOLDER_CONTENTS: '/api/folders'
    }
};

// Export configuration
window.appConfig = config;