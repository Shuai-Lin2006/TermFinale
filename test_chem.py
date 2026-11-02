from core.ai_vision import analyze_image_with_ai

if __name__ == "__main__":
    # ⚠️ 这里的图片名字一定要跟你桌面上的图片名字一模一样！
    # 如果图片叫 化学式.png，那就改成 "/Users/lan/Desktop/化学式.png"
    image_path = "/Users/lan/Desktop/chem.jpg"

    print(f"正在识别图片：{image_path} ...")

    result = analyze_image_with_ai(image_path)

    print("\n========= AI 生成的图注 =========")
    print(result)
    print("==================================")