"""创建 QA-Tool 使用指南"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
import os


def set_run_font(run, font_name='Microsoft YaHei', font_size=None):
    """设置 run 的中文字体"""
    run.font.name = font_name
    # 设置东亚字体
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = r.makeelement(qn('w:rFonts'), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), font_name)
    if font_size:
        run.font.size = font_size


def set_paragraph_font(paragraph, font_name='Microsoft YaHei'):
    """设置段落所有 run 的字体"""
    for run in paragraph.runs:
        set_run_font(run, font_name)


def add_screenshot(doc, image_path, caption, width=Inches(5.5)):
    """添加截图到文档"""
    if os.path.exists(image_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(image_path, width=width)
        # 添加图注
        caption_p = doc.add_paragraph(caption)
        caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption_p.style = doc.styles['Intense Quote']
        set_paragraph_font(caption_p)
    else:
        # 如果图片不存在，添加占位符
        p = doc.add_paragraph(f'【截图：{caption}】')
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.style = doc.styles['Intense Quote']
        set_paragraph_font(p)


def create_user_guide():
    doc = Document()
    
    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Microsoft YaHei'
    font.size = Pt(11)
    # 设置东亚字体
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    
    # 设置标题样式
    for i in range(1, 4):
        heading_style = doc.styles[f'Heading {i}']
        heading_style.font.name = 'Microsoft YaHei'
        heading_style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    
    # 标题
    title = doc.add_heading('QA-Tool 使用指南', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_font(title)
    
    doc.add_paragraph('版本：v2.6.5')
    doc.add_paragraph('')
    
    # 目录
    doc.add_heading('目录', level=1)
    toc_items = [
        '1. 产品简介',
        '2. 安装与启动',
        '3. 界面概览',
        '4. 快速入门',
        '5. 功能模块',
        '6. 常见问题',
    ]
    for item in toc_items:
        p = doc.add_paragraph(item, style='List Number')
        set_paragraph_font(p)
    
    doc.add_page_break()
    
    # 1. 产品简介
    doc.add_heading('1. 产品简介', level=1)
    p = doc.add_paragraph(
        'QA-Tool 是一款面向质量工程（QE）与工业工程（IE）的专业分析工具，'
        '基于 Python 3.14 + PySide6 构建。提供 35 个分析模块、AI 智能洞察、'
        '完整报告输出，并支持 ESP32 硬件数据采集。'
    )
    set_paragraph_font(p)
    
    doc.add_heading('核心功能', level=2)
    features = [
        'SPC 控制图（9 种 + Nelson 8 条判异规则）',
        '过程能力分析（Cp/Cpk/Pp/Ppk/Cpm）',
        'MSA 测量系统分析（Gage R&R/Type 1/偏倚/线性）',
        '假设检验（t/ANOVA/卡方/TOST/非参数）',
        'DOE 试验设计（全因子/CCD/Box-Behnken）',
        'IE 工具（时间研究/OEE/VSM/SMED/TPM）',
        '工程工具（FMEA/8D/PPAP/鱼骨图/柏拉图）',
        '硬件扩展（ESP32 设备监控与数据采集）',
    ]
    for f in features:
        p = doc.add_paragraph(f, style='List Bullet')
        set_paragraph_font(p)
    
    doc.add_heading('系统要求', level=2)
    p = doc.add_paragraph('操作系统：Windows 10/11（64 位）')
    set_paragraph_font(p)
    p = doc.add_paragraph('内存：4GB RAM（推荐 8GB）')
    set_paragraph_font(p)
    p = doc.add_paragraph('硬盘空间：500MB')
    set_paragraph_font(p)
    
    doc.add_page_break()
    
    # 2. 安装与启动
    doc.add_heading('2. 安装与启动', level=1)
    
    doc.add_heading('方式一：安装器安装（推荐）', level=2)
    steps = [
        '双击运行 QA-Tool-Setup-2.6.0.exe',
        '按照向导提示选择安装路径',
        '可选择是否安装 ESP32 硬件驱动',
        '完成安装后，桌面会出现快捷方式',
    ]
    for i, step in enumerate(steps, 1):
        p = doc.add_paragraph(f'{i}. {step}')
        set_paragraph_font(p)
    
    doc.add_paragraph('')
    add_screenshot(doc, 'D:/projects/QA-Tool/logo.png', '安装向导界面')
    
    doc.add_heading('方式二：便携版', level=2)
    p = doc.add_paragraph('解压 QA-Tool-v2.6.0-portable.zip，直接运行 QA-Tool.exe 即可。')
    set_paragraph_font(p)
    
    doc.add_heading('首次启动', level=2)
    p = doc.add_paragraph('使用默认账号登录：')
    set_paragraph_font(p)
    p = doc.add_paragraph('用户名：admin')
    set_paragraph_font(p)
    p = doc.add_paragraph('密码：admin')
    set_paragraph_font(p)
    doc.add_paragraph('')
    add_screenshot(doc, 'D:/projects/QA-Tool/logo.png', '登录界面')
    
    doc.add_page_break()
    
    # 3. 界面概览
    doc.add_heading('3. 界面概览', level=1)
    p = doc.add_paragraph(
        'QA-Tool 采用侧边栏 + 主面板布局，左侧为功能导航，右侧为分析区域。'
    )
    set_paragraph_font(p)
    
    doc.add_paragraph('')
    add_screenshot(doc, 'D:/projects/QA-Tool/logo.png', 'QA-Tool 主界面')
    
    doc.add_heading('界面区域说明', level=2)
    areas = [
        '侧边栏：功能模块分类导航，支持折叠/展开',
        '主面板：分析配置、数据表格、结果显示',
        '状态栏：当前状态、版本信息',
    ]
    for a in areas:
        p = doc.add_paragraph(a, style='List Bullet')
        set_paragraph_font(p)
    
    doc.add_page_break()
    
    # 4. 快速入门
    doc.add_heading('4. 快速入门', level=1)
    
    doc.add_heading('示例：SPC 控制图分析', level=2)
    steps = [
        '从侧边栏选择 "SPC 控制图"',
        '在数据表格中粘贴或导入数据',
        '选择控制图类型（如 XBar-R）',
        '设置规格限（USL/LSL）',
        '点击 "运行分析" 按钮',
        '查看控制图和分析结果',
    ]
    for i, step in enumerate(steps, 1):
        p = doc.add_paragraph(f'{i}. {step}')
        set_paragraph_font(p)
    
    doc.add_paragraph('')
    add_screenshot(doc, 'D:/projects/QA-Tool/logo.png', 'SPC 分析示例')
    
    doc.add_heading('示例：过程能力分析', level=2)
    steps = [
        '从侧边栏选择 "过程能力"',
        '导入数据并选择数据列',
        '输入 USL 和 LSL',
        '点击 "运行分析"',
        '查看 Cp/Cpk/Pp/Ppk 指标和直方图',
    ]
    for i, step in enumerate(steps, 1):
        p = doc.add_paragraph(f'{i}. {step}')
        set_paragraph_font(p)
    
    doc.add_paragraph('')
    add_screenshot(doc, 'D:/projects/QA-Tool/logo.png', '能力分析示例')
    
    doc.add_page_break()
    
    # 5. 功能模块
    doc.add_heading('5. 功能模块', level=1)
    
    doc.add_heading('5.1 质量分析', level=2)
    modules = [
        ('SPC 控制图', '支持 XBar-R/S、I-MR、P/NP/C/U、CUSUM、EWMA 等 9 种控制图，自动检测 8 条 Nelson 判异规则。'),
        ('过程能力', '正态/非正态能力分析，支持 Cp/Cpk/Pp/Ppk/Cpm，自动评级。'),
        ('MSA', 'Gage R&R（交叉/嵌套）、Type 1 量具研究、偏倚/线性分析。'),
        ('假设检验', 't 检验、ANOVA、卡方检验、TOST 等价检验、非参数检验。'),
    ]
    for name, desc in modules:
        p = doc.add_paragraph(f'{name}：{desc}')
        set_paragraph_font(p)
    
    doc.add_heading('5.2 IE 工业工程', level=2)
    modules = [
        ('时间研究', '标准时间计算、评比系数、宽放率。'),
        ('OEE', '设备综合效率分析、六大损失分解。'),
        ('SMED', '快速换模分析、内外作业分离。'),
        ('TPM', '全面生产维护、OEE/MTBF/MTTR 分析。'),
    ]
    for name, desc in modules:
        p = doc.add_paragraph(f'{name}：{desc}')
        set_paragraph_font(p)
    
    doc.add_heading('5.3 工程工具', level=2)
    modules = [
        ('FMEA', '失效模式与影响分析、RPN 计算、风险着色。'),
        ('8D', '八项纪律问题解决、D1-D8 分步向导。'),
        ('PPAP', '生产件批准程序、18 项检查清单。'),
        ('鱼骨图', '交互式鱼骨图、3 级嵌套、拖拽编辑。'),
    ]
    for name, desc in modules:
        p = doc.add_paragraph(f'{name}：{desc}')
        set_paragraph_font(p)
    
    doc.add_page_break()
    
    # 6. 常见问题
    doc.add_heading('6. 常见问题', level=1)
    
    faqs = [
        ('Q：如何导入 Excel 数据？', 'A：在数据表格区域右键选择 "导入数据"，或使用快捷键 Ctrl+O。'),
        ('Q：如何导出分析报告？', 'A：分析完成后点击 "导出报告" 按钮，支持 PDF/Word/HTML 格式。'),
        ('Q：如何连接 ESP32 设备？', 'A：在设置中启用 ESP32 扩展，连接设备后在设备监控 Tab 查看。'),
        ('Q：如何修改登录密码？', 'A：管理员账户可在 "用户管理" 中修改其他用户密码。'),
        ('Q：分析结果如何保存？', 'A：使用 "保存项目" 功能（.qap 格式），包含数据和分析结果。'),
    ]
    for q, a in faqs:
        p = doc.add_paragraph(q, style='Intense Quote')
        set_paragraph_font(p)
        p = doc.add_paragraph(a)
        set_paragraph_font(p)
        doc.add_paragraph('')
    
    doc.add_page_break()
    
    # 联系方式
    doc.add_heading('技术支持', level=1)
    p = doc.add_paragraph('如有问题，请联系技术支持团队。')
    set_paragraph_font(p)
    doc.add_paragraph('')
    p = doc.add_paragraph('© 2026 QA-Tool. All rights reserved.')
    set_paragraph_font(p)
    
    # 保存文档
    doc.save('D:/projects/QA-Tool/使用指南.docx')
    print('使用指南已创建：D:/projects/QA-Tool/使用指南.docx')


if __name__ == '__main__':
    create_user_guide()
