from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from loguru import logger

import os

# 获取当前 database.py 所在目录的上一级（也就是项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'term_finale_pro.db')

# 1.初始化数据库引擎
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)


# 2. 创建基类
Base = declarative_base()


# ==================== 定义数据表模型 ====================

class Course(Base):
    """课程表模型"""
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    school_level = Column(String(50), nullable=False)
    credits = Column(Float, nullable=False)
    days_left = Column(Integer, nullable=False)
    target_score = Column(Integer, nullable=False)
    user_difficulty = Column(Integer, nullable=False)
    is_major = Column(Boolean, nullable=False)
    final_weight = Column(Float, nullable=False) # 👈 新增：用来存算出来的权重


class KnowledgePoint(Base):
    """知识点表模型 (与课程强关联)"""
    __tablename__ = 'knowledge_points'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    difficulty = Column(Integer, default=1)
    mastery = Column(Float, default=0.0)

    summary = Column(String(500), default="暂无总结")


# ==================== 初始化与 Session ====================

def init_db():
    try:
        Base.metadata.create_all(engine)
        logger.success("企业级数据库表结构初始化成功！")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    return SessionLocal()


# ==================== 测试区 ====================
if __name__ == "__main__":
    logger.add("app.log", rotation="10 MB")
    init_db()

    db = get_db_session()
    try:
        new_course = Course(
            name="高等数学",
            school_level="中9",
            credits=4.0,
            days_left=7,
            target_score=90,
            user_difficulty=5,
            is_major=True  # 👈 现在直接传 True，不用传 1 了
        )
        db.add(new_course)
        db.commit()
        db.refresh(new_course)  # 👈 核心：立刻获取刚生成的 id
        logger.success(f"课程保存成功，分配的ID是: {new_course.id}")

        # 接着存一个知识点，用到刚才获取的 ID
        kp = KnowledgePoint(
            course_id=new_course.id,
            title="二重积分",
            difficulty=3,
            mastery=0.2
        )
        db.add(kp)
        db.commit()
        logger.success("知识点保存成功！并且与课程外键关联完成！")

    except Exception as e:
        db.rollback()
        logger.error(f"保存失败: {e}")
    finally:
        db.close()
