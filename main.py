from core.database import get_db_session, Course, KnowledgePoint, init_db
from core.parser import extract_text_from_pptx
from core.ai_engine import extract_knowledge_with_ai
from loguru import logger

from models.user_profile import CourseInfo


def start_app():
    # 1. 确保数据表建好
    init_db()

    # 2. 开启数据库会话（叫柜员过来）
    db = get_db_session()

    try:
        # ================= 任务一：建档 =================
        logger.info("【任务一】正在调用核心大脑计算权重并建档...")

        # 1. 先用你的 CourseInfo 大脑，接收用户输入
        course_info = CourseInfo(
            name="大学物理",
            school="中9",
            credits=4.0,
            days=7,
            target=90,
            user_difficulty=5,
            is_major=True
        )

        # 2. 算出这门课的权重（比如是 13.61）
        weight = course_info.calculate_weight()
        logger.info(f"大脑计算完毕，该课程权重为: {weight}")

        # 3. 把大脑里的数据 + 算出来的权重，一起装进数据库的 Course 模型里
        new_course = Course(
            name=course_info.course_name,
            school_level=course_info.school_level,
            credits=course_info.credits,
            days_left=course_info.days_left,
            target_score=course_info.target_score,
            user_difficulty=course_info.user_difficulty,
            is_major=course_info.is_major,
            final_weight=weight  # 👈 把算出来的权重存进去！
        )

        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        logger.success(f"✅ 课程【大学物理】已入库，分配 ID: {new_course.id}")

        # ================= 任务二：解析文件 =================
        logger.info("【任务二】正在解析 PPT...")
        # ⚠️ 注意：换成你桌面上真正的路径！
        test_ppt_path = "/Users/lan/Desktop/test.pptx"
        cleaned_pages = extract_text_from_pptx(test_ppt_path)

        if not cleaned_pages:
            logger.warning("PPT 解析失败或没有内容，流程终止")
            return

        # ================= 任务三：AI提取与入库 =================
        logger.info("【任务三】开始呼叫 AI 提取知识点...")

        # 为了给你省钱和时间，我们只取前 3 页去测试
        test_pages = cleaned_pages[:3]

        for index, page_text in enumerate(test_pages):
            logger.info(f"正在处理第 {index + 1} 页...")

            # 呼叫大脑
            kps = extract_knowledge_with_ai(page_text)

            if kps:
                for kp_data in kps:
                    # 核心动作：把 AI 提取的数据，打包成数据库表格式
                    new_kp = KnowledgePoint(
                        course_id=new_course.id,
                        title=kp_data.get("title", "未知考点"),
                        difficulty=kp_data.get("difficulty", 3),
                        mastery=0.0,
                        # 👇 新增这一行，把 AI 的总结存进去
                        summary=kp_data.get("summary", "暂无总结")
                    )
                    db.add(new_kp)

                # 这一页处理完了，提交入库
                db.commit()
                logger.success(f"✅ 第 {index + 1} 页处理完毕，存入 {len(kps)} 个考点！")

    except Exception as e:
        db.rollback()
        logger.error(f"流水线运转失败: {e}")
    finally:
        db.close()
        logger.info("🎉 本次流水线运行结束！")


if __name__ == "__main__":
    start_app()

