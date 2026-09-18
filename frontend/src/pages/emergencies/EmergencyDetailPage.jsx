import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { emergencyApi } from '../../api/emergencies.js';
import DetailList from '../../components/DetailList.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { EmergencyTypeTag, ResponseTimeoutTag, StatusTag } from '../../components/Tags.jsx';
import Timeline from '../../components/Timeline.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDateTime, formatMinutes } from '../../utils/format.js';
import EmergencyActionModal from './EmergencyActionModal.jsx';
import EmergencyEditModal from './EmergencyEditModal.jsx';

export default function EmergencyDetailPage() {
  const { emergencyId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [activeOption, setActiveOption] = useState(null);
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [progressError, setProgressError] = useState(null);
  const [progress, setProgress] = useState({
    action: '处置进展',
    operator: '',
    remark: '',
  });

  const { data: emergency, loading, error, reload } = useAsync(
    () => emergencyApi.detail(emergencyId),
    [emergencyId],
  );
  const { data: options, reload: reloadOptions } = useAsync(
    () => emergencyApi.transitions(emergencyId),
    [emergencyId],
  );

  const refresh = () => {
    reload();
    reloadOptions();
  };

  const submitTransition = async (payload) => {
    setSaving(true);
    try {
      await emergencyApi.changeStatus(emergencyId, payload);
      toast.success('处置状态已更新');
      setActiveOption(null);
      refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitProgress = async (event) => {
    event.preventDefault();
    if (!progress.operator.trim()) {
      setProgressError('请填写操作人');
      return;
    }
    setProgressError(null);
    try {
      await emergencyApi.addRecord(emergencyId, {
        action: progress.action || '处置进展',
        operator: progress.operator.trim(),
        remark: progress.remark || null,
      });
      toast.success('已追加处置记录');
      setProgress({ action: progress.action, operator: progress.operator, remark: '' });
      reload();
    } catch (err) {
      setProgressError(err.message);
    }
  };

  const remove = async () => {
    if (!window.confirm('确认删除该应急事件及其处置记录？')) return;
    try {
      await emergencyApi.remove(emergencyId);
      toast.success('已删除');
      navigate('/emergencies');
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title={emergency ? `应急事件 ${emergency.code}` : '事件详情'}
        description={emergency?.title}
        actions={
          <>
            <Link className="btn" to="/emergencies">
              返回列表
            </Link>
            <button type="button" className="btn" onClick={() => setShowEdit(true)}>
              编辑信息
            </button>
            <button type="button" className="btn btn-danger" onClick={remove}>
              删除
            </button>
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !emergency ? <div className="loading-block">加载中...</div> : null}

        {emergency ? (
          <>
            <section className="card">
              <div className="card-title">
                <div className="inline">
                  <h3>{emergency.title}</h3>
                  <StatusTag status={emergency.status} />
                  <EmergencyTypeTag eventType={emergency.event_type} />
                  <ResponseTimeoutTag overdue={emergency.response_overdue} />
                </div>
                <span className="hint">最后更新：{formatDateTime(emergency.updated_at)}</span>
              </div>
              <DetailList
                items={[
                  {
                    label: '所属公厕',
                    value: emergency.restroom ? (
                      <Link to={`/restrooms/${emergency.restroom.id}`}>
                        {emergency.restroom.name}（{emergency.restroom.district}）
                      </Link>
                    ) : (
                      '-'
                    ),
                  },
                  { label: '事件类型', value: emergency.event_type },
                  {
                    label: '发现时间',
                    value: `${formatDateTime(emergency.discovered_at)} · 上报人：${
                      emergency.reporter || '-'
                    }`,
                  },
                  {
                    label: '约定响应时限',
                    value: `${formatMinutes(emergency.response_limit_minutes)}（限时至 ${formatDateTime(
                      emergency.response_due_at,
                    )}）`,
                  },
                  {
                    label: '响应时间 / 耗时',
                    value: emergency.responded_at
                      ? `${formatDateTime(emergency.responded_at)} · 耗时 ${formatMinutes(
                          emergency.response_minutes,
                        )}${emergency.response_overdue ? '（已超时）' : '（未超时）'}`
                      : '尚未响应',
                  },
                  { label: '处置人', value: emergency.handler || '未指派' },
                  {
                    label: '恢复时间 / 处置耗时',
                    value: emergency.recovered_at
                      ? `${formatDateTime(emergency.recovered_at)} · 处置耗时 ${formatMinutes(
                          emergency.handling_minutes,
                        )}`
                      : '尚未恢复',
                  },
                  { label: '关闭时间', value: formatDateTime(emergency.closed_at) },
                  { label: '影响范围', value: emergency.impact_scope || '无' },
                  { label: '处置措施', value: emergency.measures || '无' },
                  { label: '恢复情况', value: emergency.recovery_note || '待恢复后补充' },
                  { label: '造成的影响', value: emergency.impact_note || '待恢复后补充' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>处置流转</h3>
                <span className="hint">按流程推进，越级操作会被服务端拒绝</span>
              </div>
              {options?.length ? (
                <div className="action-group">
                  {options.map((option) => (
                    <button
                      key={option.status}
                      type="button"
                      className={`btn${option.status === '已恢复' ? ' btn-primary' : ''}`}
                      onClick={() => setActiveOption(option)}
                    >
                      {option.action}（变更为「{option.status}」）
                    </button>
                  ))}
                </div>
              ) : (
                <div className="alert alert-info">该事件已关闭，处置流程结束。</div>
              )}

              {emergency.status !== '已关闭' ? (
                <form className="form-grid" style={{ marginTop: 18 }} onSubmit={submitProgress}>
                  <Field label="记录类型">
                    <select
                      value={progress.action}
                      onChange={(event) =>
                        setProgress((prev) => ({ ...prev, action: event.target.value }))
                      }
                    >
                      <option>处置进展</option>
                      <option>现场核查</option>
                      <option>协调联动</option>
                    </select>
                  </Field>
                  <Field label="操作人 *">
                    <input
                      value={progress.operator}
                      onChange={(event) =>
                        setProgress((prev) => ({ ...prev, operator: event.target.value }))
                      }
                      placeholder="不改变状态，仅追加跟进记录"
                    />
                  </Field>
                  <Field label="说明" full>
                    <textarea
                      rows="2"
                      value={progress.remark}
                      onChange={(event) =>
                        setProgress((prev) => ({ ...prev, remark: event.target.value }))
                      }
                    />
                  </Field>
                  {progressError ? (
                    <div className="alert alert-error full">{progressError}</div>
                  ) : null}
                  <div className="full">
                    <button type="submit" className="btn">
                      追加处置记录
                    </button>
                  </div>
                </form>
              ) : null}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>处置轨迹</h3>
                <span className="hint">共 {emergency.records.length} 条记录</span>
              </div>
              <Timeline records={emergency.records} />
            </section>
          </>
        ) : null}
      </div>

      {activeOption && emergency ? (
        <EmergencyActionModal
          option={activeOption}
          emergency={emergency}
          saving={saving}
          onClose={() => setActiveOption(null)}
          onSubmit={submitTransition}
        />
      ) : null}

      {showEdit && emergency ? (
        <EmergencyEditModal emergency={emergency} onClose={() => setShowEdit(false)} onSaved={refresh} />
      ) : null}
    </>
  );
}
