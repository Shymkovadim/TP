from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from app.parser import parse_free_text
from app.config import settings
from app.models import TechProcess
from app.agent import TechAgent
from app.excel_generator import ExcelGenerator

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
excel_gen = ExcelGenerator()


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


@app.post("/api/generate-excel")
async def generate_excel(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Генерация Excel-файла"""
    try:
        # Анализируем
        full_input = f"Деталь: {request.part_name or 'Не указана'}\n"
        full_input += f"Описание:\n{request.description}"
        
        process = agent.analyze_process(full_input, request.material)
        
        # Генерируем Excel
        filename = f"tech_process_{request.part_name or 'unnamed'}.xlsx"
        output_path = f"output/{filename}"
        
        excel_gen.generate(process, output_path)
        
        return {
            "success": True,
            "message": "Excel сгенерирован",
            "file_path": f"/download/{filename}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Скачивание сгенерированного файла"""
    file_path = f"output/{filename}"
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Файл не найден")


@app.get("/api/knowledge/tools")
async def get_tools():
    """Получить список инструментов из базы знаний"""
    return agent.knowledge_base.get("tools", {})


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)