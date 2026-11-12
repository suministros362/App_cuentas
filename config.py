from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class DevelopmentConfig:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'data' / 'gastos.sqlite3').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig:
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'data' / 'gastos.sqlite3').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
