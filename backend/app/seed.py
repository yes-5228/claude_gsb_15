"""演示数据生成：首次启动时写入，便于快速体验各模块。"""

import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    INSPECTION_CHECK_ITEMS,
    EmergencyStatus,
    EmergencyType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    RestroomGrade,
    RestroomStatus,
    Shift,
)
from app.models import Restroom
from app.schemas.emergency import EmergencyCreate, EmergencyStatusUpdate
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

# 应急事件模板：事件类型、标题、影响范围、处置措施
EMERGENCY_TEMPLATES = [
    (
        EmergencyType.WATER_POWER_OUTAGE,
        "突发停水，冲洗系统无法使用",
        "全厕停水，蹲位冲洗与洗手台均不可用",
        "联系供水部门排查停水原因，启用临时储水应急冲洗，张贴温馨提示",
    ),
    (
        EmergencyType.FACILITY_BURST,
        "主供水管爆裂喷水",
        "男厕区域积水并漫至走道，如厕通行受阻",
        "关闭供水总阀，设置围挡与警示牌，抢修更换爆裂管段后恢复供水",
    ),
    (
        EmergencyType.CONTAMINATION_OVERFLOW,
        "化粪池满溢污水外溢",
        "厕外检查井周边约 5 平方米污损外溢，异味明显",
        "联系吸污车紧急清掏，外溢区域冲洗消毒并撒布除臭剂",
    ),
    (
        EmergencyType.WATER_POWER_OUTAGE,
        "夜间照明线路断电",
        "厕内照明全部熄灭，夜间如厕存在安全隐患",
        "检查配电箱并联系供电抢修，处置期间放置应急照明灯",
    ),
    (
        EmergencyType.FACILITY_BURST,
        "蹲位冲水阀爆裂喷溅",
        "单个蹲位喷溅无法使用，周边地面积水",
        "关闭该蹲位角阀并暂停使用，更换冲水阀，清理地面积水",
    ),
    (
        EmergencyType.CONTAMINATION_OVERFLOW,
        "排污管堵塞污水返溢",
        "女厕地面污水返溢约 10 平方米",
        "疏通排污管道，地面清洗消毒，处置期间放置警示牌并引导至临厕",
    ),
]


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

    _seed_emergencies(db, restrooms, rng, now)

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


def _seed_emergencies(db: Session, restrooms: list, rng: random.Random, now: datetime) -> None:
    """写入应急事件演示数据：覆盖各事件类型与不同处置阶段。"""
    candidates = [room for room in restrooms if room.status != RestroomStatus.CLOSED.value]
    for index, (event_type, title, scope, measures) in enumerate(EMERGENCY_TEMPLATES):
        room = candidates[index % len(candidates)]
        discovered = now - timedelta(
            days=index, hours=rng.randint(1, 9), minutes=rng.randint(0, 59)
        )
        emergency = emergency_service.create_emergency(
            db,
            EmergencyCreate(
                restroom_id=room.id,
                title=title,
                event_type=event_type,
                discovered_at=discovered,
                impact_scope=scope,
                measures=measures,
                reporter=rng.choice(INSPECTORS),
                handler=rng.choice(MANAGERS),
                initial_remark="巡查中发现突发情况，立即登记并上报",
            ),
        )
        # 第一条保持待响应且已逾响应时限，用于演示超时预警
        if index > 0:
            _advance_emergency(db, emergency.id, discovered, rng)


def _advance_emergency(db: Session, emergency_id: int, discovered: datetime, rng: random.Random) -> None:
    """按处置流程推进演示事件，并回写与时间线一致的响应/恢复时间。"""
    roll = rng.random()
    if roll < 0.25:
        return  # 保持待响应
    emergency_service.change_status(
        db,
        emergency_id,
        EmergencyStatusUpdate(
            to_status=EmergencyStatus.PROCESSING, operator="维修班组", remark="已到场开始处置"
        ),
    )
    emergency = emergency_service.get_emergency(db, emergency_id)
    emergency.responded_at = discovered + timedelta(
        minutes=rng.randint(10, emergency.response_limit_minutes + 30)
    )
    db.commit()
    if roll < 0.55:
        return  # 处置中
    emergency_service.change_status(
        db,
        emergency_id,
        EmergencyStatusUpdate(
            to_status=EmergencyStatus.RECOVERED,
            operator="维修班组",
            remark="现场处置完毕，设施恢复运行",
            recovery_note="设施已恢复正常，现场清理消毒完毕",
            impact_note="部分区域暂停使用约 2 小时，未收到群众投诉",
        ),
    )
    emergency = emergency_service.get_emergency(db, emergency_id)
    emergency.recovered_at = emergency.responded_at + timedelta(minutes=rng.randint(30, 240))
    db.commit()
    if roll < 0.8:
        return  # 已恢复待归档
    emergency_service.change_status(
        db,
        emergency_id,
        EmergencyStatusUpdate(to_status=EmergencyStatus.CLOSED, operator="值班长", remark="归档关闭"),
    )
