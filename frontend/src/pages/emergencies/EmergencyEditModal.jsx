import { useState } from 'react';

import { emergencyApi } from '../../api/emergencies.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

/** 仅待处置阶段可补正登记信息（服务端同样校验）。 */
export default function EmergencyEditModal({ event, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [form, setForm] = useState({
    event_type: event.event_type,
    title: event.title,
    description: event.description || '',
    impact_scope: event.impact_scope || '',
    discoverer: event.discoverer || '',
    discover_time: event.discover_time ? toDateTimeInput(event.discover_time) : '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await emergencyApi.update(event.id, {
        ...form,
        discover_time: form.discover_time ? new Date(form.discover_time).toISOString() : null,
      });
      toast.success('登记信息已更新');
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`补正登记 - ${event.code}`}
      onClose={onClose}
      width={720}
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
        <Field label="事件类型">
          <select value={form.event_type} onChange={setValue('event_type')}>
            {(dictionaries?.emergency_type || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="发现人">
          <input value={form.discoverer} onChange={setValue('discoverer')} />
        </Field>
        <Field label="事件标题" full>
          <input value={form.title} onChange={setValue('title')} />
        </Field>
        <Field label="发现时间">
          <input type="datetime-local" value={form.discover_time} onChange={setValue('discover_time')} />
        </Field>
        <Field label="影响范围" full>
          <input value={form.impact_scope} onChange={setValue('impact_scope')} />
        </Field>
        <Field label="事件情况描述" full>
          <textarea rows="3" value={form.description} onChange={setValue('description')} />
        </Field>
      </form>
    </Modal>
  );
}
