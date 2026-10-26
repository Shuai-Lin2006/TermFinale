from pptx import Presentation
from loguru import logger
import re


def clean_text_lines(slide_text: str) -> list:
    """V3 终极清洗滤网"""
    cleaned_lines = []

    for line in slide_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 1. 排除极短的纯数字/符号行
        if len(line) <= 3 and re.match(r'^[\d\W]+$', line):
            continue

        # 2. 超级黑名单（过滤老师信息、成绩占比等无用信息）
        junk_keywords = [
            "Tel", "电话", "手机", "邮箱", "@", "Site", "微信", "QQ",
            "平时成绩", "期中考试", "期末考试", "期末成绩", "成绩占比",
            "作业:", "作业：", "孙冬舒", "大学物理"
        ]
        if len(line) < 30 and any(keyword in line for keyword in junk_keywords):
            continue

        # 3. 排除纯考勤比例（如 "期中考试 30%" "50%"）
        if re.match(r'^.*?\d+%.*$', line) and len(line) < 15:
            continue

        # 4. 排除纯页码
        if re.match(r'^(P\.|Page|第)?\s*\d+(\/\d+)?\s*(页)?$', line, re.IGNORECASE):
            continue

        # 5. 清理排版垃圾（压缩多余空格、重复符号）
        line = re.sub(r'\s+', ' ', line)
        line = re.sub(r'([。\-_])\1+', r'\1', line)

        # 6. 短句加句号，防止看起来像乱码
        if len(line) <= 8 and not line.endswith(('。', '，', '：', '；')):
            line = line + "。"

        cleaned_lines.append(line)

    return cleaned_lines


def extract_text_from_pptx(file_path: str):
    """解析 PPT 的主函数"""
    logger.info(f"开始解析 PPT 文件: {file_path}")
    try:
        prs = Presentation(file_path)
        all_slides_text = []

        for index, slide in enumerate(prs.slides):
            slide_text = ""
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slide_text += shape.text + "\n"

            if slide_text.strip():
                # 调用上面的清洗函数
                cleaned_lines = clean_text_lines(slide_text)
                cleaned_text = "\n".join(cleaned_lines)

                if cleaned_text.strip():
                    all_slides_text.append(f"【第 {index + 1} 页】\n{cleaned_text}")

        logger.success("PPT 解析与深度清洗完成！")
        return all_slides_text

    except Exception as e:
        logger.error(f"解析失败: {e}")
        return []


if __name__ == "__main__":
    # ⚠️ 唯一需要你确认的地方：这里的路径是不是你桌面上真实的 PPT 路径
    test_ppt_path = "/Users/lan/Desktop/test.pptx"

    extracted_data = extract_text_from_pptx(test_ppt_path)

    if extracted_data:
        final_text = "\n\n".join(extracted_data)

        # 保存到桌面的文件
        output_file = "/Users/lan/Desktop/cleaned_ppt_v3.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_text)

        print(f"\n✅ 总计提取并深度清洗了 {len(extracted_data)} 页文字。")
        print(f"🎉 已经全部保存到桌面上的 cleaned_ppt_v3.txt 文件中，快去打开看看吧！")