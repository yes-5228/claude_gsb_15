import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';

/** 通用关闭操作：作废关闭 / 终止关闭 / 归档关闭。 */
export default function EmergencyCloseModal({ option, event, onClose, onSubmit, saving }) {
  const [operator, setOperator] = useState(event.responder || '');
  const [remark, setRemark] = useState('');

  const submit = (e) => {
    e.preventDefault();
    if (!operator.trim()) return;
    onSubmit({ to_status: option.status, operator: operator.trim(), remark: remark || null });
  };

  return (
    <Modal
      title={option.action}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="emergency-close" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={event.status} /> 变更为 <StatusTag status={option.status} />
      </div>
      <form id="emergency-close" className="form-grid" onSubmit={submit}>
        <Field label="操作人 *">
          <input value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="如：值班长周明" />
        </Field>
        <Field label="说明" full>
          <textarea
            rows="3"
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
            placeholder="如：确认现场恢复无异常，归档关闭"
          />
        </Field>
      </form>
    </Modal>
  );
}
