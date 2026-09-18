"""应急情况处置记录模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import OPEN_EMERGENCY_STATUSES, EmergencyStatus, EmergencyType
from app.core.database import Base


class Emergency(Base):
    """停水停电、设施爆裂、污损外溢等突发事件的处置记录。"""

    __tablename__ = "emergencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="事件编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    title: Mapped[str] = mapped_column(String(120), comment="事件标题")
    event_type: Mapped[str] = mapped_column(
        String(30), default=EmergencyType.OTHER.value, index=True, comment="事件类型"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EmergencyStatus.PENDING.value, index=True, comment="处置状态"
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="发现时间"
    )
    impact_scope: Mapped[str] = mapped_column(String(500), default="", comment="影响范围")
    measures: Mapped[str] = mapped_column(Text, default="", comment="处置措施")
    reporter: Mapped[str] = mapped_column(String(60), default="", comment="上报人")
    handler: Mapped[str] = mapped_column(String(60), default="", comment="处置人")
    response_limit_minutes: Mapped[int] = mapped_column(
        Integer, default=60, comment="约定响应时限（分钟）"
    )
    response_due_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="响应时限截止时间"
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="响应时间（开始处置）"
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="恢复时间"
    )
    recovery_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="恢复情况")
    impact_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="造成的影响")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="关闭时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="emergencies")  # noqa: F821
    records: Mapped[list["EmergencyRecord"]] = relationship(
        back_populates="emergency",
        cascade="all, delete-orphan",
        order_by="EmergencyRecord.created_at",
    )

    @property
    def response_minutes(self) -> int | None:
        """响应耗时：发现时间到响应时间的分钟数，未响应时为 None。"""
        if self.responded_at is None or self.discovered_at is None:
            return None
        return round((self.responded_at - self.discovered_at).total_seconds() / 60)

    @property
    def handling_minutes(self) -> int | None:
        """处置耗时：响应时间到恢复时间的分钟数，未恢复时为 None。"""
        if self.responded_at is None or self.recovered_at is None:
            return None
        return round((self.recovered_at - self.responded_at).total_seconds() / 60)

    @property
    def response_overdue(self) -> bool:
        """是否响应超时：已响应看实际响应是否晚于时限，未响应看当前是否已逾时限。"""
        if self.response_due_at is None:
            return False
        if self.responded_at is not None:
            return self.responded_at > self.response_due_at
        return self.status in OPEN_EMERGENCY_STATUSES and datetime.now() > self.response_due_at


class EmergencyRecord(Base):
    """应急处置流水，用于还原完整的处置轨迹。"""

    __tablename__ = "emergency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emergency_id: Mapped[int] = mapped_column(
        ForeignKey("emergencies.id", ondelete="CASCADE"), index=True, comment="所属应急事件"
    )
    action: Mapped[str] = mapped_column(String(30), comment="处理动作")
    from_status: Mapped[str] = mapped_column(String(20), default="", comment="原状态")
    to_status: Mapped[str] = mapped_column(String(20), comment="新状态")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="操作人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="操作时间"
    )

    emergency: Mapped["Emergency"] = relationship(back_populates="records")
