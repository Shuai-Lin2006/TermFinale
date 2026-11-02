import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from loguru import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'term_finale_pro.db')

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()


class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    major = Column(String(100), default="未知")
    school_level = Column(String(50), nullable=False)
    credits = Column(Float, nullable=False)
    days_left = Column(Integer, nullable=False)
    target_score = Column(Integer, nullable=False)
    user_difficulty = Column(Integer, nullable=False)
    is_major = Column(Boolean, nullable=False)
    persona = Column(String(50), default="温柔小姐姐")

    materials = relationship("Material", back_populates="course", cascade="all, delete-orphan")
    generated_files = relationship("GeneratedFile", back_populates="course", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = 'materials'
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default="core")
    filename = Column(String(200), nullable=False)

    course = relationship("Course", back_populates="materials")


class GeneratedFile(Base):
    __tablename__ = 'generated_files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String(500), nullable=False)
    created_at = Column(String(50))
    file_type = Column(String(50), default="guide")

    course = relationship("Course", back_populates="generated_files")


class UserConfig(Base):
    __tablename__ = 'user_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    motto = Column(String(200), default="只要学不死，就往死里学！")


def init_db():
    try:
        Base.metadata.create_all(engine)
        logger.success("数据库初始化成功！")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    return SessionLocal()