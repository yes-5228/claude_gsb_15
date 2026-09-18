import { useEffect, useState } from 'react';

import { emergencyApi } from '../../api/emergencies.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

export default function EmergencyFormModal({ defaultRestroomId, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [restrooms, setRestrooms] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: defaultRestroomId ? Number(defaultRestroomId) : '',
    title: '',
    event_type: '停水停电',
    discovered_at: toDateTimeInput(new Date()),
    impact_scope: '',
    measures: '',
    reporter: '',
    handler: '',
    response_limit_minutes: '',
    initial_remark: '',
  });

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setRestrooms)
      .catch((err) => setError(err.message));
  }, []);

  // 事件类型变化时带出该类型约定的响应时限，仍可手动调整
  useEffect(() => {
    const limit = dictionaries?.emergency_response_limits?.[form.event_type];
    if (limit) {
      setForm((prev) => ({ ...prev, response_limit_minutes: String(limit) }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.event_type, dictionaries]);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.restroom_id) {
      setError('请选择所属公厕');
      return;
    }
    if (!form.title.trim()) {
      setError('请填写事件标题');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await emergencyApi.create({
        ...form,
        restroom_id: Number(form.restroom_id),
        discovered_at: form.discovered_at ? new Date(form.discovered_at).toISOString() : null,
        response_limit_minutes: form.response_limit_minutes
          ? Number(form.response_limit_minutes)
          : null,
      });
      toast.success('应急事件已登记，进入待响应状态');
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
      title="登记应急事件"
      onClose={onClose}
      width={780}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="emergency-form" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '提交登记'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="emergency-form" className="form-grid" onSubmit={submit}>
        <Field label="所属公厕 *">
          <select value={form.restroom_id} onChange={setValue('restroom_id')}>
            <option value="">请选择公厕</option>
            {restrooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} {item.name}（{item.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="事件类型">
          <select value={form.event_type} onChange={setValue('event_type')}>
            {(dictionaries?.emergency_type || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="事件标题 *" full>
          <input
            value={form.title}
            onChange={setValue('title')}
            placeholder="如：主供水管爆裂喷水"
          />
        </Field>
        <Field label="发现时间">
          <input
            type="datetime-local"
            value={form.discovered_at}
            onChange={setValue('discovered_at')}
          />
        </Field>
        <Field label="约定响应时限（分钟）" hint="按事件类型自动带出，可调整">
          <input
            type="number"
            min="1"
            max="1440"
            value={form.response_limit_minutes}
            onChange={setValue('response_limit_minutes')}
          />
        </Field>
        <Field label="影响范围" full>
          <textarea
            rows="2"
            value={form.impact_scope}
            onChange={setValue('impact_scope')}
            placeholder="如：全厕停水，蹲位冲洗与洗手台均不可用"
          />
        </Field>
        <Field label="处置措施" full>
          <textarea
            rows="3"
            value={form.measures}
            onChange={setValue('measures')}
            placeholder="如：联系供水部门排查，启用临时储水应急冲洗"
          />
        </Field>
        <Field label="上报人">
          <input value={form.reporter} onChange={setValue('reporter')} placeholder="巡查员 / 群众" />
        </Field>
        <Field label="处置人">
          <input value={form.handler} onChange={setValue('handler')} placeholder="维修班组 / 责任人" />
        </Field>
        <Field label="登记说明" full>
          <textarea
            rows="2"
            value={form.initial_remark}
            onChange={setValue('initial_remark')}
            placeholder="将记录在处置轨迹的首条节点"
          />
        </Field>
      </form>
    </Modal>
  );
}
