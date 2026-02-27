import os
from typing import List
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.models import TechProcess, Operation, Transition


class ExcelGenerator:
    TEMPLATE_PATH = "templates/tech_process_template.xlsx"
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path or self.TEMPLATE_PATH
    
    def generate(self, process: TechProcess, output_path: str) -> str:
        """Генерирует Excel-файл технологического процесса"""
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Шаблон не найден: {self.template_path}")
        
        # Загружаем шаблон
        wb = load_workbook(self.template_path)
        ws = wb.active
        
        # Заполняем заголовок
        self._fill_header(ws, process)
        
        # Заполняем операции
        self._fill_operations(ws, process.operations)
        
        # Сохраняем файл
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        wb.save(output_path)
        
        return output_path
    
    def _fill_header(self, ws, process: TechProcess):
        """Заполняет шапку документа"""
        mappings = {
            "B2": process.part_name,
            "B3": process.drawing_number or "",
            "B4": process.material or "",
            "B5": process.notes or ""
        }
        for cell, value in mappings.items():
            ws[cell] = value
    
    def _fill_operations(self, ws, operations: List[Operation], start_row: int = 7):
        """Заполняет таблицу операций"""
        row = start_row
        
        for op in operations:
            # Первая строка операции
            ws[f"A{row}"] = op.op_number
            ws[f"B{row}"] = op.op_name
            ws[f"C{row}"] = op.equipment or ""
            
            # Переходы операции
            for i, trans in enumerate(op.transitions):
                if i > 0:
                    row += 1
                    ws[f"A{row}"] = ""  # Пустой номер операции для продолжения
                    ws[f"B{row}"] = ""
                    ws[f"C{row}"] = ""
                
                ws[f"D{row}"] = trans.transition_number
                ws[f"E{row}"] = trans.description
                
                if trans.tool:
                    tool_text = f"{trans.tool.name}"
                    if trans.tool.gost:
                        tool_text += f" ({trans.tool.gost})"
                    if trans.tool.material:
                        tool_text += f", {trans.tool.material}"
                    ws[f"F{row}"] = tool_text
                
                if trans.cutting_params:
                    params = []
                    if trans.cutting_params.v_m_min:
                        params.append(f"V={trans.cutting_params.v_m_min}")
                    if trans.cutting_params.s_mm_rev:
                        params.append(f"S={trans.cutting_params.s_mm_rev}")
                    if trans.cutting_params.t_mm:
                        params.append(f"t={trans.cutting_params.t_mm}")
                    ws[f"G{row}"] = ", ".join(params)
                
                row += 1
        
        # Возвращаем последнюю заполненную строку
        return row