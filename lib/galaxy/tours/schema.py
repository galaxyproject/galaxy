from typing import (
    List,
    Optional,
)

from pydantic import BaseModel


class Tour(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]


class TourList(BaseModel):
    __root__: List[Tour] = []


class TourStep(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    element: Optional[str] = None
    placement: Optional[str] = None
    preclick: Optional[list] = None
    postclick: Optional[list] = None
    textinsert: Optional[str] = None
    backdrop: Optional[bool] = None


class TourDetails(Tour):
    title_default: Optional[str] = None
    steps: List[TourStep]
