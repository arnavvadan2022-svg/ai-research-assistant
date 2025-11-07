import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'quantum_assistant')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    
    # API Keys
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')
    SERP_API_KEY = os.getenv('SERP_API_KEY', '')
    ARXIV_API_URL = 'http://export.arxiv.org/api/query'
    
    # Application Settings
    MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', 10))
    MAX_ARXIV_PAPERS = int(os.getenv('MAX_ARXIV_PAPERS', 5))
    MAX_WEB_RESULTS = int(os.getenv('MAX_WEB_RESULTS', 5))
    CONVERSATION_HISTORY_LIMIT = int(os.getenv('CONVERSATION_HISTORY_LIMIT', 10))
    HF_MODEL = os.getenv('HF_MODEL', 'google/flan-t5-large')
    
    # Quantum categories for arXiv
    QUANTUM_CATEGORIES = ['quant-ph', 'cond-mat.mes-hall', 'cs.ET']
    
    @staticmethod
    def get_database_uri():
        return f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}