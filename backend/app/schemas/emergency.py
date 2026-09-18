"""应急情况处置记录相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import EmergencyStatus, EmergencyType
from app.schemas.restroom import RestroomBrief


class EmergencyRecordOut(BaseModel):
    """处置流水节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    operator: str
    remark: str | None = None
    created_at: datetime


class EmergencyBase(BaseModel):
    title: str = Field(min_length=1, max_length=120, description="事件标题")
    event_type: EmergencyType = Field(default=EmergencyType.OTHER, description="事件类型")
    impact_scope: str = Field(default="", max_length=500, description="影响范围")
    measures: str = Field(default="", max_length=1000, description="处置措施")
    reporter: str = Field(default="", max_length=60, description="上报人")
    handler: str = Field(default="", max_length=60, description="处置人")
    response_limit_minutes: int | None = Field(
        default=None, ge=1, le=24 * 60, description="约定响应时限（分钟），留空按事件类型约定"
    )


class EmergencyCreate(EmergencyBase):
    restroom_id: int
    discovered_at: datetime | None = Field(default=None, description="发现时间，留空取当前时间")
    initial_remark: str | None = Field(default=None, max_length=500, description="登记说明")


class EmergencyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    event_type: EmergencyType | None = None
    discovered_at: datetime | None = None
    impact_scope: str | None = Field(default=None, max_length=500)
    measures: str | None = Field(default=None, max_length=1000)
    handler: str | None = Field(default=None, max_length=60)
    response_limit_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    recovery_note: str | None = Field(default=None, max_length=1000, description="恢复情况")
    impact_note: str | None = Field(default=None, max_length=1000, description="造成的影响")


class EmergencyStatusUpdate(BaseModel):
    """一次应急处置流转操作。"""

    to_status: EmergencyStatus = Field(description="目标状态")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="处理说明")
    recovery_note: str | None = Field(
        default=None, max_length=1000, description="恢复情况，流转到已恢复时必填"
    )
    impact_note: str | None = Field(default=None, max_length=1000, description="造成的影响")


class EmergencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    title: str
    event_type: str
    status: str
    discovered_at: datetime
    impact_scope: str
    measures: str
    reporter: str
    handler: str
    response_limit_minutes: int
    response_due_at: datetime | None = None
    responded_at: datetime | None = None
    response_minutes: int | None = Field(default=None, description="响应耗时（分钟）")
    handling_minutes: int | None = Field(default=None, description="处置耗时（分钟）")
    response_overdue: bool = Field(default=False, description="是否响应超时")
    recovered_at: datetime | None = None
    recovery_note: str | None = None
    impact_note: str | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    records: list[EmergencyRecordOut] = Field(default_factory=list)
