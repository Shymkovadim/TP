from pydantic import BaseModel, Field
from typing import Optional, List


class CuttingParams(BaseModel):
    v_m_min: Optional[int] = Field(None, description="Скорость резания, м/мин")
    s_mm_rev: Optional[float] = Field(None, description="Подача, мм/об")
    t_mm: Optional[float] = Field(None, description="Глубина резания, мм")
    n_rpm: Optional[int] = Field(None, description="Частота вращения, об/мин")


class Tool(BaseModel):
    name: str = Field(..., description="Наименование инструмента")
    gost: Optional[str] = Field(None, description="ГОСТ или ТУ")
    material: Optional[str] = Field(None, description="Материал режущей части")
    geometry: Optional[str] = Field(None, description="Геометрия/форма")
    size: Optional[str] = Field(None, description="Размерные параметры")


class Transition(BaseModel):
    transition_number: int = Field(..., description="№ перехода")
    description: str = Field(..., description="Описание перехода по ЕСКД")
    tool: Optional[Tool] = Field(None, description="Применяемый инструмент")
    cutting_params: Optional[CuttingParams] = Field(None, description="Режимы резания")


class Operation(BaseModel):
    op_number: str = Field(..., description="Номер операции (005, 010...)")
    op_name: str = Field(..., description="Наименование операции")
    equipment: Optional[str] = Field(None, description="Оборудование/станок")
    transitions: List[Transition] = Field(default_factory=list, description="Переходы операции")


class TechProcess(BaseModel):
    part_name: str = Field(..., description="Наименование детали")
    drawing_number: Optional[str] = Field(None, description="№ чертежа")
    material: Optional[str] = Field(None, description="Материал заготовки")
    operations: List[Operation] = Field(default_factory=list, description="Маршрут операций")
    notes: Optional[str] = Field(None, description="Примечания")