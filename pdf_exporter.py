from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import datetime
import os
import cv2
import numpy as np
import tempfile

class PDFExporter:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.orange = colors.HexColor('#D85A30')
        self.dark = colors.HexColor('#1a1a2e')
        self.light_orange = colors.HexColor('#FAECE7')

    def export(self, output_path, food_items, totals, daily_goal, annotated_image_rgb=None):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        story = []
        title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.orange,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.grey,
            spaceAfter=16,
            alignment=TA_CENTER
        )
        section_style = ParagraphStyle(
            'Section',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=self.orange,
            spaceBefore=16,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        normal_style = ParagraphStyle(
            'Normal2',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4
        )
        story.append(Paragraph("NutriScan PK", title_style))
        story.append(Paragraph("Pakistani Food Nutrition Analysis Report", subtitle_style))
        story.append(Paragraph(
            f"Generated: {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}",
            subtitle_style
        ))
        story.append(Spacer(1, 12))

        if annotated_image_rgb is not None:
            try:
                tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                img_bgr = cv2.cvtColor(annotated_image_rgb, cv2.COLOR_RGB2BGR)
                cv2.imwrite(tmp.name, img_bgr)
                rl_img = RLImage(tmp.name, width=4*inch, height=3*inch)
                rl_img.hAlign = 'CENTER'
                story.append(rl_img)
                story.append(Spacer(1, 12))
            except:
                pass

        story.append(Paragraph("Meal Summary", section_style))
        summary_data = [
            ['Metric', 'Value', 'Daily Goal', 'Remaining'],
            [
                'Calories',
                f"{totals['calories']} kcal",
                f"{daily_goal} kcal",
                f"{max(0, daily_goal - totals['calories'])} kcal"
            ],
            [
                'Protein',
                f"{totals['protein']}g",
                '50g',
                f"{max(0, 50 - totals['protein'])}g"
            ],
            [
                'Carbohydrates',
                f"{totals['carbs']}g",
                '250g',
                f"{max(0, 250 - totals['carbs'])}g"
            ],
            [
                'Fat',
                f"{totals['fat']}g",
                '65g',
                f"{max(0, 65 - totals['fat'])}g"
            ],
        ]
        summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_orange, colors.white]),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWHEIGHT', (0, 0), (-1, -1), 28),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 8))

        story.append(Paragraph("Detected Food Items", section_style))
        if food_items:
            items_data = [['Food Item', 'Grams', 'Calories', 'Protein', 'Carbs', 'Fat']]
            for item in food_items:
                items_data.append([
                    item['name'].title(),
                    f"{item['grams']}g",
                    f"{item['calories']} kcal",
                    f"{item['protein']}g",
                    f"{item['carbs']}g",
                    f"{item['fat']}g"
                ])
            items_table = Table(items_data, colWidths=[1.3*inch, 0.8*inch, 1*inch, 0.9*inch, 0.9*inch, 0.9*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.dark),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('ROWHEIGHT', (0, 0), (-1, -1), 24),
            ]))
            story.append(items_table)
        else:
            story.append(Paragraph("No food items recorded.", normal_style))

        story.append(Spacer(1, 12))
        goal_pct = min(100, round((totals['calories'] / daily_goal) * 100))
        if goal_pct < 50:
            status = "Under target — consider eating more to meet your daily goal."
        elif goal_pct <= 90:
            status = "On track — great balance for the day."
        elif goal_pct <= 100:
            status = "Almost at goal — one small snack and you are there."
        else:
            status = "Goal exceeded — consider lighter meals for the rest of the day."

        story.append(Paragraph("Daily Progress", section_style))
        story.append(Paragraph(
            f"You have consumed {totals['calories']} kcal which is {goal_pct}% of your {daily_goal} kcal daily goal.",
            normal_style
        ))
        story.append(Paragraph(f"Status: {status}", normal_style))
        story.append(Spacer(1, 16))
        story.append(Paragraph(
            "Generated by NutriScan PK — AI-Powered Pakistani Food Nutrition Tracker",
            subtitle_style
        ))
        doc.build(story)
        return output_path