"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]
    assert "停水停电" in payload["emergency_type"]
    assert "待响应" in payload["emergency_status"]
    assert payload["emergency_response_limits"]["设施爆裂"] == 20
    assert payload["emergency_transitions"]["待响应"] == ["处置中", "已关闭"]


def test_restroom_crud_and_delete_guard(client, restroom):
    assert restroom["code"].startswith("WC-")

    listed = client.get("/api/v1/restrooms", params={"district": "测试区"}).json()
    assert listed["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["inspection_count"] == 0
    assert detail["open_issue_count"] == 0

    updated = client.patch(
        f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中", "manager": "新责任人"}
    ).json()
    assert updated["status"] == "维修中"
    assert updated["manager"] == "新责任人"

    # 存在关联数据时不允许直接删除
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "测试巡查员",
            "shift": "早班",
            "items": full_items(9),
        },
    )
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").status_code == 404


def test_inspection_scoring_and_filter(client, restroom):
    good = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "中班",
            "items": full_items(9),
            "remark": "整体良好",
        },
    ).json()
    assert good["score"] == 90.0
    assert good["grade"] == "优秀"
    assert good["result"] == "正常"

    bad_items = full_items(9)
    bad_items[0]["score"] = 3
    bad_items[0]["remark"] = "地面污渍"
    bad = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "晚班",
            "items": bad_items,
        },
    ).json()
    assert bad["result"] == "发现问题"
    assert bad["score"] < 90

    filtered = client.get(
        "/api/v1/inspections", params={"result": "发现问题", "restroom_id": restroom["id"]}
    ).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == bad["id"]
    assert filtered["items"][0]["restroom"]["name"] == restroom["name"]

    today = datetime.now().date().isoformat()
    ranged = client.get(
        "/api/v1/inspections", params={"date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    duplicate = full_items(5) + [{"name": "地面与台阶清洁", "score": 4}]
    rejected = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": duplicate},
    )
    assert rejected.status_code == 400

    empty = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": []},
    )
    assert empty.status_code == 422


def test_issue_lifecycle(client, restroom):
    inspection = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "王巡查",
            "items": full_items(4),
        },
    ).json()

    issue = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "地面污渍未清理",
            "description": "巡查发现地面有明显污渍",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
            "assignee": "保洁班组",
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert issue["status"] == "待整改"
    assert len(issue["records"]) == 1
    assert issue["records"][0]["action"] == "上报问题"

    # 越级流转被拒绝：待整改 -> 已完成
    invalid = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "已完成", "operator": "值班长"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/issues/{issue['id']}/transitions").json()
    assert {option["status"] for option in options} == {"整改中", "已关闭"}

    processing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "保洁班组张伟", "remark": "已安排清洗"},
    ).json()
    assert processing["status"] == "整改中"
    assert processing["assignee"] == "保洁班组"

    reviewing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "待验收", "operator": "保洁班组张伟", "remark": "整改完成待验收"},
    ).json()
    assert reviewing["status"] == "待验收"

    # 验收驳回回到整改中
    rejected = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "王巡查", "remark": "角落仍有残留"},
    ).json()
    assert rejected["status"] == "整改中"
    assert rejected["records"][-1]["action"] == "验收驳回"

    for target in ("待验收", "已完成", "已关闭"):
        payload = {"to_status": target, "operator": "值班长", "remark": f"流转到{target}"}
        response = client.post(f"/api/v1/issues/{issue['id']}/transitions", json=payload)
        assert response.status_code == 200, response.text
    final = response.json()
    assert final["status"] == "已关闭"
    assert final["closed_at"] is not None
    assert [record["to_status"] for record in final["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/issues/{issue['id']}/records",
        json={"action": "整改进度", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    overdue = client.get("/api/v1/issues", params={"overdue": "true"}).json()
    assert overdue["meta"]["total"] == 0

    # 巡查记录可反查关联问题数量
    detail = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert detail["issue_count"] == 1


def test_issue_requires_matching_restroom(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "测试区", "address": "测试路 2 号"},
    ).json()
    inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": other["id"], "inspector": "周巡查", "items": full_items(9)},
    ).json()
    mismatch = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "关联错误",
        },
    )
    assert mismatch.status_code == 400
    assert "不一致" in mismatch.json()["detail"]


def test_dashboard_stats(client, restroom):
    payload = client.get("/api/v1/stats/dashboard", params={"trend_days": 7}).json()
    overview = payload["overview"]
    assert overview["restroom_total"] >= 1
    assert overview["inspection_total"] >= 1
    assert len(payload["inspection_trend"]) == 7
    assert {item["name"] for item in payload["issue_by_status"]} == {
        "待整改",
        "整改中",
        "待验收",
        "已完成",
        "已关闭",
    }
    assert payload["top_restrooms"]
    assert "rectification_rate" in overview
    assert "emergency_open" in overview
    assert {item["name"] for item in payload["emergency_by_type"]} == {
        "停水停电",
        "设施爆裂",
        "污损外溢",
        "其他",
    }


def test_emergency_lifecycle(client, restroom):
    discovered = datetime.now() - timedelta(minutes=45)
    emergency = client.post(
        "/api/v1/emergencies",
        json={
            "restroom_id": restroom["id"],
            "title": "主供水管爆裂喷水",
            "event_type": "设施爆裂",
            "discovered_at": discovered.isoformat(),
            "impact_scope": "男厕区域积水并漫至走道",
            "measures": "关闭总阀并设置围挡，安排抢修",
            "reporter": "王巡查",
            "handler": "维修班组",
        },
    )
    assert emergency.status_code == 201, emergency.text
    emergency = emergency.json()
    assert emergency["code"].startswith("YJ-")
    assert emergency["status"] == "待响应"
    # 未指定时限时按事件类型约定：设施爆裂 20 分钟
    assert emergency["response_limit_minutes"] == 20
    assert emergency["response_due_at"] is not None
    assert emergency["response_minutes"] is None
    assert emergency["response_overdue"] is True  # 发现于 45 分钟前，已超过 20 分钟时限
    assert emergency["records"][0]["action"] == "登记事件"

    # 越级流转被拒绝：待响应 -> 已恢复
    invalid = client.post(
        f"/api/v1/emergencies/{emergency['id']}/transitions",
        json={"to_status": "已恢复", "operator": "维修班组", "recovery_note": "已修复"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/emergencies/{emergency['id']}/transitions").json()
    assert {option["status"] for option in options} == {"处置中", "已关闭"}

    # 响应处置：记录响应时间并计算响应耗时
    processing = client.post(
        f"/api/v1/emergencies/{emergency['id']}/transitions",
        json={"to_status": "处置中", "operator": "维修班组老张", "remark": "已到场关阀止水"},
    ).json()
    assert processing["status"] == "处置中"
    assert processing["responded_at"] is not None
    assert processing["response_minutes"] >= 45
    assert processing["response_overdue"] is True  # 实际响应晚于约定时限

    # 恢复时必须补充恢复情况
    missing_note = client.post(
        f"/api/v1/emergencies/{emergency['id']}/transitions",
        json={"to_status": "已恢复", "operator": "维修班组老张"},
    )
    assert missing_note.status_code == 400
    assert "恢复情况" in missing_note.json()["detail"]

    recovered = client.post(
        f"/api/v1/emergencies/{emergency['id']}/transitions",
        json={
            "to_status": "已恢复",
            "operator": "维修班组老张",
            "remark": "更换爆裂管段，恢复供水",
            "recovery_note": "供水恢复正常，地面积水已清理",
            "impact_note": "男厕暂停使用约 1 小时",
        },
    ).json()
    assert recovered["status"] == "已恢复"
    assert recovered["recovered_at"] is not None
    assert recovered["handling_minutes"] >= 0
    assert recovered["recovery_note"] == "供水恢复正常，地面积水已清理"
    assert recovered["impact_note"] == "男厕暂停使用约 1 小时"

    # 处置后仍可补充恢复情况与影响
    supplemented = client.patch(
        f"/api/v1/emergencies/{emergency['id']}",
        json={"impact_note": "男厕暂停使用约 1 小时，期间引导至临厕"},
    ).json()
    assert supplemented["impact_note"] == "男厕暂停使用约 1 小时，期间引导至临厕"

    closed = client.post(
        f"/api/v1/emergencies/{emergency['id']}/transitions",
        json={"to_status": "已关闭", "operator": "值班长", "remark": "归档关闭"},
    ).json()
    assert closed["status"] == "已关闭"
    assert closed["closed_at"] is not None
    assert [record["to_status"] for record in closed["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/emergencies/{emergency['id']}/records",
        json={"action": "处置进展", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    # 超时筛选：该事件实际响应晚于时限，应被筛出
    overdue = client.get("/api/v1/emergencies", params={"overdue": "true"}).json()
    assert any(item["id"] == emergency["id"] for item in overdue["items"])
    by_type = client.get("/api/v1/emergencies", params={"event_type": "设施爆裂"}).json()
    assert any(item["id"] == emergency["id"] for item in by_type["items"])

    # 公厕详情与删除保护计入应急事件
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["total_emergency_count"] >= 1
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409
    assert "应急事件" in blocked.json()["detail"]


def test_emergency_custom_response_limit(client, restroom):
    emergency = client.post(
        "/api/v1/emergencies",
        json={
            "restroom_id": restroom["id"],
            "title": "突发停电",
            "event_type": "停水停电",
            "response_limit_minutes": 15,
        },
    ).json()
    assert emergency["response_limit_minutes"] == 15

    # 修改事件类型且未显式指定时限时，按新类型重新约定
    updated = client.patch(
        f"/api/v1/emergencies/{emergency['id']}", json={"event_type": "污损外溢"}
    ).json()
    assert updated["event_type"] == "污损外溢"
    assert updated["response_limit_minutes"] == 40

    removed = client.delete(f"/api/v1/emergencies/{emergency['id']}")
    assert removed.status_code == 200
    assert client.get(f"/api/v1/emergencies/{emergency['id']}").status_code == 404
