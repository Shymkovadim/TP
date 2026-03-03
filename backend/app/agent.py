import json
import re
import os
from typing import Optional, Dict, List

from groq import Groq

from app.config import settings, TECH_PROCESS_PROMPT
from app.models import TechProcess, Operation, Transition, CuttingParams
from app.parser import parse_free_text


class TechAgent:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> dict:
        """Загружает базу знаний из JSON файлов"""
        kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base")
        
        kb = {}
        for filename in ["tools.json", "eskd_rules.json", "materials.json"]:
            filepath = os.path.join(kb_path, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            kb[filename.replace('.json', '')] = json.loads(content)
                        else:
                            print(f"⚠️  Файл {filename} пустой")
                            kb[filename.replace('.json', '')] = {}
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка JSON в {filename}: {e}")
                    kb[filename.replace('.json', '')] = {}
            else:
                print(f"⚠️  Файл {filename} не найден")
                kb[filename.replace('.json', '')] = {}
        
        return kb
    
    def analyze_process(self, user_input: str, material: Optional[str] = None) -> TechProcess:
        """Анализирует описание обработки и формирует технологический процесс"""
        
        # Формируем контекст с базой инструментов
        tools_summary = self._create_tools_summary()
        
        kb_context = f"""
БАЗА ИНСТРУМЕНТОВ (используй ТОЛЬКО эти ID):
{tools_summary}

ПРАВИЛА ПОДБОРА:
- Подрезка торца (черновая) → TOOL-001
- Подрезка торца (чистовая) → TOOL-002
- Расточка (черновая) → TOOL-003 + AUX-001
- Расточка (чистовая) → TOOL-004 + AUX-001
- Канавки → TOOL-005
- Сверление → TOOL-006 + AUX-002
- Фаски → TOOL-007 + AUX-003
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
{kb_context}

Входные данные от пользователя:
"{user_input}"

Материал заготовки: {material or 'не указан'}

Сформируй технологический процесс в формате JSON.
ВАЖНО: tool_id — ТОЛЬКО из базы (TOOL-001...TOOL-007)!
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
            # Валидация tool_id
            self._validate_tool_ids(tech_process_data)
            return TechProcess(**tech_process_data)
        else:
            raise ValueError("Не удалось распарсить ответ от AI")
    
    def _create_tools_summary(self) -> str:
        """Создаёт краткую выжимку по инструментам"""
        tools = self.knowledge_base.get('tools', {}).get('tools', [])
        summary_lines = []
        
        for tool in tools:
            summary_lines.append(
                f"{tool['id']}: {tool['holder']} + {tool['full_designation']}\n"
                f"  → {tool['description']}\n"
                f"  → V={tool['cutting_params']['v_min']}-{tool['cutting_params']['v_max']}, "
                f"S={tool['cutting_params']['s_min']}-{tool['cutting_params']['s_max']}"
            )
        
        return "\n\n".join(summary_lines)
    
    def _validate_tool_ids(self, data: dict) -> None:
        """Проверяет, что все tool_id существуют в базе"""
        valid_ids = {t['id'] for t in self.knowledge_base.get('tools', {}).get('tools', [])}
        valid_aux = {t['id'] for t in self.knowledge_base.get('tools', {}).get('auxiliary_tools', [])}
        
        for op in data.get('operations', []):
            for trans in op.get('transitions', []):
                tool_id = trans.get('tool_id')
                if tool_id and tool_id not in valid_ids:
                    # Заменяем на ближайший подходящий
                    trans['tool_id'] = self._find_best_tool_id(trans.get('description', ''))
                
                # Проверяем вспомогательный инструмент
                aux_tools = trans.get('auxiliary_tools', [])
                if aux_tools:
                    trans['auxiliary_tools'] = [
                        aux for aux in aux_tools if aux in valid_aux
                    ]
    
    def _find_best_tool_id(self, description: str) -> str:
        """Находит подходящий tool_id по описанию операции"""
        desc_lower = description.lower()
        
        if 'канавк' in desc_lower:
            return 'TOOL-005'
        elif 'сверл' in desc_lower:
            return 'TOOL-006'
        elif 'фаск' in desc_lower or 'фрезер' in desc_lower:
            return 'TOOL-007'
        elif 'расточ' in desc_lower:
            if 'окончательн' in desc_lower or 'чистов' in desc_lower:
                return 'TOOL-004'
            else:
                return 'TOOL-003'
        elif 'подрез' in desc_lower or 'торец' in desc_lower:
            if 'окончательн' in desc_lower or 'чистов' in desc_lower:
                return 'TOOL-002'
            else:
                return 'TOOL-001'
        elif 'точить' in desc_lower:
            if 'окончательн' in desc_lower or 'чистов' in desc_lower:
                return 'TOOL-002'
            else:
                return 'TOOL-001'
        
        return 'TOOL-001'  # По умолчанию
    
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
    
    def get_tool_by_id(self, tool_id: str) -> Optional[dict]:
        """Возвращает данные инструмента по ID"""
        tools = self.knowledge_base.get('tools', {}).get('tools', [])
        for tool in tools:
            if tool['id'] == tool_id:
                return tool
        return None
    
    def get_aux_by_id(self, aux_id: str) -> Optional[dict]:
        """Возвращает данные вспомогательного инструмента по ID"""
        aux_tools = self.knowledge_base.get('tools', {}).get('auxiliary_tools', [])
        for aux in aux_tools:
            if aux['id'] == aux_id:
                return aux
        return None
    
    def validate_process(self, process: TechProcess) -> List[str]:
        """Проверяет технологический процесс"""
        warnings = []
        valid_ids = {t['id'] for t in self.knowledge_base.get('tools', {}).get('tools', [])}
        
        for op in process.operations:
            if not op.op_number.isdigit() or len(op.op_number) != 3:
                warnings.append(f"Операция {op.op_name}: номер должен быть 3-значным")
            
            for trans in op.transitions:
                if not trans.tool_id:
                    warnings.append(f"Операция {op.op_number}: не указан tool_id")
                elif trans.tool_id not in valid_ids:
                    warnings.append(f"Операция {op.op_number}: неверный tool_id '{trans.tool_id}'")
                
                if not trans.cutting_params:
                    warnings.append(f"Операция {op.op_number}: не указаны режимы резания")
        
        return warnings