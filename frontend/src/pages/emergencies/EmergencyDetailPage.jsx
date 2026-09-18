import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { emergencyApi } from '../../api/emergencies.js';
import DetailList from '../../components/DetailList.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Timeline from '../../components/Timeline.jsx';
import { EventTypeTag, ResponseTag, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDateTime, formatMinutes } from '../../utils/format.js';
import EmergencyCloseModal from './EmergencyCloseModal.jsx';
import EmergencyEditModal from './EmergencyEditModal.jsx';
import EmergencyHandleModal from './EmergencyHandleModal.jsx';
import EmergencyRecoverModal from './EmergencyRecoverModal.jsx';

export default function EmergencyDetailPage() {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [activeOption, setActiveOption] = useState(null);
  const [mode, setMode] = useState(null); // handle | recover | close
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [progressError, setProgressError] = useState(null);
  const [progress, setProgress] = useState({ action: '处置跟进', operator: '', remark: '' });

  const { data: event, loading, error, reload } = useAsync(
    () => emergencyApi.detail(eventId),
    [eventId],
  );
  const { data: options } = useAsync(() => emergencyApi.transitions(eventId), [eventId]);

  const openAction = (option) => {
    setActiveOption(option);
    setMode(option.status === '已恢复' ? 'recover' : 'close');
  };

  const submitHandle = async (payload) => {
    setSaving(true);
    try {
      await emergencyApi.handle(eventId, payload);
      toast.success('处置措施已登记');
      setMode(null);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitRecover = async (payload) => {
    setSaving(true);
    try {
      await emergencyApi.recover(eventId, payload);
      toast.success('恢复情况已登记，事件进入已恢复状态');
      setMode(null);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitClose = async (payload) => {
    setSaving(true);
    try {
      await emergencyApi.changeStatus(eventId, payload);
      toast.success('事件已关闭');
      setMode(null);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitProgress = async (e) => {
    e.preventDefault();
    if (!progress.operator.trim()) {
      setProgressError('请填写操作人');
      return;
    }
    setProgressError(null);
    try {
      await emergencyApi.addRecord(eventId, {
        action: progress.action || '处置跟进',
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
      await emergencyApi.remove(eventId);
      toast.success('已删除');
      navigate('/emergencies');
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title={event ? `应急事件 ${event.code}` : '应急事件详情'}
        description={event?.title}
        actions={
          <>
            <Link className="btn" to="/emergencies">
              返回列表
            </Link>
            {event?.status === '待处置' ? (
              <button type="button" className="btn" onClick={() => setShowEdit(true)}>
                补正登记
              </button>
            ) : null}
            <button type="button" className="btn btn-danger" onClick={remove}>
              删除
            </button>
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !event ? <div className="loading-block">加载中...</div> : null}

        {event ? (
          <>
            <div className="stat-grid">
              <div className={`stat-card${event.response_overdue ? ' is-danger' : ' is-info'}`}>
                <div className="label">响应耗时</div>
                <div className="value" style={{ fontSize: 26 }}>
                  {event.response_time ? formatMinutes(event.response_duration_minutes) : '未到场'}
                </div>
                <div className="foot">
                  约定时限 {event.response_limit_minutes} 分钟 ·{' '}
                  {event.response_time
                    ? event.response_overdue
                      ? '响应超时'
                      : '响应及时'
                    : '等待到场处置'}
                </div>
              </div>
              <div className="stat-card">
                <div className="label">事件持续时长</div>
                <div className="value" style={{ fontSize: 26 }}>
                  {formatMinutes(event.handle_duration_minutes)}
                </div>
                <div className="foot">
                  {event.recover_time
                    ? `已于 ${formatDateTime(event.recover_time)} 恢复`
                    : '自发现起计时，尚未恢复'}
                </div>
              </div>
              <div className={`stat-card${event.is_open ? ' is-warning' : ''}`}>
                <div className="label">处置状态</div>
                <div className="value" style={{ fontSize: 26 }}>
                  {event.status}
                </div>
                <div className="foot">
                  {event.is_open ? '事件处置中' : `关闭于 ${formatDateTime(event.close_time)}`}
                </div>
              </div>
            </div>

            <section className="card">
              <div className="card-title">
                <div className="inline">
                  <h3>{event.title}</h3>
                  <EventTypeTag type={event.event_type} />
                  <StatusTag status={event.status} />
                  <ResponseTag
                    responded={event.response_time != null}
                    duration={event.response_duration_minutes}
                    limit={event.response_limit_minutes}
                    overdue={event.response_overdue}
                  />
                </div>
                <span className="hint">最后更新：{formatDateTime(event.updated_at)}</span>
              </div>
              <DetailList
                items={[
                  {
                    label: '所属公厕',
                    value: event.restroom ? (
                      <Link to={`/restrooms/${event.restroom.id}`}>
                        {event.restroom.name}（{event.restroom.district}）
                      </Link>
                    ) : (
                      '-'
                    ),
                  },
                  {
                    label: '发现人 / 时间',
                    value: `${event.discoverer || '-'} · ${formatDateTime(event.discover_time)}`,
                  },
                  { label: '影响范围', value: event.impact_scope || '未填写' },
                  {
                    label: '开始处置 / 处置人',
                    value: event.response_time
                      ? `${formatDateTime(event.response_time)} · ${event.responder || '-'}`
                      : '尚未到场处置',
                  },
                  { label: '处置措施', value: event.measure || '尚未登记' },
                  { label: '恢复时间', value: formatDateTime(event.recover_time) },
                  { label: '恢复情况', value: event.recover_note || '尚未恢复' },
                  { label: '造成的影响', value: event.impact_detail || '未填写' },
                  { label: '事件情况描述', value: event.description || '无' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>处置流转</h3>
                <span className="hint">待处置 → 处置中 → 已恢复 → 已关闭</span>
              </div>
              {options?.length ? (
                <div className="action-group">
                  {options.map((option) =>
                    option.status === '处置中' ? (
                      <button
                        key={option.status}
                        type="button"
                        className="btn btn-primary"
                        onClick={() => setMode('handle')}
                      >
                        {option.action}（登记处置措施）
                      </button>
                    ) : (
                      <button
                        key={option.status}
                        type="button"
                        className={`btn${option.status === '已恢复' ? ' btn-primary' : ''}`}
                        onClick={() => openAction(option)}
                      >
                        {option.action}
                        {option.status === '已关闭' ? '' : `（变更为「${option.status}」）`}
                      </button>
                    ),
                  )}
                </div>
              ) : (
                <div className="alert alert-info">该事件已关闭，处置流程结束。</div>
              )}

              {event.status !== '已关闭' ? (
                <form className="form-grid" style={{ marginTop: 18 }} onSubmit={submitProgress}>
                  <Field label="记录类型">
                    <select
                      value={progress.action}
                      onChange={(e) =>
                        setProgress((prev) => ({ ...prev, action: e.target.value }))
                      }
                    >
                      <option>处置跟进</option>
                      <option>现场抢修</option>
                      <option>物资协调</option>
                      <option>外部联动</option>
                    </select>
                  </Field>
                  <Field label="操作人 *">
                    <input
                      value={progress.operator}
                      onChange={(e) =>
                        setProgress((prev) => ({ ...prev, operator: e.target.value }))
                      }
                      placeholder="不改变状态，仅追加跟进记录"
                    />
                  </Field>
                  <Field label="说明" full>
                    <textarea
                      rows="2"
                      value={progress.remark}
                      onChange={(e) =>
                        setProgress((prev) => ({ ...prev, remark: e.target.value }))
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
                <span className="hint">共 {event.records.length} 条记录</span>
              </div>
              <Timeline records={event.records} />
            </section>
          </>
        ) : null}
      </div>

      {mode === 'handle' && event ? (
        <EmergencyHandleModal
          event={event}
          saving={saving}
          onClose={() => setMode(null)}
          onSubmit={submitHandle}
        />
      ) : null}
      {mode === 'recover' && event ? (
        <EmergencyRecoverModal
          event={event}
          saving={saving}
          onClose={() => setMode(null)}
          onSubmit={submitRecover}
        />
      ) : null}
      {mode === 'close' && activeOption && event ? (
        <EmergencyCloseModal
          option={activeOption}
          event={event}
          saving={saving}
          onClose={() => setMode(null)}
          onSubmit={submitClose}
        />
      ) : null}

      {showEdit && event ? (
        <EmergencyEditModal event={event} onClose={() => setShowEdit(false)} onSaved={reload} />
      ) : null}
    </>
  );
}
