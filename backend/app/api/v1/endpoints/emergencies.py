"""应急情况处置记录接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.constants import OPEN_EMERGENCY_STATUSES
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyEventOut,
    EmergencyHandle,
    EmergencyRecover,
    EmergencyStatusUpdate,
    EmergencyUpdate,
)
from app.services import emergency_service

router = APIRouter(prefix="/emergencies", tags=["应急处置"])


class RecordCreate(BaseModel):
    action: str = Field(default="处置跟进", max_length=30)
    operator: str = Field(min_length=1, max_length=60)
    remark: str | None = Field(default=None, max_length=500)


class TransitionOption(BaseModel):
    status: str
    action: str


@router.get("", response_model=Page[EmergencyEventOut], summary="应急事件列表")
def list_events(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    status: Annotated[str | None, Query(description="处置状态")] = None,
    open_only: Annotated[bool, Query(description="仅看处置中事件")] = False,
    event_type: Annotated[str | None, Query(description="事件类型")] = None,
    keyword: Annotated[str | None, Query(description="标题/描述/编号/处置人模糊搜索")] = None,
    overdue: Annotated[bool | None, Query(description="响应是否超过约定时限")] = None,
    recovered: Annotated[bool | None, Query(description="是否已恢复")] = None,
    date_from: Annotated[date | None, Query(description="发现开始日期")] = None,
    date_to: Annotated[date | None, Query(description="发现结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "discover_time",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[EmergencyEventOut]:
    statuses = list(OPEN_EMERGENCY_STATUSES) if open_only else None
    rows, total = emergency_service.list_events(
        db,
        restroom_id=restroom_id,
        district=district,
        status=status,
        statuses=statuses,
        event_type=event_type,
        keyword=keyword,
        overdue=overdue,
        recovered=recovered,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[EmergencyEventOut](
        items=[emergency_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=EmergencyEventOut, status_code=201, summary="登记应急事件")
def create_event(payload: EmergencyCreate, db: Annotated[Session, Depends(get_db)]) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.create_event(db, payload))


@router.get("/{event_id}", response_model=EmergencyEventOut, summary="事件详情与处置轨迹")
def get_event(event_id: int, db: Annotated[Session, Depends(get_db)]) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.get_event(db, event_id))


@router.patch("/{event_id}", response_model=EmergencyEventOut, summary="补正登记信息")
def update_event(
    event_id: int, payload: EmergencyUpdate, db: Annotated[Session, Depends(get_db)]
) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.update_event(db, event_id, payload))


@router.post("/{event_id}/handle", response_model=EmergencyEventOut, summary="开始处置（登记处置措施）")
def handle_event(
    event_id: int, payload: EmergencyHandle, db: Annotated[Session, Depends(get_db)]
) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.handle_event(db, event_id, payload))


@router.post("/{event_id}/recover", response_model=EmergencyEventOut, summary="恢复确认（补充恢复情况与影响）")
def recover_event(
    event_id: int, payload: EmergencyRecover, db: Annotated[Session, Depends(get_db)]
) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.recover_event(db, event_id, payload))


@router.post("/{event_id}/transitions", response_model=EmergencyEventOut, summary="推进处置状态（关闭）")
def change_status(
    event_id: int, payload: EmergencyStatusUpdate, db: Annotated[Session, Depends(get_db)]
) -> EmergencyEventOut:
    return emergency_service.to_out(emergency_service.change_status(db, event_id, payload))


@router.get(
    "/{event_id}/transitions",
    response_model=list[TransitionOption],
    summary="可执行的处置动作",
)
def list_transitions(
    event_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[TransitionOption]:
    event = emergency_service.get_event(db, event_id)
    return [
        TransitionOption(**option) for option in emergency_service.allowed_transitions(event)
    ]


@router.post("/{event_id}/records", response_model=EmergencyEventOut, summary="追加处置记录")
def add_record(
    event_id: int, payload: RecordCreate, db: Annotated[Session, Depends(get_db)]
) -> EmergencyEventOut:
    event = emergency_service.add_record(
        db,
        event_id,
        action=payload.action,
        operator=payload.operator,
        remark=payload.remark,
    )
    return emergency_service.to_out(event)


@router.delete("/{event_id}", response_model=MessageOut, summary="删除应急事件")
def delete_event(event_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    emergency_service.delete_event(db, event_id)
    return MessageOut(message="删除成功")
