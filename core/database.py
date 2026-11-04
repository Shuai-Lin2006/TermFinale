from sqlalchemy import create_engine, event, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from loguru import logger

from core import paths

# 数据落用户目录（macOS/Windows/Linux 统一），打包后不再写入临时解压目录
paths.ensure_dirs()
BASE_DIR = str(paths.project_root())  # 兼容旧引用：仅指向源码资源，禁止用于存数据
DB_PATH = str(paths.db_path())

# timeout=15：并发写入时等待而不是立刻 database is locked
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False, connect_args={"timeout": 15})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL 提升读写并发；NORMAL 在 WAL 下兼顾安全与速度。"""
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
    finally:
        cur.close()


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
    notes = relationship("Note", back_populates="course", cascade="all, delete-orphan")
    mistakes = relationship("Mistake", back_populates="course", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = 'materials'
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default="core")  # core=重点资料, support=辅助资料
    weight = Column(Integer, default=3)
    filename = Column(String(200), nullable=False)

    course = relationship("Course", back_populates="materials")


class Note(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    chapter = Column(String(200), default="")
    question = Column(String(2000), default="")
    answer = Column(String(8000), default="")
    created_at = Column(String(50))

    course = relationship("Course", back_populates="notes")


class Mistake(Base):
    __tablename__ = 'mistakes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    question = Column(String(3000), default="")
    answer = Column(String(3000), default="")
    note = Column(String(1000), default="")
    stage = Column(Integer, default=0)
    mastered = Column(Boolean, default=False)
    created_at = Column(String(50))
    due_at = Column(String(50))

    course = relationship("Course", back_populates="mistakes")


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
        try:
            with engine.connect() as conn:
                cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(materials)")]
                if "weight" not in cols:
                    conn.exec_driver_sql("ALTER TABLE materials ADD COLUMN weight INTEGER DEFAULT 3")
                    conn.commit()
        except Exception:
            pass
        logger.success("数据库初始化成功！")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    return SessionLocal()