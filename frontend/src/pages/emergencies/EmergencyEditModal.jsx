import { useState } from 'react';

import { emergencyApi } from '../../api/emergencies.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

export default function EmergencyEditModal({ emergency, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [form, setForm] = useState({
    title: emergency.title,
    event_type: emergency.event_type,
    discovered_at: emergency.discovered_at ? toDateTimeInput(emergency.discovered_at) : '',
    impact_scope: emergency.impact_scope || '',
    measures: emergency.measures || '',
    handler: emergency.handler || '',
    response_limit_minutes: String(emergency.response_limit_minutes ?? ''),
    recovery_note: emergency.recovery_note || '',
    impact_note: emergency.impact_note || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  // 切换事件类型时带出该类型约定的响应时限，仍可手动调整
  const changeType = (event) => {
    const eventType = event.target.value;
    const limit = dictionaries?.emergency_response_limits?.[eventType];
    setForm((prev) => ({
      ...prev,
      event_type: eventType,
      response_limit_minutes: limit ? String(limit) : prev.response_limit_minutes,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await emergencyApi.update(emergency.id, {
        title: form.title,
        event_type: form.event_type,
        discovered_at: form.discovered_at ? new Date(form.discovered_at).toISOString() : null,
        impact_scope: form.impact_scope,
        measures: form.measures,
        handler: form.handler,
        response_limit_minutes: form.response_limit_minutes
          ? Number(form.response_limit_minutes)
          : null,
        recovery_note: form.recovery_note || null,
        impact_note: form.impact_note || null,
      });
      toast.success('事件信息已更新');
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const recovered = ['已恢复', '已关闭'].includes(emergency.status);

  return (
    <Modal
      title={`编辑事件 - ${emergency.code}`}
      onClose={onClose}
      width={780}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="emergency-edit" className="btn btn-primary" disabled={saving}>
            保存
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="emergency-edit" className="form-grid" onSubmit={submit}>
        <Field label="事件标题" full>
          <input value={form.title} onChange={setValue('title')} />
        </Field>
        <Field label="事件类型">
          <select value={form.event_type} onChange={changeType}>
            {(dictionaries?.emergency_type || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="发现时间">
          <input
            type="datetime-local"
            value={form.discovered_at}
            onChange={setValue('discovered_at')}
          />
        </Field>
        <Field label="处置人">
          <input value={form.handler} onChange={setValue('handler')} />
        </Field>
        <Field label="约定响应时限（分钟）">
          <input
            type="number"
            min="1"
            max="1440"
            value={form.response_limit_minutes}
            onChange={setValue('response_limit_minutes')}
          />
        </Field>
        <Field label="影响范围" full>
          <textarea rows="2" value={form.impact_scope} onChange={setValue('impact_scope')} />
        </Field>
        <Field label="处置措施" full>
          <textarea rows="3" value={form.measures} onChange={setValue('measures')} />
        </Field>
        {recovered ? (
          <>
            <Field label="恢复情况" full hint="处置后补充">
              <textarea rows="2" value={form.recovery_note} onChange={setValue('recovery_note')} />
            </Field>
            <Field label="造成的影响" full hint="处置后补充">
              <textarea rows="2" value={form.impact_note} onChange={setValue('impact_note')} />
            </Field>
          </>
        ) : null}
      </form>
    </Modal>
  );
}
