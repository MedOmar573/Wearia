from typing import Optional
from pydantic import BaseModel

class ClassifyResponse(BaseModel):
    category: str
    color: str
    confidence: float
    image_url: str
    color_hex: Optional[str] = None
    suggested_type_id: Optional[int] = None
    suggested_color_id: Optional[int] = None
    name: Optional[str] = None
    matiere: Optional[str] = None
    coupe: Optional[str] = None
    saison: Optional[str] = None
    est_thermique: Optional[bool] = None
    est_impermeable: Optional[bool] = None
    style_id: Optional[int] = None
    style_name: Optional[str] = None


