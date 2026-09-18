import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';

const PLACEHOLDER = {
  处置中: '填写响应情况，如：维修班组已到场关阀止水',
  已恢复: '填写处置结果，如：已更换爆裂管段，恢复供水',
  已关闭: '填写关闭原因，如：事件处置完毕归档',
};

export default function EmergencyActionModal({ option, emergency, onClose, onSubmit, saving }) {
  const [operator, setOperator] = useState(emergency.handler || '');
  const [remark, setRemark] = useState('');
  const [recoveryNote, setRecoveryNote] = useState('');
  const [impactNote, setImpactNote] = useState('');
  const [error, setError] = useState(null);

  const isRecover = option.status === '已恢复';

  const submit = (event) => {
    event.preventDefault();
    if (!operator.trim()) return;
    if (isRecover && !recoveryNote.trim()) {
      setError('流转到「已恢复」时需补充恢复情况');
      return;
    }
    setError(null);
    onSubmit({
      to_status: option.status,
      operator: operator.trim(),
      remark: remark || null,
      recovery_note: isRecover ? recoveryNote.trim() : null,
      impact_note: isRecover && impactNote.trim() ? impactNote.trim() : null,
    });
  };

  return (
    <Modal
      title={`应急处置 - ${option.action}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="emergency-action"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中...' : '确认提交'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={emergency.status} /> 变更为 <StatusTag status={option.status} />
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="emergency-action" className="form-grid" onSubmit={submit}>
        <Field label="操作人 *">
          <input
            value={operator}
            onChange={(event) => setOperator(event.target.value)}
            placeholder="如：维修班组张伟"
          />
        </Field>
        <Field label="处理说明" full>
          <textarea
            rows="3"
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            placeholder={PLACEHOLDER[option.status] || '填写本次处理说明'}
          />
        </Field>
        {isRecover ? (
          <>
            <Field label="恢复情况 *" full>
              <textarea
                rows="2"
                value={recoveryNote}
                onChange={(event) => setRecoveryNote(event.target.value)}
                placeholder="如：供水恢复正常，地面积水已清理消毒"
              />
            </Field>
            <Field label="造成的影响" full>
              <textarea
                rows="2"
                value={impactNote}
                onChange={(event) => setImpactNote(event.target.value)}
                placeholder="如：男厕暂停使用约 1 小时，未收到投诉"
              />
            </Field>
          </>
        ) : null}
      </form>
    </Modal>
  );
}
