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
    event_type: '停水',
    title: '',
    description: '',
    impact_scope: '',
    discoverer: '',
    discover_time: toDateTimeInput(new Date()),
    initial_remark: '',
  });

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setRestrooms)
      .catch((err) => setError(err.message));
  }, []);

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
        discover_time: form.discover_time ? new Date(form.discover_time).toISOString() : null,
      });
      toast.success('应急事件已登记，进入待处置状态');
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const limit = dictionaries?.emergency_response_limits?.[form.event_type];

  return (
    <Modal
      title="应急情况登记"
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
        <Field
          label="事件类型 *"
          hint={limit ? `约定响应时限 ${limit} 分钟` : undefined}
        >
          <select value={form.event_type} onChange={setValue('event_type')}>
            {(dictionaries?.emergency_type || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="事件标题 *" full>
          <input value={form.title} onChange={setValue('title')} placeholder="如：进水管道爆裂大量跑水" />
        </Field>
        <Field label="发现人">
          <input value={form.discoverer} onChange={setValue('discoverer')} placeholder="巡查员 / 值班人员" />
        </Field>
        <Field label="发现时间 *">
          <input
            type="datetime-local"
            value={form.discover_time}
            onChange={setValue('discover_time')}
          />
        </Field>
        <Field label="影响范围" full hint="受影响的区域、设施、人员或持续范围">
          <input
            value={form.impact_scope}
            onChange={setValue('impact_scope')}
            placeholder="如：女卫全部区域积水，影响相邻步道"
          />
        </Field>
        <Field label="事件情况描述" full>
          <textarea rows="3" value={form.description} onChange={setValue('description')} />
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
