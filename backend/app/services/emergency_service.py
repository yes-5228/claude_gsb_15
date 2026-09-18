"""应急情况处置记录业务逻辑。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    EMERGENCY_RESPONSE_LIMITS,
    EMERGENCY_TRANSITION_ACTIONS,
    EMERGENCY_TRANSITIONS,
    OPEN_EMERGENCY_STATUSES,
    EmergencyStatus,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import Emergency, EmergencyRecord, Restroom
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyOut,
    EmergencyStatusUpdate,
    EmergencyUpdate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "discovered_at": Emergency.discovered_at,
    "response_due_at": Emergency.response_due_at,
    "event_type": Emergency.event_type,
    "status": Emergency.status,
    "code": Emergency.code,
    "updated_at": Emergency.updated_at,
}


def _next_code(db: Session) -> str:
    prefix = datetime.now().strftime("YJ-%Y%m%d")
    seq = (
        db.scalar(
            select(func.count()).select_from(Emergency).where(Emergency.code.like(f"{prefix}-%"))
        )
        or 0
    ) + 1
    while True:
        code = f"{prefix}-{seq:03d}"
        if not db.scalar(select(Emergency.id).where(Emergency.code == code)):
            return code
        seq += 1


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def _default_limit(event_type: str) -> int:
    return EMERGENCY_RESPONSE_LIMITS.get(event_type, EMERGENCY_RESPONSE_LIMITS["其他"])


def _refresh_due(emergency: Emergency) -> None:
    """发现时间或响应时限变化后，重新计算响应时限截止时间。"""
    if emergency.discovered_at is None or emergency.response_limit_minutes is None:
        emergency.response_due_at = None
        return
    emergency.response_due_at = emergency.discovered_at + timedelta(
        minutes=emergency.response_limit_minutes
    )


def get_emergency(db: Session, emergency_id: int) -> Emergency:
    emergency = db.get(Emergency, emergency_id)
    if emergency is None:
        raise NotFoundError(f"应急事件 {emergency_id} 不存在")
    return emergency


def to_out(emergency: Emergency) -> EmergencyOut:
    return EmergencyOut.model_validate(emergency)


def list_emergencies(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    status: str | None = None,
    statuses: list[str] | None = None,
    event_type: str | None = None,
    keyword: str | None = None,
    overdue: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "discovered_at",
    order: str = "desc",
) -> tuple[list[Emergency], int]:
    stmt = select(Emergency)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == Emergency.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(Emergency.restroom_id == restroom_id)
    if status:
        stmt = stmt.where(Emergency.status == status)
    if statuses:
        stmt = stmt.where(Emergency.status.in_(statuses))
    if event_type:
        stmt = stmt.where(Emergency.event_type == event_type)
    if date_from:
        stmt = stmt.where(Emergency.discovered_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Emergency.discovered_at <= datetime.combine(date_to, time.max))
    now = datetime.now()
    if overdue is True:
        # 响应超时：未响应且已逾时限，或实际响应时间晚于时限
        stmt = stmt.where(
            or_(
                and_(
                    Emergency.responded_at.is_(None),
                    Emergency.status.in_(OPEN_EMERGENCY_STATUSES),
                    Emergency.response_due_at.is_not(None),
                    Emergency.response_due_at < now,
                ),
                and_(
                    Emergency.responded_at.is_not(None),
                    Emergency.responded_at > Emergency.response_due_at,
                ),
            )
        )
    elif overdue is False:
        stmt = stmt.where(
            or_(
                and_(
                    Emergency.responded_at.is_(None),
                    Emergency.response_due_at.is_not(None),
                    Emergency.response_due_at >= now,
                ),
                and_(
                    Emergency.responded_at.is_not(None),
                    Emergency.responded_at <= Emergency.response_due_at,
                ),
            )
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Emergency.title.like(like),
                Emergency.impact_scope.like(like),
                Emergency.code.like(like),
                Emergency.handler.like(like),
                Emergency.reporter.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Emergency.discovered_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Emergency.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_emergency(db: Session, payload: EmergencyCreate) -> Emergency:
    restroom_service.get_restroom(db, payload.restroom_id)

    data = _values(payload.model_dump(exclude={"discovered_at", "initial_remark"}))
    discovered_at = payload.discovered_at or datetime.now()
    if data.get("response_limit_minutes") is None:
        data["response_limit_minutes"] = _default_limit(data["event_type"])
    emergency = Emergency(
        code=_next_code(db),
        discovered_at=discovered_at,
        status=EmergencyStatus.PENDING.value,
        **data,
    )
    _refresh_due(emergency)
    emergency.records.append(
        EmergencyRecord(
            action="登记事件",
            from_status="",
            to_status=EmergencyStatus.PENDING.value,
            operator=payload.reporter or "值班员",
            remark=payload.initial_remark or "发现突发情况，登记等待响应",
        )
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)
    restroom_service.touch(db, emergency.restroom_id)
    return emergency


def update_emergency(db: Session, emergency_id: int, payload: EmergencyUpdate) -> Emergency:
    emergency = get_emergency(db, emergency_id)
    emergency_data = payload.model_dump(exclude_unset=True)
    # 事件类型变更且未显式指定时限时，按新类型重新约定响应时限
    if "event_type" in emergency_data and "response_limit_minutes" not in emergency_data:
        new_type = emergency_data["event_type"]
        new_type_value = new_type.value if hasattr(new_type, "value") else new_type
        emergency_data["response_limit_minutes"] = _default_limit(new_type_value)
    for key, value in _values(emergency_data).items():
        setattr(emergency, key, value)
    if "discovered_at" in emergency_data or "response_limit_minutes" in emergency_data:
        _refresh_due(emergency)
    db.commit()
    db.refresh(emergency)
    return emergency


def allowed_transitions(emergency: Emergency) -> list[dict[str, str]]:
    return [
        {
            "status": target,
            "action": EMERGENCY_TRANSITION_ACTIONS.get((emergency.status, target), "状态变更"),
        }
        for target in EMERGENCY_TRANSITIONS.get(emergency.status, [])
    ]


def change_status(db: Session, emergency_id: int, payload: EmergencyStatusUpdate) -> Emergency:
    emergency = get_emergency(db, emergency_id)
    target = payload.to_status.value
    if target == emergency.status:
        raise DomainError(f"事件已处于「{target}」状态")
    allowed = EMERGENCY_TRANSITIONS.get(emergency.status, [])
    if target not in allowed:
        raise DomainError(
            f"当前状态「{emergency.status}」不允许流转到「{target}」，可选："
            + ("、".join(allowed) if allowed else "无（流程已结束）")
        )
    if target == EmergencyStatus.RECOVERED.value and not (payload.recovery_note or "").strip():
        raise DomainError("流转到「已恢复」时需补充恢复情况")

    now = datetime.now()
    from_status = emergency.status
    emergency.status = target
    if target == EmergencyStatus.PROCESSING.value:
        emergency.responded_at = now
        if payload.operator and not emergency.handler:
            emergency.handler = payload.operator
    elif target == EmergencyStatus.RECOVERED.value:
        emergency.recovered_at = now
        emergency.recovery_note = (payload.recovery_note or "").strip()
        if payload.impact_note is not None:
            emergency.impact_note = payload.impact_note.strip() or None
    emergency.closed_at = now if target == EmergencyStatus.CLOSED.value else None
    emergency.records.append(
        EmergencyRecord(
            action=EMERGENCY_TRANSITION_ACTIONS.get((from_status, target), "状态变更"),
            from_status=from_status,
            to_status=target,
            operator=payload.operator,
            remark=payload.remark,
        )
    )
    db.commit()
    db.refresh(emergency)
    restroom_service.touch(db, emergency.restroom_id)
    return emergency


def add_record(
    db: Session, emergency_id: int, *, action: str, operator: str, remark: str | None
) -> Emergency:
    """在不改变状态的前提下追加跟进记录（如处置进展说明）。"""
    emergency = get_emergency(db, emergency_id)
    if emergency.status == EmergencyStatus.CLOSED.value:
        raise DomainError("事件已关闭，无法追加处置记录")
    emergency.records.append(
        EmergencyRecord(
            action=action or "处置进展",
            from_status=emergency.status,
            to_status=emergency.status,
            operator=operator,
            remark=remark,
        )
    )
    db.commit()
    db.refresh(emergency)
    return emergency


def delete_emergency(db: Session, emergency_id: int) -> None:
    emergency = get_emergency(db, emergency_id)
    db.delete(emergency)
    db.commit()
