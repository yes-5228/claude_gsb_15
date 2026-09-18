"""业务枚举与规则常量。"""

from enum import StrEnum


class RestroomStatus(StrEnum):
    NORMAL = "正常开放"
    MAINTENANCE = "维修中"
    CLOSED = "暂停使用"


class RestroomGrade(StrEnum):
    FIRST = "一类"
    SECOND = "二类"
    THIRD = "三类"


class Shift(StrEnum):
    MORNING = "早班"
    MIDDLE = "中班"
    NIGHT = "晚班"


class InspectionResult(StrEnum):
    NORMAL = "正常"
    ABNORMAL = "发现问题"


class IssueCategory(StrEnum):
    CLEANING = "保洁不到位"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    OTHER = "其他"


class IssueSeverity(StrEnum):
    NORMAL = "一般"
    SERIOUS = "严重"
    URGENT = "紧急"


class IssueStatus(StrEnum):
    PENDING = "待整改"
    PROCESSING = "整改中"
    REVIEWING = "待验收"
    DONE = "已完成"
    CLOSED = "已关闭"


# 整改流转规则：当前状态 -> 允许流转到的状态
ISSUE_TRANSITIONS: dict[str, list[str]] = {
    IssueStatus.PENDING: [IssueStatus.PROCESSING, IssueStatus.CLOSED],
    IssueStatus.PROCESSING: [IssueStatus.REVIEWING, IssueStatus.CLOSED],
    IssueStatus.REVIEWING: [IssueStatus.DONE, IssueStatus.PROCESSING],
    IssueStatus.DONE: [IssueStatus.CLOSED],
    IssueStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成整改流水
TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (IssueStatus.PENDING, IssueStatus.PROCESSING): "开始整改",
    (IssueStatus.PENDING, IssueStatus.CLOSED): "作废关闭",
    (IssueStatus.PROCESSING, IssueStatus.REVIEWING): "提交验收",
    (IssueStatus.PROCESSING, IssueStatus.CLOSED): "终止关闭",
    (IssueStatus.REVIEWING, IssueStatus.DONE): "验收通过",
    (IssueStatus.REVIEWING, IssueStatus.PROCESSING): "验收驳回",
    (IssueStatus.DONE, IssueStatus.CLOSED): "归档关闭",
}

class EmergencyType(StrEnum):
    WATER_CUT = "停水"
    POWER_CUT = "停电"
    FACILITY_BURST = "设施爆裂"
    SEWAGE_OVERFLOW = "污损外溢"
    OTHER = "其他"


class EmergencyStatus(StrEnum):
    PENDING = "待处置"
    PROCESSING = "处置中"
    RECOVERED = "已恢复"
    CLOSED = "已关闭"


# 各类应急事件的响应时限（分钟）：从发现到开始处置必须在此时限内到场
EMERGENCY_RESPONSE_LIMITS_MINUTES: dict[str, int] = {
    EmergencyType.WATER_CUT: 30,
    EmergencyType.POWER_CUT: 30,
    EmergencyType.FACILITY_BURST: 15,
    EmergencyType.SEWAGE_OVERFLOW: 15,
    EmergencyType.OTHER: 30,
}

# 仍处于应急处置中的状态，用于超时判定与统计
OPEN_EMERGENCY_STATUSES: list[str] = [
    EmergencyStatus.PENDING,
    EmergencyStatus.PROCESSING,
]

# 应急处置流转规则：当前状态 -> 允许流转到的状态
EMERGENCY_TRANSITIONS: dict[str, list[str]] = {
    EmergencyStatus.PENDING: [EmergencyStatus.PROCESSING, EmergencyStatus.CLOSED],
    EmergencyStatus.PROCESSING: [EmergencyStatus.RECOVERED, EmergencyStatus.CLOSED],
    EmergencyStatus.RECOVERED: [EmergencyStatus.CLOSED],
    EmergencyStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成处置流水
EMERGENCY_TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (EmergencyStatus.PENDING, EmergencyStatus.PROCESSING): "开始处置",
    (EmergencyStatus.PENDING, EmergencyStatus.CLOSED): "作废关闭",
    (EmergencyStatus.PROCESSING, EmergencyStatus.RECOVERED): "恢复确认",
    (EmergencyStatus.PROCESSING, EmergencyStatus.CLOSED): "终止关闭",
    (EmergencyStatus.RECOVERED, EmergencyStatus.CLOSED): "归档关闭",
}


# 巡查检查项，每项 0-10 分
INSPECTION_CHECK_ITEMS: list[str] = [
    "地面与台阶清洁",
    "便池蹲位清洁",
    "洗手台与镜面",
    "通风除臭",
    "耗材补充",
    "垃圾清运",
    "工具与标识摆放",
    "墙面门窗卫生",
]

INSPECTION_ITEM_MAX_SCORE = 10

GRADE_EXCELLENT = "优秀"
GRADE_GOOD = "良好"
GRADE_PASS = "合格"
GRADE_FAIL = "不合格"

# 仍处于整改闭环中的状态，用于统计未整改问题
OPEN_ISSUE_STATUSES: list[str] = [
    IssueStatus.PENDING,
    IssueStatus.PROCESSING,
    IssueStatus.REVIEWING,
]

# 单检查项低于该分数视为不合格项
INSPECTION_ITEM_PROBLEM_THRESHOLD = 6
