import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { toDateTimeInput } from '../../utils/format.js';

export default function EmergencyRecoverModal({ event, onClose, onSubmit, saving }) {
  const [form, setForm] = useState({
    recover_note: '',
    impact_detail: event.impact_detail || '',
    recover_time: toDateTimeInput(new Date()),
    remark: '',
  });
  const [error, setError] = useState(null);

  const setValue = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const submit = (event) => {
    event.preventDefault();
    if (!form.recover_note.trim()) {
      setError('请填写恢复情况');
      return;
    }
    setError(null);
    onSubmit({
      recover_note: form.recover_note.trim(),
      impact_detail: form.impact_detail.trim() || null,
      recover_time: form.recover_time ? new Date(form.recover_time).toISOString() : null,
      remark: form.remark || null,
    });
  };

  return (
    <Modal
      title="恢复情况登记"
      onClose={onClose}
      width={720}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="emergency-recover" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认恢复'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        登记后事件由「处置中」变更为「已恢复」，请补充现场恢复情况与本次事件造成的影响。
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="emergency-recover" className="form-grid" onSubmit={submit}>
        <Field label="恢复时间 *" full={false}>
          <input type="datetime-local" value={form.recover_time} onChange={setValue('recover_time')} />
        </Field>
        <Field label="恢复情况 *" full hint="如：供水恢复、积水退净、消杀完成、设施运行正常">
          <textarea rows="3" value={form.recover_note} onChange={setValue('recover_note')} />
        </Field>
        <Field label="造成的影响" full hint="如：停业时长、影响人次、财产损失等">
          <textarea rows="3" value={form.impact_detail} onChange={setValue('impact_detail')} />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
