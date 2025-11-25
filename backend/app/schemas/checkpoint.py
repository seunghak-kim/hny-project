from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# ===== CheckPoint Schemas =====
class CheckPointBase(BaseModel):
    thread_id: str
    check_point_ns: str
    check_point_ns_id: str
    parent_checkpoint_id: Optional[str] = None
    type: str
    check_point_data: Dict[str, Any]
    meta_data: Dict[str, Any] = Field(default_factory=dict)


class CheckPointCreate(CheckPointBase):
    pass


class CheckPointUpdate(BaseModel):
    check_point_data: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    parent_checkpoint_id: Optional[str] = None


class CheckPointResponse(CheckPointBase):
    id: int

    class Config:
        from_attributes = True


# ===== CheckPointBlob Schemas =====
class CheckPointBlobBase(BaseModel):
    thread_id: str
    check_point_ns: str
    channel: str
    version: str
    type: str
    blob: bytes


class CheckPointBlobCreate(CheckPointBlobBase):
    pass


class CheckPointBlobResponse(BaseModel):
    id: int
    thread_id: str
    check_point_ns: str
    channel: str
    version: str
    type: str

    class Config:
        from_attributes = True


# ===== CheckPointWrite Schemas =====
class CheckPointWriteBase(BaseModel):
    thread_id: str
    check_point_ns: str
    check_point_id: str
    idx: int
    channel: str
    type: str
    value: Optional[Dict[str, Any]] = None


class CheckPointWriteCreate(CheckPointWriteBase):
    pass


class CheckPointWriteResponse(CheckPointWriteBase):
    id: int

    class Config:
        from_attributes = True
