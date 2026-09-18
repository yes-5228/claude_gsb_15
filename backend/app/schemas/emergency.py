"""应急情况处置记录相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.core.constants import (
    EMERGENCY_RESPONSE_LIMITS_MINUTES,
    OPEN_EMERGENCY_STATUSES,
    EmergencyStatus,
    EmergencyType,
)
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
    event_type: EmergencyType = Field(default=EmergencyType.OTHER, description="事件类型")
    title: str = Field(min_length=1, max_length=120, description="事件标题")
    description: str = Field(default="", max_length=1000, description="事件情况描述")
    impact_scope: str = Field(default="", max_length=300, description="影响范围")
    discoverer: str = Field(default="", max_length=60, description="发现人")
    images: list[str] = Field(default_factory=list, description="现场图片链接")


class EmergencyCreate(EmergencyBase):
    restroom_id: int
    discover_time: datetime | None = Field(default=None, description="发现时间，留空取当前时间")
    initial_remark: str | None = Field(default=None, max_length=500, description="登记说明")


class EmergencyUpdate(BaseModel):
    """仅在待处置阶段允许补正登记信息。"""

    event_type: EmergencyType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    impact_scope: str | None = Field(default=None, max_length=300)
    discoverer: str | None = Field(default=None, max_length=60)
    discover_time: datetime | None = None
    images: list[str] | None = None


class EmergencyHandle(BaseModel):
    """开始处置：登记处置措施并确定响应时间。"""

    responder: str = Field(min_length=1, max_length=60, description="到场处置人")
    measure: str = Field(min_length=1, max_length=1000, description="处置措施")
    response_time: datetime | None = Field(default=None, description="开始处置时间，留空取当前时间")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EmergencyRecover(BaseModel):
    """处置后补充恢复情况与造成的影响。"""

    recover_note: str = Field(min_length=1, max_length=1000, description="恢复情况")
    impact_detail: str | None = Field(default=None, max_length=1000, description="造成的影响")
    recover_time: datetime | None = Field(default=None, description="恢复时间，留空取当前时间")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EmergencyStatusUpdate(BaseModel):
    """通用状态流转（主要用于关闭）。"""

    to_status: EmergencyStatus = Field(description="目标状态")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="处理说明")


class EmergencyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    event_type: str
    title: str
    description: str
    impact_scope: str
    status: str
    discoverer: str
    discover_time: datetime
    response_time: datetime | None = None
    responder: str
    measure: str | None = None
    recover_time: datetime | None = None
    recover_note: str | None = None
    impact_detail: str | None = None
    close_time: datetime | None = None
    images: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    records: list[EmergencyRecordOut] = Field(default_factory=list)

    @computed_field(description="按事件类型约定的响应时限（分钟）")
    @property
    def response_limit_minutes(self) -> int:
        return EMERGENCY_RESPONSE_LIMITS_MINUTES.get(self.event_type, 30)

    @computed_field(description="响应耗时：发现到开始处置（分钟）")
    def response_duration_minutes(self) -> int | None:
        if self.response_time is None:
            return None
        seconds = (self.response_time - self.discover_time).total_seconds()
        return max(0, round(seconds / 60))

    @computed_field(description="事件持续时长：发现到恢复，未恢复取至今（分钟）")
    def handle_duration_minutes(self) -> int:
        end = self.recover_time or datetime.now()
        seconds = (end - self.discover_time).total_seconds()
        return max(0, round(seconds / 60))

    @computed_field(description="响应是否超过约定时限")
    @property
    def response_overdue(self) -> bool:
        duration = self.response_duration_minutes
        if duration is not None:
            return duration > self.response_limit_minutes
        # 尚未到场处置：仅仍在待处置阶段且已超过时限才判定超时（误报作废关闭不算）
        if self.status != EmergencyStatus.PENDING.value:
            return False
        elapsed = (datetime.now() - self.discover_time).total_seconds() / 60
        return elapsed > self.response_limit_minutes

    @computed_field(description="是否仍在处置中")
    @property
    def is_open(self) -> bool:
        return self.status in OPEN_EMERGENCY_STATUSES
