from pydantic import BaseModel, Field
from typing import Optional, List


class CuttingParams(BaseModel):
    v_m_min: Optional[int] = Field(None, description="Скорость резания мин, м/мин")
    v_m_max: Optional[int] = Field(None, description="Скорость резания макс, м/мин")
    s_mm_rev: Optional[float] = Field(None, description="Подача, мм/об")
    t_mm: Optional[float] = Field(None, description="Глубина резания, мм")
    n_rpm: Optional[int] = Field(None, description="Частота вращения, об/мин")


class Transition(BaseModel):
    transition_number: int = Field(..., description="№ перехода")
    description: str = Field(..., description="Описание перехода по ЕСКД")
    tool_id: str = Field(..., description="ID инструмента из базы знаний (например, TOOL-001)")
    auxiliary_tools: Optional[List[str]] = Field(None, description="ID вспомогательного инструмента (AUX-001...)")
    cutting_params: Optional[CuttingParams] = Field(None, description="Режимы резания")
    diameter: Optional[str] = Field(None, description="Диаметр обработки")
    tolerance: Optional[str] = Field(None, description="Допуск")
    roughness: Optional[str] = Field(None, description="Шероховатость Ra")


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
    cycle_time: Optional[float] = Field(None, description="Время цикла, мин")