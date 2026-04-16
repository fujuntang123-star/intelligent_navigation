"""
PDF 报告导出工具
使用 reportlab 库生成专业的 PDF 格式职业规划报告
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import markdown


def export_report_to_pdf(report_data: dict, output_path: str = None):
    """
    将职业规划报告导出为 PDF 格式
    
    Args:
        report_data: 包含报告数据的字典，或直接包含 'content' 键的 Markdown 文本
        output_path: 输出文件路径，如果为 None 则返回 BytesIO 对象
    
    Returns:
        BytesIO 对象或 None
    """
    # 检查是否是纯 Markdown 内容
    if 'content' in report_data:
        return _export_markdown_to_pdf(report_data['content'], output_path)
    
    # 创建 PDF 文档
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # 故事列表（内容容器）
    story = []
    
    # 设置样式
    styles = getSampleStyleSheet()
    
    # 注册中文字体（需要系统中有中文字体）
    font_name = 'Helvetica'
    try:
        # Windows 系统可以使用宋体
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        # 直接使用绝对路径
        font_path = r'C:\Windows\Fonts\simsun.ttc'
        pdfmetrics.registerFont(TTFont('Chinese', font_path))
        font_name = 'Chinese'
        print(f"✅ 成功注册中文字体：{font_path}")
    except Exception as e:
        print(f"⚠️ 字体注册失败：{str(e)}")
        print("⚠️ 将使用英文字体，中文可能显示为方块")
    
    # 自定义标题样式
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a56db'),
        spaceAfter=30,
        alignment=1,  # 居中
        fontName=font_name
    )
    
    # 自定义章节标题样式
    heading_style = ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=20,
        fontName=font_name
    )
    
    # 正文样式
    normal_style = ParagraphStyle(
        name='CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8,
        fontName=font_name
    )
    
    # 添加标题
    story.append(Paragraph("职业生涯发展报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 添加基本信息表格
    if 'student_profile' in report_data:
        profile = report_data['student_profile']
        basic_info_data = [
            ['目标岗位', report_data.get('target_job', '未指定')],
            ['学历', profile.get('education', '未填写')],
            ['专业', profile.get('major', '未填写')]
        ]
        
        basic_table = Table(basic_info_data, colWidths=[4*cm, 10*cm])
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(basic_table)
        story.append(Spacer(1, 1*cm))
    
    # 添加匹配度分析
    if 'match_result' in report_data:
        story.append(Paragraph("一、人岗匹配度分析", heading_style))
        match = report_data['match_result']
        
        # 总分
        total_score = match.get('total_score', 0)
        story.append(Paragraph(f"<b>综合匹配得分：{total_score}/100</b>", normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # 详细维度
        details = match.get('details', {})
        score_data = [['维度', '得分']]
        score_data.append(['专业技能', f"{details.get('professional', 0)}/40"])
        score_data.append(['硬性条件', f"{details.get('hard_req', 0)}/20"])
        score_data.append(['软性素质', f"{details.get('soft_skills', 0)}/20"])
        score_data.append(['项目经验', f"{details.get('project_exp', 0)}/20"])
        
        score_table = Table(score_data, colWidths=[8*cm, 6*cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(score_table)
        story.append(Spacer(1, 1*cm))
    
    # 添加职业发展路径
    if 'transfer_paths' in report_data:
        story.append(Paragraph("二、职业发展路径", heading_style))
        
        # 横向换岗路径
        if report_data['transfer_paths']:
            story.append(Paragraph("<b>1. 横向换岗机会</b>", normal_style))
            for idx, path in enumerate(report_data['transfer_paths'], 1):
                target_job = path.get('target_job', '未知岗位')
                similarity = path.get('similarity', 0)
                common_skills = path.get('common_skills', 0)
                story.append(Paragraph(
                    f"{idx}. <b>{target_job}</b> (匹配度：{similarity*100:.0f}%, 共同技能：{common_skills}个)",
                    normal_style
                ))
        
        story.append(Spacer(1, 0.5*cm))
    
    # 添加行动计划
    if 'action_plan' in report_data:
        story.append(Paragraph("三、行动计划建议", heading_style))
        plan = report_data['action_plan']
        
        if 'short_term' in plan:
            story.append(Paragraph("<b>短期计划（1-3 个月）</b>", normal_style))
            story.append(Paragraph(plan['short_term'], normal_style))
            story.append(Spacer(1, 0.3*cm))
        
        if 'mid_term' in plan:
            story.append(Paragraph("<b>中期计划（3-12 个月）</b>", normal_style))
            story.append(Paragraph(plan['mid_term'], normal_style))
            story.append(Spacer(1, 0.3*cm))
    
    # 构建 PDF
    doc.build(story)
    
    # 返回结果
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
        print(f"✅ PDF 报告已保存至：{output_path}")
    else:
        buffer.seek(0)
        return buffer


def _export_markdown_to_pdf(markdown_text: str, output_path: str = None):
    """
    将 Markdown 文本转换为 PDF（支持表格、列表等完整格式）
    
    Args:
        markdown_text: Markdown 格式文本
        output_path: 输出文件路径
    
    Returns:
        BytesIO 对象或 None
    """
    import re
    import markdown2
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    
    # 注册中文字体
    font_name = 'Helvetica'
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        # 直接使用绝对路径
        font_path = r'C:\Windows\Fonts\simsun.ttc'
        pdfmetrics.registerFont(TTFont('Chinese', font_path))
        font_name = 'Chinese'
        print(f"✅ 成功注册中文字体：{font_path}")
    except Exception as e:
        print(f"⚠️ 字体注册失败：{str(e)}")
        print("⚠️ 将使用英文字体，中文可能显示为方块")
    
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a56db'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName=font_name
    )
    
    h1_style = ParagraphStyle(
        name='CustomH1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=20,
        spaceBefore=20,
        fontName=font_name
    )
    
    h2_style = ParagraphStyle(
        name='CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=15,
        spaceBefore=15,
        fontName=font_name
    )
    
    h3_style = ParagraphStyle(
        name='CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=10,
        spaceBefore=10,
        fontName=font_name
    )
    
    normal_style = ParagraphStyle(
        name='CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8,
        fontName=font_name
    )
    
    # 使用 markdown2 解析 Markdown
    markdown_text = markdown_text.replace('\n\n\n', '\n\n')  # 清理多余空行
    
    # 按行处理
    lines = markdown_text.split('\n')
    i = 0
    table_data = []
    in_table = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 检测表格开始（Markdown 表格格式）
        if line.startswith('|') and line.endswith('|') and not line.startswith('|---'):
            # 检查是否是分隔线行
            if not re.match(r'^\|[-\s|]+\|$', line):
                in_table = True
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                table_data.append(cells)
            elif in_table:
                # 分隔线行，跳过
                pass
        elif in_table and line.startswith('|') and line.endswith('|'):
            # 继续表格行
            if not re.match(r'^\|[-\s|]+\|$', line):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                table_data.append(cells)
        elif in_table:
            # 表格结束
            if len(table_data) > 1:  # 至少有表头和数据
                # 创建表格，根据列数动态调整列宽
                num_cols = len(table_data[0])
                if num_cols == 1:
                    col_widths = [14*cm]
                elif num_cols == 2:
                    col_widths = [7*cm, 7*cm]
                elif num_cols == 3:
                    col_widths = [4*cm, 3*cm, 7*cm]  # 第三列最宽
                else:
                    col_widths = [14*cm / num_cols] * num_cols
                
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 顶部对齐
                    ('WORDWRAP', (0, 0), (-1, -1), 'ON'),  # 自动换行
                ]))
                story.append(table)
                story.append(Spacer(1, 0.5*cm))
            table_data = []
            in_table = False
            # 处理当前行（非表格内容）
            if line and not re.match(r'^\|[-\s|]+\|$', line):
                story.append(Paragraph(line, normal_style))
        else:
            # 普通内容
            if not line:
                story.append(Spacer(1, 0.3*cm))
            elif line.startswith('#### '):
                text = line[5:]
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, h3_style))
            elif line.startswith('### '):
                text = line[4:]
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, h3_style))
            elif line.startswith('## '):
                text = line[3:]
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, h2_style))
            elif line.startswith('# '):
                text = line[2:]
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, title_style))
            elif line.startswith('- '):
                # 列表项
                text = line[2:]
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(f"• {text}", normal_style))
            elif line.startswith('> '):
                # 引用
                text = line[2:]
                story.append(Paragraph(f"<i>{text}</i>", normal_style))
            elif re.match(r'^\d+\. ', line):
                # 编号列表（如 "1. 内容"）
                text = re.sub(r'^\d+\. ', '', line)
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, normal_style))
            else:
                # 普通段落
                text = line
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
                story.append(Paragraph(text, normal_style))
        
        i += 1
    
    # 处理未结束的表格
    if in_table and table_data:
        table = Table(table_data, colWidths=[5*cm] * len(table_data[0]))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        story.append(table)
    
    doc.build(story)
    
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
        print(f"✅ PDF 报告已保存至：{output_path}")
    else:
        buffer.seek(0)
        return buffer
