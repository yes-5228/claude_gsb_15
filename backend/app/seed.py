"""演示数据生成：首次启动时写入，便于快速体验各模块。"""

import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    EmergencyStatus,
    EmergencyType,
    INSPECTION_CHECK_ITEMS,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    RestroomGrade,
    RestroomStatus,
    Shift,
)
from app.models import Restroom
from app.schemas.emergency import (
    EmergencyCreate,
    EmergencyHandle,
    EmergencyRecover,
    EmergencyStatusUpdate,
)
from app.schemas.inspection import InspectionCreate, InspectionItem
from app.schemas.issue import IssueCreate, IssueStatusUpdate
from app.schemas.restroom import RestroomCreate
from app.services import emergency_service, inspection_service, issue_service, restroom_service

RANDOM_SEED = 20240913

RESTROOM_SPECS = [
    ("人民广场公共厕所", "城东区", "人民广场东侧 50 米", RestroomGrade.FIRST, RestroomStatus.NORMAL, "王秀兰", 12, 6, True),
    ("滨江公园公共厕所", "城东区", "滨江公园 3 号入口", RestroomGrade.SECOND, RestroomStatus.NORMAL, "李国强", 8, 4, True),
    ("和平路公共厕所", "城东区", "和平路与解放街交叉口", RestroomGrade.THIRD, RestroomStatus.MAINTENANCE, "赵敏", 4, 2, False),
    ("火车站南广场公共厕所", "城西区", "火车站南广场西侧", RestroomGrade.FIRST, RestroomStatus.NORMAL, "陈志远", 16, 8, True),
    ("西城集贸市场公共厕所", "城西区", "西城集贸市场北门", RestroomGrade.SECOND, RestroomStatus.NORMAL, "刘桂芳", 10, 4, False),
    ("文化路步行街公共厕所", "城西区", "文化路步行街中段", RestroomGrade.SECOND, RestroomStatus.NORMAL, "孙鹏", 9, 5, True),
    ("滨江新区体育中心公共厕所", "滨江新区", "体育中心东看台下", RestroomGrade.FIRST, RestroomStatus.NORMAL, "周晓燕", 14, 7, True),
    ("滨江新区政务中心公共厕所", "滨江新区", "政务服务中心一楼", RestroomGrade.SECOND, RestroomStatus.NORMAL, "吴建华", 8, 4, True),
    ("老城隍庙公共厕所", "老城区", "城隍庙街 12 号", RestroomGrade.THIRD, RestroomStatus.NORMAL, "郑淑珍", 5, 2, False),
    ("老城区第三小学旁公共厕所", "老城区", "第三小学东侧巷道", RestroomGrade.THIRD, RestroomStatus.CLOSED, "何伟", 4, 2, False),
]

INSPECTORS = ["张伟", "刘洋", "胡明月", "邓晨曦", "马晓峰", "杨柳"]
MANAGERS = ["王秀兰", "李国强", "陈志远", "刘桂芳", "周晓燕", "吴建华", "郑淑珍", "孙鹏"]

ISSUE_TEMPLATES = {
    IssueCategory.CLEANING: [
        "地面存在明显污渍未及时清理",
        "蹲位清洁不彻底，存在残留",
        "垃圾篓内垃圾未及时清运",
    ],
    IssueCategory.FACILITY: [
        "水龙头漏水，需更换阀芯",
        "感应冲水器失灵，无法自动冲水",
        "隔间门锁损坏无法反锁",
    ],
    IssueCategory.ODOR: [
        "公厕内异味明显，通风效果差",
        "排风扇停转导致异味积聚",
    ],
    IssueCategory.CONSUMABLE: [
        "洗手液未及时补充",
        "纸巾盒空置，未补充厕纸",
    ],
    IssueCategory.SAFETY: [
        "地面湿滑未放置防滑警示牌",
        "照明灯具损坏，夜间存在安全隐患",
    ],
    IssueCategory.OTHER: [
        "无障碍扶手松动需加固",
        "标识牌褪色需更换",
    ],
}

CATEGORY_BY_ITEM = {
    "地面与台阶清洁": IssueCategory.CLEANING,
    "便池蹲位清洁": IssueCategory.CLEANING,
    "洗手台与镜面": IssueCategory.CLEANING,
    "通风除臭": IssueCategory.ODOR,
    "耗材补充": IssueCategory.CONSUMABLE,
    "垃圾清运": IssueCategory.CLEANING,
    "工具与标识摆放": IssueCategory.OTHER,
    "墙面门窗卫生": IssueCategory.CLEANING,
}


def _build_items(rng: random.Random, quality: float) -> list[InspectionItem]:
    items: list[InspectionItem] = []
    for name in INSPECTION_CHECK_ITEMS:
        score = quality + rng.uniform(-1.6, 1.4)
        items.append(InspectionItem(name=name, score=max(0, min(10, round(score)))))
    return items


def _pick_problem(items: list[InspectionItem]) -> str | None:
    """找出最需要整改的检查项：优先取不合格项，否则取得分最低的一项。"""
    if not items:
        return None
    problems = [item for item in items if item.score < 6]
    pool = problems or items
    return min(pool, key=lambda item: item.score).name


def seed_database(db: Session, *, reset: bool = False) -> int:
    """写入演示数据，返回新增的问题条数；已有数据时默认跳过。"""
    existing = db.scalar(select(func.count()).select_from(Restroom)) or 0
    if existing and not reset:
        return 0

    rng = random.Random(RANDOM_SEED)
    now = datetime.now()

    restrooms = [
        restroom_service.create_restroom(
            db,
            RestroomCreate(
                name=name,
                district=district,
                address=address,
                grade=grade,
                status=status,
                manager=manager,
                manager_phone=f"13{rng.randint(100000000, 999999999)}",
                stall_count=stalls,
                basin_count=basins,
                has_accessible=accessible,
                open_hours="06:00-22:30" if grade == RestroomGrade.FIRST else "06:30-21:30",
            ),
        )
        for name, district, address, grade, status, manager, stalls, basins, accessible in RESTROOM_SPECS
    ]

    quality_by_restroom = {room.id: rng.uniform(7.4, 9.8) for room in restrooms}
    inspection_ids: list[tuple[int, int]] = []  # (restroom_id, inspection_id)

    for offset in range(13, -1, -1):
        day = now - timedelta(days=offset)
        for room in restrooms:
            if room.status == RestroomStatus.CLOSED:
                continue
            if rng.random() < 0.3:
                continue
            quality = quality_by_restroom[room.id] + rng.uniform(-1.0, 0.6)
            if rng.random() < 0.18:
                quality -= 2.6
            items = _build_items(rng, quality)
            inspection = inspection_service.create_inspection(
                db,
                InspectionCreate(
                    restroom_id=room.id,
                    inspector=rng.choice(INSPECTORS),
                    shift=rng.choice(list(Shift)),
                    inspect_time=day.replace(
                        hour=rng.choice([8, 10, 14, 16, 19]), minute=rng.choice([5, 20, 35, 50])
                    ),
                    items=items,
                    remark=None,
                ),
            )
            inspection_ids.append((room.id, inspection.id))

    created = 0
    for restroom_id, inspection_id in inspection_ids:
        summary = inspection_service.get_inspection(db, inspection_id)
        if summary.result != "发现问题" or rng.random() > 0.75:
            continue
        problem_item = _pick_problem([InspectionItem(**item) for item in summary.items])
        category = CATEGORY_BY_ITEM.get(problem_item or "", IssueCategory.OTHER)
        title = rng.choice(ISSUE_TEMPLATES[category])
        severity = (
            IssueSeverity.URGENT
            if category in (IssueCategory.SAFETY, IssueCategory.FACILITY) and rng.random() < 0.3
            else rng.choice([IssueSeverity.NORMAL, IssueSeverity.SERIOUS])
        )
        age_days = (now - summary.inspect_time).days
        deadline = summary.inspect_time + timedelta(
            days=1 if severity == IssueSeverity.URGENT else 3
        )
        issue = issue_service.create_issue(
            db,
            IssueCreate(
                restroom_id=restroom_id,
                inspection_id=inspection_id,
                title=title,
                description=f"巡查得分 {summary.score} 分（{summary.grade}），检查项「{problem_item}」不达标，请安排整改。",
                category=category,
                severity=severity,
                reporter=summary.inspector,
                assignee=rng.choice(MANAGERS),
                deadline=deadline,
                initial_remark="由保洁巡查自动生成的问题工单",
            ),
        )
        created += 1
        _advance_issue(db, issue.id, age_days, rng)

    _seed_emergencies(db, restrooms, now, rng)

    return created


def _advance_issue(db: Session, issue_id: int, age_days: int, rng: random.Random) -> None:
    """按问题存在时长模拟整改进度，让看板呈现多种状态。"""
    steps: list[tuple[str, str, str]] = []
    if age_days >= 1:
        steps.append(
            (
                IssueStatus.PROCESSING.value,
                "街办保洁队",
                "已派单至保洁班组，安排当日整改",
            )
        )
    if age_days >= 3:
        steps.append(
            (
                IssueStatus.REVIEWING.value,
                "整改责任人",
                "整改完成，提交巡查员验收",
            )
        )
    if age_days >= 5 and rng.random() < 0.75:
        steps.append((IssueStatus.DONE.value, "巡查员", "现场复核通过，问题已闭环"))
    if age_days >= 8 and rng.random() < 0.6:
        steps.append((IssueStatus.CLOSED.value, "值班长", "归档关闭"))

    for target, operator, remark in steps:
        try:
            issue_service.change_status(
                db,
                issue_id,
                IssueStatusUpdate(to_status=IssueStatus(target), operator=operator, remark=remark),
            )
        except Exception:  # noqa: BLE001  演示数据允许跳过不合法的流转
            break


# (公厕序号, 类型, 发现距今天, 响应耗时分钟, 处置总时长小时, 阶段)
# 阶段：pending 待处置 / processing 处置中 / recovered 已恢复 / closed 已关闭
EMERGENCY_SPECS: list[tuple[int, EmergencyType, int, int, int, str]] = [
    (3, EmergencyType.FACILITY_BURST, 0, 0, 0, "pending"),       # 刚发现，尚未到场
    (1, EmergencyType.POWER_CUT, 0, 1, 1, "processing"),        # 已到场，抢修中
    (4, EmergencyType.SEWAGE_OVERFLOW, 1, 12, 2, "recovered"),  # 响应及时
    (8, EmergencyType.WATER_CUT, 1, 20, 5, "recovered"),        # 响应及时
    (0, EmergencyType.FACILITY_BURST, 2, 45, 4, "recovered"),   # 响应超时
    (5, EmergencyType.POWER_CUT, 3, 50, 3, "closed"),           # 响应超时
    (2, EmergencyType.SEWAGE_OVERFLOW, 5, 10, 3, "closed"),
    (6, EmergencyType.WATER_CUT, 7, 25, 8, "closed"),
    (7, EmergencyType.OTHER, 9, 18, 2, "closed"),
    (9, EmergencyType.SEWAGE_OVERFLOW, 12, 8, 1, "closed"),
]

EMERGENCY_TEMPLATES = {
    EmergencyType.WATER_CUT: (
        "市政供水管网检修导致公厕停水",
        "男、女卫生间全部供水中断，无法冲厕与洗手，影响如厕市民约 200 人次",
        "立即启用储备水箱保障基本冲厕，张贴停水告示，安排应急送水，联系自来水公司确认恢复时间",
        "供水恢复正常，水箱补水完毕，各洁具冲洗正常",
        "停水 5 小时，期间启用应急供水，无市民投诉",
    ),
    EmergencyType.POWER_CUT: (
        "配电线路故障导致公厕停电",
        "照明、排风扇、感应洁具全部断电，夜间存在安全隐患",
        "拉设临时照明并放置警示牌，电工排查线路，更换故障空气开关",
        "线路修复，照明、通风与感应洁具供电恢复正常",
        "停电约 1 小时，未造成人员伤亡",
    ),
    EmergencyType.FACILITY_BURST: (
        "进水管道爆裂大量跑水",
        "洗手台进水管爆裂，地面积水漫延至门口，影响相邻步道",
        "关闭进水总阀，疏散如厕市民，清理积水，更换爆裂管件后恢复供水",
        "管件更换完成，供水恢复，地面无积水",
        "地面积水约 15 平方米，已拖干并放置防滑垫，无滑倒事件",
    ),
    EmergencyType.SEWAGE_OVERFLOW: (
        "排污井堵塞污水外溢",
        "污物污水从地漏外溢至男卫生间地面，异味明显，影响约 30 平方米区域",
        "设置围挡暂停使用该区域，疏通班组高压冲洗排污管道，全面消杀除味",
        "管道疏通完毕，污水退净，消杀除味完成，卫生间恢复开放",
        "外溢持续约 2 小时，临时封闭 2 个蹲位，已完成 2 次消杀",
    ),
    EmergencyType.OTHER: (
        "大风导致屋面排水槽脱落",
        "排水槽一端脱落悬于门口上方，存在坠物风险，影响人员进出",
        "现场设置警戒线，维修班组拆除松动构件并重新固定",
        "排水槽修复牢固，门口警戒解除，通行恢复正常",
        "封闭入口约 40 分钟，无人员受伤",
    ),
}


def _seed_emergencies(db: Session, restrooms: list, now: datetime, rng: random.Random) -> None:
    """按固定模板生成不同类型与处置阶段的应急事件。"""
    responders = ["抢修班李建国", "水电工马晓峰", "保洁班王秀兰", "维保组陈志远", "值班长周明"]
    discoverers = ["张伟", "刘洋", "胡明月", "邓晨曦", "马晓峰"]

    for room_index, event_type, day_ago, response_minutes, duration_hours, stage in EMERGENCY_SPECS:
        room = restrooms[room_index]
        title, scope, measure, recover_note, impact = EMERGENCY_TEMPLATES[event_type]
        discover_time = now - timedelta(
            days=day_ago, hours=rng.randint(0, 6), minutes=rng.randint(0, 50)
        )
        if stage == "pending":
            # 控制在刚刚发现、尚未超时的时间点
            discover_time = now - timedelta(minutes=rng.randint(3, 10))

        event = emergency_service.create_event(
            db,
            EmergencyCreate(
                restroom_id=room.id,
                event_type=event_type,
                title=title,
                description=f"巡检发现：{scope}。",
                impact_scope=scope,
                discoverer=rng.choice(discoverers),
                discover_time=discover_time,
                initial_remark="应急情况登记，已通知抢修力量",
            ),
        )

        if stage == "pending":
            continue

        responder = rng.choice(responders)
        response_time = discover_time + timedelta(minutes=response_minutes)
        emergency_service.handle_event(
            db,
            event.id,
            EmergencyHandle(
                responder=responder,
                measure=measure,
                response_time=response_time,
                remark="已到场并采取先期处置措施",
            ),
        )

        if stage == "processing":
            continue

        recover_time = response_time + timedelta(hours=duration_hours)
        emergency_service.recover_event(
            db,
            event.id,
            EmergencyRecover(
                recover_note=recover_note,
                impact_detail=impact,
                recover_time=recover_time,
                remark="现场已恢复正常",
            ),
        )

        if stage == "recovered":
            continue

        close_time = recover_time + timedelta(hours=rng.randint(2, 20))
        emergency_service.change_status(
            db,
            event.id,
            EmergencyStatusUpdate(
                to_status=EmergencyStatus.CLOSED,
                operator="值班长周明",
                remark="确认恢复无异常，归档关闭",
            ),
        )
        event = emergency_service.get_event(db, event.id)
        event.close_time = close_time
        event.records[-1].created_at = close_time
        db.commit()
