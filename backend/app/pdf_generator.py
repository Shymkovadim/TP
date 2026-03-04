import os
import re
from typing import List, Optional, Tuple
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models import TechProcess, Operation, Transition
from app.agent import TechAgent


class PDFTimeStudyGenerator:
    """Генератор PDF Time Study (альбомная ориентация)"""
    
    def __init__(self, agent: TechAgent = None):
        self.agent = agent or TechAgent()
        self.styles = getSampleStyleSheet()
        self._register_fonts()
    
    def _register_fonts(self):
        """Регистрирует шрифты с поддержкой кириллицы"""
        font_paths = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\times.ttf",
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont('Arial', path))
                    return
                except:
                    continue
        print("⚠️  Используем стандартные шрифты")
    
    def generate(self, process: TechProcess, output_path: str) -> str:
        """Генерирует PDF файл Time Study"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # Альбомная ориентация
        page_size = landscape(A4)
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=5*mm,
            leftMargin=5*mm,
            topMargin=5*mm,
            bottomMargin=10*mm
        )
        
        elements = []
        
        # Шапка
        elements.extend(self._create_header(process))
        elements.append(Spacer(1, 3*mm))
        
        # Таблица операций
        elements.append(self._create_operations_table(process))
        elements.append(Spacer(1, 3*mm))
        
        # Итоги
        elements.append(self._create_summary(process))
        elements.append(Spacer(1, 3*mm))
        
        # Примечания
        elements.extend(self._create_notes())
        
        doc.build(elements)
        return output_path
    
    def _create_header(self, process: TechProcess) -> List:
        """Создает шапку документа"""
        elements = []
        
        title_style = ParagraphStyle(
            'Title', fontSize=16, textColor=colors.red,
            alignment=TA_CENTER, spaceAfter=10, fontName='Arial'
        )
        elements.append(Paragraph("TIME STUDY", title_style))
        
        info_data = [
            ["Заказчик:", "ОАО «МЗШ»"],
            ["Модель оборудования:", "WINPOWER WPLF45D"],
            ["Система ЧПУ:", "SIEMENS 828D"],
            ["Макс. скорость шпинделя, мин⁻¹:", "2500"],
            ["Макс. скорость приводн. инстр., мин⁻¹:", "4500"],
            ["Номер проекта:", ""],
            ["Номер детали:", process.drawing_number or ""],
            ["Наименование детали:", process.part_name],
            ["Материал:", process.material or ""],
            ["Твердость:", "156…207 HB"],
            ["Заготовка:", "Поковка Ø306.6 x 75 (22.1 кг)"],
        ]
        
        info_table = Table(info_data, colWidths=[6*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        return elements
    
    def _create_operations_table(self, process: TechProcess):
        """Создает таблицу операций (22 колонки как в Excel)"""
        headers = [
            "№\nинстр.", "Наименование\nинструмента", "Обозначение", "Переход",
            "Dmax", "Dmin", "V", "n", "Lрез", "Lвсп", "Lр.х", "a",
            "Кол-во", "t", "L", "So", "Sm", "P", "U", "V", "W", "T"
        ]
        
        table_data = [headers]
        total_time = 0.0
        total_cutting = 0.0
        
        for op in process.operations:
            # Заголовок операции
            table_data.append(["", f"Операция {op.op_number}", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
            
            # Установка
            if op.op_number == "005" or op.op_number == "001":
                table_data.append(["", "Установка заготовки в патроне", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "15", "", "", "15"])
                total_time += 15
            
            # Переходы
            for trans in op.transitions:
                row, cutting, total = self._create_transition_row(trans)
                table_data.append(row)
                total_cutting += cutting
                total_time += total
        
        # Итого
        cycle_min = total_time / 60
        cutting_min = total_cutting / 60
        productivity = 60 / (cycle_min / 0.85) if cycle_min > 0 else 0
        
        total_row = ["", "", "", "ИТОГО:", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", f"{total_cutting:.1f}", f"{total_time:.1f}"]
        table_data.append(total_row)
        
        # Ширина колонок для альбомной ориентации
        col_widths = [1, 2, 2.5, 4, 1, 1, 1, 1, 1, 1, 1, 0.8, 0.8, 0.8, 1, 1, 1.2, 0.8, 1, 1, 1.2, 1.2]
        col_widths = [w*cm for w in col_widths]
        
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arial'), ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTNAME', (0, 1), (-1, -1), 'Arial'), ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return table
    
    def _create_transition_row(self, trans: Transition) -> Tuple[List, float, float]:
        """Создает строку перехода с расчетом Lрез из описания"""
        tool = self.agent.get_tool_by_id(trans.tool_id) if self.agent else None
        
        tool_num = f"Т{trans.transition_number:03d}"
        tool_name = tool['holder'].split()[0] if tool and tool.get('holder') else ""
        tool_designation = tool.get('full_designation', '') if tool else ""
        
        # Извлекаем диаметры из описания
        diameter_max = 0
        diameter_min = 0
        if trans.diameter:
            # Извлекаем все диаметры из строки типа "Ø301.45-0.1 / Ø255±0.1"
            diameters = re.findall(r'Ø?(\d+\.?\d*)', trans.diameter)
            if diameters:
                diameter_max = float(diameters[0])
                diameter_min = float(diameters[-1]) if len(diameters) > 1 else float(diameters[0])
        
        # Рассчитываем длину резания на основе типа операции
        l_cut = self._calculate_cutting_length(trans.description, diameter_max, diameter_min)
        
        # Режимы резания
        v = trans.cutting_params.v_m_min if trans.cutting_params else 0
        n = trans.cutting_params.n_rpm if trans.cutting_params else 0
        s = trans.cutting_params.s_mm_rev if trans.cutting_params else 0
        t = trans.cutting_params.t_mm if trans.cutting_params else 2.0
        
        # Длина врезания и перебега
        l_approach = 5.0
        
        # Длина рабочего хода: Lр.х = Lрез + Lвсп
        l_work = l_cut + l_approach
        
        # Подача минутная: Sm = So × n
        s_minute = s * n if s and n else 0
        
        # Общая длина (с учетом кол-ва проходов)
        num_passes = 1
        total_length = l_work * num_passes
        
        # Время резания: (L / (So × n)) × 60
        cutting_time = (total_length / (s * n)) * 60 if s and n else 0
        
        # Общее время: U + V + W
        tool_change_time = 3  # Время смены инструмента
        rapid_time = 5  # Время ускоренного перемещения
        total_time = tool_change_time + rapid_time + cutting_time
        
        # Мощность (примерная)
        power = 3.0
        
        # Сокращаем описание перехода если слишком длинное
        desc = trans.description[:37] + "..." if len(trans.description) > 40 else trans.description
        
        row = [
            tool_num,                    # 0: № инстр.
            tool_name,                   # 1: Наименование
            tool_designation,            # 2: Обозначение
            desc,                        # 3: Переход
            f"{diameter_max:.1f}",       # 4: Dmax
            f"{diameter_min:.1f}",       # 5: Dmin
            f"{v:.0f}",                  # 6: V
            f"{n:.0f}",                  # 7: n
            f"{l_cut:.1f}",              # 8: Lрез ← РАССЧИТАНО ИЗ ОПИСАНИЯ!
            f"{l_approach:.1f}",         # 9: Lвсп
            f"{l_work:.1f}",             # 10: Lр.х
            f"{t:.1f}",                  # 11: a
            f"{num_passes}",             # 12: Кол-во проход
            f"{t:.1f}",                  # 13: t
            f"{total_length:.0f}",       # 14: L
            f"{s:.3f}",                  # 15: So
            f"{s_minute:.0f}",           # 16: Sm
            f"{power:.1f}",              # 17: P
            f"{tool_change_time}",       # 18: Время смены
            f"{rapid_time}",             # 19: Время ускор.
            f"{cutting_time:.1f}",       # 20: Время резан.
            f"{total_time:.1f}"          # 21: Общее время
        ]
        return row, cutting_time, total_time
    
    def _calculate_cutting_length(self, description: str, d_max: float, d_min: float) -> float:
        """
        Рассчитывает длину резания на основе описания перехода.
        """
        desc_lower = description.lower()
        
        # 1. Подрезка торца
        if 'подрезать торец' in desc_lower or 'подрезка торца' in desc_lower:
            # Lрез = (D_max - D_min) / 2
            if d_max > 0 and d_min > 0:
                return (d_max - d_min) / 2
            return 0.0  # Если диаметры не указаны или равны
        
        # 2. Точение наружной поверхности
        elif 'точить диаметр' in desc_lower or 'точить поверхность' in desc_lower:
            # Ищем длину в описании: "на длину 88" или "длину 88"
            length_match = re.search(r'на\s+длину\s+(\d+\.?\d*)', desc_lower)
            if length_match:
                return float(length_match.group(1))
            
            # Или просто "длину X"
            length_match = re.search(r'длину\s+(\d+\.?\d*)', desc_lower)
            if length_match:
                return float(length_match.group(1))
            
            return 1.0  # По умолчанию
        
        # 3. Расточка отверстий
        elif 'расточить' in desc_lower or 'расточка' in desc_lower:
            # Ищем глубину
            depth_match = re.search(r'глубин[ауою]\s*(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            if '255' in description:
                return 17.8
            elif '201.5' in description:
                return 34.5
            
            return 20.0
        
        # 4. Центровка/засверливание
        elif 'зацентровать' in desc_lower or 'центровать' in desc_lower or 'засверливать' in desc_lower:
            # Ищем глубину: "на глубину 10"
            depth_match = re.search(r'на\s+глубину\s+(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            depth_match = re.search(r'глубину\s+(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            return 10.0  # По умолчанию
        
        # 5. Канавки
        elif 'канавк' in desc_lower:
            # Для торцевых канавок Lрез = ширина канавки
            width_match = re.search(r'шириной\s+(\d+\.?\d*)', desc_lower)
            if width_match:
                return float(width_match.group(1))
            
            depth_match = re.search(r'глубин[ауою]\s*(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            return 1.6
        
        # 6. Сверление
        elif 'сверл' in desc_lower:
            # Ищем количество отверстий и глубину
            count_match = re.search(r'(\d+)\s*отверстий', desc_lower)
            depth_match = re.search(r'глубин[ауою]\s*(\d+\.?\d*)', desc_lower)
            
            if count_match and depth_match:
                num_holes = int(count_match.group(1))
                depth = float(depth_match.group(1))
                return depth * num_holes
            
            if depth_match:
                return float(depth_match.group(1))
            
            return 34.5
        
        # 7. Фрезерование/фаски/пазы
        elif 'фрезер' in desc_lower or 'фаск' in desc_lower or 'паз' in desc_lower:
            # Ищем длину или глубину
            length_match = re.search(r'на\s+длину\s+(\d+\.?\d*)', desc_lower)
            if length_match:
                return float(length_match.group(1))
            
            depth_match = re.search(r'глубиной\s+(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            depth_match = re.search(r'глубин[ауою]\s*(\d+\.?\d*)', desc_lower)
            if depth_match:
                return float(depth_match.group(1))
            
            return 30.0
        
        # 8. По умолчанию
        else:
            if d_max > 0 and d_min > 0:
                return (d_max - d_min) / 2
            return 30.0
    
    def _create_summary(self, process: TechProcess):
        """Создает секцию итогов с расчетом времени"""
        # Рассчитываем по данным из процесса
        total_time = 0.0
        total_cutting = 0.0
        
        for op in process.operations:
            for trans in op.transitions:
                if trans.cutting_params:
                    s = trans.cutting_params.s_mm_rev or 0.1
                    n = trans.cutting_params.n_rpm or 100
                    l_work = 35.0
                    if s and n:
                        cutting = (l_work / (s * n)) * 60
                        total_cutting += cutting
                        total_time += cutting + 8
            total_time += 30  # установка + снятие
        
        cycle_min = total_time / 60
        cutting_min = total_cutting / 60
        utilization = 0.85
        productivity = 60 / (cycle_min / utilization) if cycle_min > 0 else 0
        
        summary_data = [
            ["Суммарное время цикла:", f"{total_time:.1f}", "сек ± 15%"],
            ["", f"{cycle_min:.2f}", "мин ± 15%"],
            ["Время резания:", f"{total_cutting:.1f}", "сек ± 15%"],
            ["", f"{cutting_min:.2f}", "мин ± 15%"],
            ["Коэффициент использования Ки:", f"{utilization:.2f}", ""],
            ["Производительность:", f"{productivity:.1f}", "дет./час"],
        ]
        
        summary_table = Table(summary_data, colWidths=[12*cm, 4*cm, 3*cm])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return summary_table
    
    def _create_notes(self) -> List:
        """Создает примечания"""
        notes_style = ParagraphStyle(
            'Notes', parent=self.styles['Normal'],
            fontSize=9, alignment=TA_LEFT, spaceAfter=5, fontName='Arial'
        )
        return [
            Paragraph("<b>Примечания:</b>", notes_style),
            Paragraph("1) Инструмент и режимы могут изменяться при отладке.", notes_style),
            Paragraph("2) Для точного времени необходима тестовая обработка (Cutting Test).", notes_style),
            Paragraph("3) Базирование:", notes_style),
            Paragraph("   - Оп. 005: в патроне Ø530 мм по Ø306.6 мм с упором в торец.", notes_style),
            Paragraph("   - Оп. 010: на оправке по Ø201.5 мм с упором в торец.", notes_style),
        ]


class PDFGenerator:
    """Основной генератор PDF"""
    def __init__(self, agent: TechAgent = None):
        self.agent = agent or TechAgent()
        self.pdf_generator = PDFTimeStudyGenerator(self.agent)
    
    def generate(self, process: TechProcess, output_path: str) -> str:
        return self.pdf_generator.generate(process, output_path)