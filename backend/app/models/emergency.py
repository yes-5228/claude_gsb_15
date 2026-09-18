"""应急情况处置记录模型。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EmergencyStatus, EmergencyType
from app.core.database import Base


class EmergencyEvent(Base):
    """停水停电、设施爆裂、污损外溢等应急情况的处置记录。"""

    __tablename__ = "emergency_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="事件编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    event_type: Mapped[str] = mapped_column(
        String(20), default=EmergencyType.OTHER.value, index=True, comment="事件类型"
    )
    title: Mapped[str] = mapped_column(String(120), comment="事件标题")
    description: Mapped[str] = mapped_column(Text, default="", comment="事件情况描述")
    impact_scope: Mapped[str] = mapped_column(
        String(300), default="", comment="影响范围（区域、设施、人数等）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EmergencyStatus.PENDING.value, index=True, comment="处置状态"
    )
    discoverer: Mapped[str] = mapped_column(String(60), default="", comment="发现人")
    discover_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="发现时间"
    )
    response_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始处置时间（响应时间）"
    )
    responder: Mapped[str] = mapped_column(String(60), default="", comment="到场处置人")
    measure: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处置措施")
    recover_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="恢复正常时间"
    )
    recover_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="恢复情况")
    impact_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="造成的影响（停业时长、财产损失等）"
    )
    close_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="关闭时间")
    images: Mapped[list[str]] = mapped_column(JSON, default=list, comment="现场图片链接")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="emergencies")  # noqa: F821
    records: Mapped[list["EmergencyRecord"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EmergencyRecord.created_at",
    )


class EmergencyRecord(Base):
    """应急处置流水，用于还原发现、处置、恢复、关闭的完整轨迹。"""

    __tablename__ = "emergency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("emergency_events.id", ondelete="CASCADE"), index=True, comment="所属事件"
    )
    action: Mapped[str] = mapped_column(String(30), comment="处理动作")
    from_status: Mapped[str] = mapped_column(String(20), default="", comment="原状态")
    to_status: Mapped[str] = mapped_column(String(20), comment="新状态")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="操作人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="操作时间"
    )

    event: Mapped["EmergencyEvent"] = relationship(back_populates="records")
