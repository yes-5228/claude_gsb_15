"""应急情况处置记录业务逻辑。"""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    EMERGENCY_RESPONSE_LIMITS_MINUTES,
    EMERGENCY_TRANSITIONS,
    EMERGENCY_TRANSITION_ACTIONS,
    EmergencyStatus,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import EmergencyEvent, EmergencyRecord, Restroom
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyEventOut,
    EmergencyHandle,
    EmergencyRecover,
    EmergencyStatusUpdate,
    EmergencyUpdate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "discover_time": EmergencyEvent.discover_time,
    "response_time": EmergencyEvent.response_time,
    "recover_time": EmergencyEvent.recover_time,
    "event_type": EmergencyEvent.event_type,
    "status": EmergencyEvent.status,
    "code": EmergencyEvent.code,
    "updated_at": EmergencyEvent.updated_at,
}


def _next_code(db: Session) -> str:
    prefix = datetime.now().strftime("YJ-%Y%m%d")
    seq = (
        db.scalar(
            select(func.count())
            .select_from(EmergencyEvent)
            .where(EmergencyEvent.code.like(f"{prefix}-%"))
        )
        or 0
    ) + 1
    while True:
        code = f"{prefix}-{seq:03d}"
        if not db.scalar(select(EmergencyEvent.id).where(EmergencyEvent.code == code)):
            return code
        seq += 1


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def get_event(db: Session, event_id: int) -> EmergencyEvent:
    event = db.get(EmergencyEvent, event_id)
    if event is None:
        raise NotFoundError(f"应急事件 {event_id} 不存在")
    return event


def to_out(event: EmergencyEvent) -> EmergencyEventOut:
    return EmergencyEventOut.model_validate(event)


def response_overdue(event: EmergencyEvent, *, now: datetime | None = None) -> bool:
    """与 EmergencyEventOut 中保持一致的超时判定，供列表筛选使用。"""
    limit = EMERGENCY_RESPONSE_LIMITS_MINUTES.get(event.event_type, 30)
    if event.response_time is not None:
        return (event.response_time - event.discover_time).total_seconds() / 60 > limit
    if event.status != EmergencyStatus.PENDING.value:
        return False
    now = now or datetime.now()
    return (now - event.discover_time).total_seconds() / 60 > limit


def list_events(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    status: str | None = None,
    statuses: list[str] | None = None,
    event_type: str | None = None,
    keyword: str | None = None,
    overdue: bool | None = None,
    recovered: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "discover_time",
    order: str = "desc",
) -> tuple[list[EmergencyEvent], int]:
    stmt = select(EmergencyEvent)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == EmergencyEvent.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(EmergencyEvent.restroom_id == restroom_id)
    if status:
        stmt = stmt.where(EmergencyEvent.status == status)
    if statuses:
        stmt = stmt.where(EmergencyEvent.status.in_(statuses))
    if event_type:
        stmt = stmt.where(EmergencyEvent.event_type == event_type)
    if recovered is True:
        stmt = stmt.where(EmergencyEvent.recover_time.is_not(None))
    elif recovered is False:
        stmt = stmt.where(EmergencyEvent.recover_time.is_(None))
    if date_from:
        stmt = stmt.where(EmergencyEvent.discover_time >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(EmergencyEvent.discover_time <= datetime.combine(date_to, time.max))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                EmergencyEvent.title.like(like),
                EmergencyEvent.description.like(like),
                EmergencyEvent.code.like(like),
                EmergencyEvent.responder.like(like),
                EmergencyEvent.discoverer.like(like),
            )
        )

    rows = list(db.scalars(stmt.order_by(EmergencyEvent.id.desc())))
    if overdue is not None:
        rows = [row for row in rows if response_overdue(row) is overdue]

    reverse = order == "desc"
    if sort_by in SORTABLE_FIELDS:
        # 可能为空的时间字段（响应/恢复时间）无论升降序都排到最后
        valued = [row for row in rows if getattr(row, sort_by) is not None]
        empty = [row for row in rows if getattr(row, sort_by) is None]
        valued.sort(key=lambda row: (getattr(row, sort_by), row.id), reverse=reverse)
        ordered = valued + empty
    else:
        ordered = sorted(rows, key=lambda row: (row.discover_time, row.id), reverse=True)
    total = len(ordered)
    start = (page - 1) * page_size
    return ordered[start : start + page_size], total


def create_event(db: Session, payload: EmergencyCreate) -> EmergencyEvent:
    restroom_service.get_restroom(db, payload.restroom_id)
    data = _values(payload.model_dump(exclude={"discover_time", "initial_remark"}))
    discover_time = payload.discover_time or datetime.now()
    event = EmergencyEvent(
        code=_next_code(db),
        discover_time=discover_time,
        status=EmergencyStatus.PENDING.value,
        **data,
    )
    event.records.append(
        EmergencyRecord(
            action="发现登记",
            from_status="",
            to_status=EmergencyStatus.PENDING.value,
            operator=payload.discoverer or "值班人员",
            remark=payload.initial_remark or "应急情况已登记，等待到场处置",
            created_at=discover_time,
        )
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    restroom_service.touch(db, event.restroom_id)
    return event


def update_event(db: Session, event_id: int, payload: EmergencyUpdate) -> EmergencyEvent:
    event = get_event(db, event_id)
    if event.status != EmergencyStatus.PENDING.value:
        raise DomainError("事件已开始处置，登记信息不可修改")
    data = payload.model_dump(exclude_unset=True)
    if "images" in data and payload.images is not None:
        data["images"] = list(payload.images)
    for key, value in _values(data).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


def allowed_transitions(event: EmergencyEvent) -> list[dict[str, str]]:
    return [
        {
            "status": target,
            "action": EMERGENCY_TRANSITION_ACTIONS.get((event.status, target), "状态变更"),
        }
        for target in EMERGENCY_TRANSITIONS.get(event.status, [])
    ]


def _change_status(
    event: EmergencyEvent,
    target: str,
    operator: str,
    remark: str | None,
    *,
    now: datetime | None = None,
) -> EmergencyRecord:
    if target == event.status:
        raise DomainError(f"事件已处于「{target}」状态")
    allowed = EMERGENCY_TRANSITIONS.get(event.status, [])
    if target not in allowed:
        raise DomainError(
            f"当前状态「{event.status}」不允许流转到「{target}」，可选："
            + ("、".join(allowed) if allowed else "无（流程已结束）")
        )

    now = now or datetime.now()
    from_status = event.status
    event.status = target
    if target == EmergencyStatus.CLOSED.value:
        event.close_time = now
    record = EmergencyRecord(
        action=EMERGENCY_TRANSITION_ACTIONS.get((from_status, target), "状态变更"),
        from_status=from_status,
        to_status=target,
        operator=operator,
        remark=remark,
        created_at=now,
    )
    event.records.append(record)
    return record


def handle_event(db: Session, event_id: int, payload: EmergencyHandle) -> EmergencyEvent:
    """登记处置措施：待处置 -> 处置中，并记录响应时间用于计算响应耗时。"""
    event = get_event(db, event_id)
    response_time = payload.response_time or datetime.now()
    if response_time < event.discover_time:
        raise DomainError("开始处置时间不能早于发现时间")

    _change_status(
        event,
        EmergencyStatus.PROCESSING.value,
        payload.responder,
        payload.remark or payload.measure,
        now=response_time,
    )
    event.response_time = response_time
    event.responder = payload.responder
    event.measure = payload.measure
    db.commit()
    db.refresh(event)
    restroom_service.touch(db, event.restroom_id)
    return event


def recover_event(db: Session, event_id: int, payload: EmergencyRecover) -> EmergencyEvent:
    """处置完成：处置中 -> 已恢复，补充恢复情况与造成的影响。"""
    event = get_event(db, event_id)
    recover_time = payload.recover_time or datetime.now()
    if event.response_time is not None and recover_time < event.response_time:
        raise DomainError("恢复时间不能早于开始处置时间")

    _change_status(
        event,
        EmergencyStatus.RECOVERED.value,
        event.responder or "值班人员",
        payload.remark or payload.recover_note,
        now=recover_time,
    )
    event.recover_time = recover_time
    event.recover_note = payload.recover_note
    event.impact_detail = payload.impact_detail
    db.commit()
    db.refresh(event)
    restroom_service.touch(db, event.restroom_id)
    return event


def change_status(
    db: Session, event_id: int, payload: EmergencyStatusUpdate
) -> EmergencyEvent:
    event = get_event(db, event_id)
    _change_status(event, payload.to_status.value, payload.operator, payload.remark)
    db.commit()
    db.refresh(event)
    restroom_service.touch(db, event.restroom_id)
    return event


def add_record(
    db: Session, event_id: int, *, action: str, operator: str, remark: str | None
) -> EmergencyEvent:
    """在不改变状态的前提下追加跟进记录（如抢修进度、物资协调）。"""
    event = get_event(db, event_id)
    if event.status == EmergencyStatus.CLOSED.value:
        raise DomainError("事件已关闭，无法追加处置记录")
    event.records.append(
        EmergencyRecord(
            action=action or "处置跟进",
            from_status=event.status,
            to_status=event.status,
            operator=operator,
            remark=remark,
        )
    )
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> None:
    event = get_event(db, event_id)
    db.delete(event)
    db.commit()
