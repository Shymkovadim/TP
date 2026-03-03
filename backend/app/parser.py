import re
from typing import List, Optional


def parse_free_text(text: str) -> dict:
    """
    Простой парсер свободного текста для извлечения ключевых параметров.
    """
    result = {
        "operations": [],
        "dimensions": [],
        "material": None
    }
    
    # Извлечение материала
    material_patterns = [
        r'(сталь\s+\d+[А-Я]?|чугун\s+[А-Я]+|алюминий\s+[А-Я0-9]+)',
        r'([0-9]+[А-Я][0-9]+)'  # типа 45, 40Х, 12Х18Н10Т
    ]
    for pattern in material_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            result["material"] = match.group(1)
            break
    
    # Извлечение операций
    op_keywords = {
        'точить|токар': 'turning',
        'сверл|отверст': 'drilling',
        'фрезер|фреза': 'milling',
        'шлиф|шлифов': 'grinding',
        'нарез|резьб': 'threading',
        'канавк': 'grooving',
        'расточ': 'boring'
    }
    
    for keyword, op_type in op_keywords.items():
        if re.search(keyword, text, re.I):
            result["operations"].append(op_type)
    
    # Извлечение размеров (Ø20, д.20, диаметр 20)
    dim_pattern = r'[Øøд\.]?\s*(\d+(?:\.\d+)?)\s*(?:мм|mm|отв\.?|диаметр)?'
    dimensions = re.findall(dim_pattern, text, re.I)
    result["dimensions"] = [float(d) for d in dimensions if d]
    
    return result