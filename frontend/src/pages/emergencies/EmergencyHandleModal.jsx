import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { toDateTimeInput } from '../../utils/format.js';

const MEASURE_HINT = {
  停水: '如：启用储备水箱、张贴告示、联系自来水公司',
  停电: '如：拉设临时照明、电工排查线路、更换故障开关',
  设施爆裂: '如：关闭总阀、疏散人员、清理积水、更换爆裂管件',
  污损外溢: '如：设置围挡、高压疏通管道、全面消杀除味',
  其他: '填写现场采取的先期处置措施',
};

export default function EmergencyHandleModal({ event, onClose, onSubmit, saving }) {
  const [form, setForm] = useState({
    responder: event.responder || '',
    measure: '',
    response_time: toDateTimeInput(new Date()),
    remark: '',
  });
  const [error, setError] = useState(null);

  const setValue = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const submit = (event) => {
    event.preventDefault();
    if (!form.responder.trim()) {
      setError('请填写到场处置人');
      return;
    }
    if (!form.measure.trim()) {
      setError('请填写处置措施');
      return;
    }
    setError(null);
    onSubmit({
      responder: form.responder.trim(),
      measure: form.measure.trim(),
      response_time: form.response_time ? new Date(form.response_time).toISOString() : null,
      remark: form.remark || null,
    });
  };

  return (
    <Modal
      title="开始处置"
      onClose={onClose}
      width={720}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="emergency-handle" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认到场处置'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        登记后事件由「待处置」变更为「处置中」，系统按发现时间与到场时间计算响应耗时。
        该事件约定响应时限 {event.response_limit_minutes} 分钟。
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="emergency-handle" className="form-grid" onSubmit={submit}>
        <Field label="到场处置人 *">
          <input value={form.responder} onChange={setValue('responder')} placeholder="如：抢修班李建国" />
        </Field>
        <Field label="开始处置时间 *">
          <input type="datetime-local" value={form.response_time} onChange={setValue('response_time')} />
        </Field>
        <Field label="处置措施 *" full hint={MEASURE_HINT[event.event_type]}>
          <textarea rows="3" value={form.measure} onChange={setValue('measure')} />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
