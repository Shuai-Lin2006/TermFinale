from core.exporter import export_to_html

if __name__ == "__main__":
    # 用 chr(96) * 3 生成三个反引号，彻底避开聊天软件对代码块的乱码打乱
    ticks = chr(96) * 3

    test_md = f"""
## 📊 宏观复习战略
这是最终极的渲染测试。注意看名词、公式、流程图和图片。

### 一、 流程图测试
{ticks}mermaid
graph TD
A[读题找已知量] --> B{{判断方向是否一致?}}
B -->|同向| C[速度直接相加]
B -->|反向| D[速度相减]
B -->|垂直| E[用勾股定理求斜边]
C --> F[得出最终结果]
D --> F
E --> F
{ticks}

### 二、 图片与公式测试
这是原题配图：
[IMAGE: slide1_img2.jpg]

我们看公式：$$ v_{{bc}} = \\sqrt{{v_{{bg}}^2 + v_{{cg}}^2}} $$
"""

    # 生成网页
    export_to_html(test_md, "/Users/lan/Desktop/纯手工测试.html")
    print("✅ 完美生成成功！请去桌面用 Edge 打开【纯手工测试.html】")