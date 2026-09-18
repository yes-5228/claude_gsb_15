"""应急情况处置记录接口测试：登记、响应时限、处置流转、恢复补充。"""

from datetime import datetime, timedelta


def _create_event(client, restroom, **overrides):
    payload = {
        "restroom_id": restroom["id"],
        "event_type": "设施爆裂",
        "title": "进水管爆裂跑水",
        "description": "洗手台下方管道爆裂",
        "impact_scope": "女卫全部区域积水",
        "discoverer": "张巡查",
    }
    payload.update(overrides)
    response = client.post("/api/v1/emergencies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_emergency_dictionary_and_create(client, restroom):
    dictionaries = client.get("/api/v1/meta/dictionaries").json()
    assert dictionaries["emergency_type"] == ["停水", "停电", "设施爆裂", "污损外溢", "其他"]
    assert dictionaries["emergency_response_limits"]["设施爆裂"] == 15
    assert dictionaries["emergency_response_limits"]["停水"] == 30
    assert dictionaries["emergency_transitions"]["处置中"] == ["已恢复", "已关闭"]

    event = _create_event(client, restroom)
    assert event["code"].startswith("YJ-")
    assert event["status"] == "待处置"
    assert event["response_limit_minutes"] == 15
    assert event["response_duration_minutes"] is None
    assert event["response_overdue"] is False
    assert event["is_open"] is True
    assert len(event["records"]) == 1
    assert event["records"][0]["action"] == "发现登记"


def test_emergency_full_lifecycle_with_response_duration(client, restroom):
    # 补录一起 3 小时前发现、已恢复待关闭的事件，保证各动作时间按真实时序落在过去
    discover = datetime.now() - timedelta(minutes=180)
    event = _create_event(
        client, restroom, discover_time=discover.isoformat()
    )

    # 越级流转被拒绝：待处置 -> 已恢复
    invalid = client.post(
        f"/api/v1/emergencies/{event['id']}/transitions",
        json={"to_status": "已恢复", "operator": "值班长"},
    )
    assert invalid.status_code == 400

    # 开始处置：响应耗时 10 分钟，设施爆裂时限 15 分钟，未超时
    response_time = discover + timedelta(minutes=10)
    handled = client.post(
        f"/api/v1/emergencies/{event['id']}/handle",
        json={
            "responder": "抢修班李建国",
            "measure": "关闭总阀、清理积水、更换爆裂管件",
            "response_time": response_time.isoformat(),
        },
    ).json()
    assert handled["status"] == "处置中"
    assert handled["response_duration_minutes"] == 10
    assert handled["response_overdue"] is False
    assert handled["measure"].startswith("关闭总阀")

    # 恢复时间不能早于开始处置时间
    early_recover = client.post(
        f"/api/v1/emergencies/{event['id']}/recover",
        json={
            "recover_note": "恢复",
            "recover_time": (response_time - timedelta(minutes=1)).isoformat(),
        },
    )
    assert early_recover.status_code == 400
    assert "恢复时间" in early_recover.json()["detail"]

    # 补充恢复情况与造成的影响：处置中 -> 已恢复
    recovered = client.post(
        f"/api/v1/emergencies/{event['id']}/recover",
        json={
            "recover_note": "管件更换完成，供水恢复，地面无积水",
            "impact_detail": "跑水约 20 分钟，影响如厕市民约 30 人",
            "recover_time": (response_time + timedelta(hours=2)).isoformat(),
        },
    ).json()
    assert recovered["status"] == "已恢复"
    assert recovered["recover_note"].startswith("管件更换")
    assert "跑水" in recovered["impact_detail"]
    assert recovered["handle_duration_minutes"] == 130

    closed = client.post(
        f"/api/v1/emergencies/{event['id']}/transitions",
        json={"to_status": "已关闭", "operator": "值班长周明", "remark": "归档"},
    ).json()
    assert closed["status"] == "已关闭"
    assert closed["close_time"] is not None
    assert closed["is_open"] is False
    assert closed["records"][-1]["action"] == "归档关闭"

    # 关闭后不允许追加记录
    blocked = client.post(
        f"/api/v1/emergencies/{event['id']}/records",
        json={"operator": "周明", "remark": "补充"},
    )
    assert blocked.status_code == 400


def test_emergency_response_overtime(client, restroom):
    """响应耗时超过设施爆裂 15 分钟时限时，应标记超时。"""
    discover = datetime.now() - timedelta(hours=1)
    event = _create_event(client, restroom, discover_time=discover.isoformat())

    # 尚未到场且已超过时限：列表超时筛选可查到
    overdue_list = client.get(
        "/api/v1/emergencies", params={"overdue": "true"}
    ).json()
    assert any(item["id"] == event["id"] for item in overdue_list["items"])

    handled = client.post(
        f"/api/v1/emergencies/{event['id']}/handle",
        json={
            "responder": "抢修班李建国",
            "measure": "到场关闭阀门并抽水",
            "response_time": (discover + timedelta(minutes=20)).isoformat(),
        },
    ).json()
    assert handled["response_duration_minutes"] == 20
    assert handled["response_overdue"] is True

    # 已开始处置后即使当前已过时限，结论以实际响应耗时为准（20>15 仍超时）
    recovered = client.post(
        f"/api/v1/emergencies/{event['id']}/recover",
        json={
            "recover_note": "管件更换完成，恢复供水",
            "impact_detail": "积水约 10 平方米，封闭 30 分钟",
        },
    ).json()
    assert recovered["status"] == "已恢复"
    assert recovered["recover_note"].startswith("管件更换")
    assert "积水" in recovered["impact_detail"]
    assert recovered["handle_duration_minutes"] >= 60


def test_emergency_update_guard_and_filters(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "城南", "address": "测试路 9 号"},
    ).json()
    event = _create_event(
        client,
        restroom,
        event_type="停水",
        title="计划外停水",
        discover_time=(datetime.now() - timedelta(days=2)).isoformat(),
    )

    # 待处置阶段可补正
    updated = client.patch(
        f"/api/v1/emergencies/{event['id']}", json={"title": "市政管网检修停水"}
    ).json()
    assert updated["title"] == "市政管网检修停水"

    # 开始处置后不允许修改登记信息
    client.post(
        f"/api/v1/emergencies/{event['id']}/handle",
        json={"responder": "王师傅", "measure": "启用应急水箱"},
    )
    blocked = client.patch(
        f"/api/v1/emergencies/{event['id']}", json={"title": "新标题"}
    )
    assert blocked.status_code == 400

    # 另建一条停电事件，用于类型与区域筛选
    other_event = _create_event(client, other, event_type="停电", title="配电故障停电")

    by_type = client.get("/api/v1/emergencies", params={"event_type": "停电"}).json()
    assert {item["id"] for item in by_type["items"]} == {other_event["id"]}

    by_district = client.get("/api/v1/emergencies", params={"district": "城南"}).json()
    assert all(item["restroom"]["district"] == "城南" for item in by_district["items"])

    open_only = client.get(
        "/api/v1/emergencies", params={"open_only": "true"}
    ).json()
    assert {item["status"] for item in open_only["items"]} <= {"待处置", "处置中"}

    recovered_filter = client.get(
        "/api/v1/emergencies", params={"recovered": "false"}
    ).json()
    assert all(item["recover_time"] is None for item in recovered_filter["items"])

    keyword = client.get(
        "/api/v1/emergencies", params={"keyword": "市政管网"}
    ).json()
    assert keyword["meta"]["total"] == 1

    # 公厕详情带应急事件统计，且删除保护提示包含应急事件数量
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["total_emergency_count"] == 1
    assert detail["open_emergency_count"] == 1

    guard = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert guard.status_code == 409
    assert "应急事件" in guard.json()["detail"]
