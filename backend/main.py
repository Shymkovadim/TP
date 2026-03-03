import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from app.parser import parse_free_text
from app.config import settings
from app.models import TechProcess
from app.agent import TechAgent
from app.pdf_generator import PDFGenerator # Импортируем PDF генератор
app = FastAPI(title="Tech Process Generator API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация компонентов
agent = TechAgent()
pdf_gen = PDFGenerator(agent)


class ProcessRequest(BaseModel):
    description: str  # Свободное описание обработки
    material: Optional[str] = None
    part_name: Optional[str] = None
    drawing_number: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool
    message: str
    process: Optional[TechProcess] = None
    warnings: Optional[list] = None
    file_path: Optional[str] = None


@app.post("/api/analyze")
async def analyze_process(request: ProcessRequest):
    """Анализ описания и формирование техпроцесса"""
    try:
        # Формируем полный запрос
        full_input = f"Деталь: {request.part_name or 'Не указана'}\n"
        full_input += f"Чертеж: {request.drawing_number or 'Не указан'}\n"
        full_input += f"Материал: {request.material or 'Не указан'}\n"
        full_input += f"Описание обработки:\n{request.description}"
        
        # Анализируем через AI
        process = agent.analyze_process(full_input, request.material)
        
        # Валидация
        warnings = agent.validate_process(process)
        
        return {
            "success": True,
            "message": "Техпроцесс сформирован",
            "process": process,
            "warnings": warnings if warnings else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-pdf")
async def generate_pdf(request: ProcessRequest):
    """Генерация PDF файла Time Study"""
    try:
        print(f"📝 Получен запрос на генерацию PDF...")
        
        # Формируем полное описание
        full_input = []
        if request.part_name:
            full_input.append(f"Деталь: {request.part_name}")
        if request.drawing_number:
            full_input.append(f"Чертеж: {request.drawing_number}")
        if request.material:
            full_input.append(f"Материал: {request.material}")
        full_input.append(f"Описание обработки:\n{request.description}")
        
        full_input_str = "\n".join(full_input)
        
        # Анализируем описание
        print("🤖 Анализируем описание...")
        process = agent.analyze_process(full_input_str, request.material)
        print(f"✅ Анализ завершен. Операций: {len(process.operations)}")
        
        # Генерируем PDF - ВАЖНО: передаем ОБА аргумента!
        print("📄 Генерируем PDF...")
        safe_name = request.part_name or "unnamed"
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        filename = f"TimeStudy_{safe_name}.pdf"
        output_path = f"output/{filename}"
        
        # Создаем папку output если нет
        os.makedirs("output", exist_ok=True)
        
        # Вызываем generate с ОБОИМИ аргументами
        pdf_gen.generate(process, output_path)
        print(f"✅ PDF сгенерирован: {output_path}")
        
        return {
            "success": True,
            "message": "PDF сгенерирован",
            "file_path": f"/download/{filename}",
            "filename": filename
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Скачивание файла"""
    file_path = f"output/{filename}"
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Файл не найден")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)