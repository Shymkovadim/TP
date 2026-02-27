import json
import re
from typing import Optional, Dict, List

from groq import Groq

from app.config import settings, TECH_PROCESS_PROMPT
from app.models import TechProcess, Operation, Transition, Tool
from app.parser import parse_free_text


class TechAgent:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> dict:
        """Загружает базу знаний (инструменты, правила ЕСКД)"""
        import os
        kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base")
        
        kb = {}
        for filename in ["tools.json", "eskd_rules.json", "materials.json"]:
            filepath = os.path.join(kb_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    kb[filename.replace('.json', '')] = json.load(f)
        return kb
    
    def analyze_process(self, user_input: str, material: Optional[str] = None) -> TechProcess:
        """Анализирует описание обработки и формирует технологический процесс"""
        
        # Предварительный парсинг
        parsed = parse_free_text(user_input)
        
        # Формируем контекст с базой знаний
        kb_context = f"""
База инструментов:
{json.dumps(self.knowledge_base.get('tools', {}), ensure_ascii=False, indent=2)}

Правила ЕСКД:
{json.dumps(self.knowledge_base.get('eskd_rules', {}), ensure_ascii=False, indent=2)}
"""
        
        # Запрос к LLM
        completion = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": TECH_PROCESS_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""
Контекст базы знаний:
{kb_context}

Входные данные от пользователя:
"{user_input}"

Предварительный анализ:
{json.dumps(parsed, ensure_ascii=False)}

Материал заготовки: {material or 'не указан'}

Сформируй технологический процесс в формате JSON.
"""
                }
            ],
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS
        )
        
        response = completion.choices[0].message.content
        
        # Парсим JSON из ответа
        tech_process_data = self._parse_json(response)
        
        if tech_process_data:
            return TechProcess(**tech_process_data)
        else:
            raise ValueError("Не удалось распарсить ответ от AI")
    
    def _parse_json(self, response: str) -> Optional[dict]:
        """Извлекает JSON из ответа модели"""
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None
    
    def validate_process(self, process: TechProcess) -> List[str]:
        """Проверяет технологический процесс на соответствие правилам"""
        warnings = []
        
        for op in process.operations:
            if not op.op_number.isdigit() or len(op.op_number) != 3:
                warnings.append(f"Операция {op.op_name}: номер должен быть 3-значным")
            
            for trans in op.transitions:
                if not trans.tool:
                    warnings.append(f"Переход {trans.transition_number}: не указан инструмент")
                if not trans.cutting_params:
                    warnings.append(f"Переход {trans.transition_number}: не указаны режимы резания")
        
        return warnings