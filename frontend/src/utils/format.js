export function formatDateTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function formatShortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

/** 把 Date 或 ISO 字符串转成 datetime-local 输入框需要的值。 */
export function toDateTimeInput(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export const STATUS_TONES = {
  正常开放: 'tag-success',
  维修中: 'tag-warning',
  暂停使用: 'tag-neutral',
  待整改: 'tag-danger',
  整改中: 'tag-warning',
  待验收: 'tag-info',
  已完成: 'tag-success',
  已关闭: 'tag-neutral',
  正常: 'tag-success',
  发现问题: 'tag-danger',
  待响应: 'tag-danger',
  处置中: 'tag-warning',
  已恢复: 'tag-success',
};

export const EMERGENCY_TYPE_TONES = {
  停水停电: 'tag-info',
  设施爆裂: 'tag-danger',
  污损外溢: 'tag-warning',
  其他: 'tag-neutral',
};

export function emergencyTypeTone(eventType) {
  return EMERGENCY_TYPE_TONES[eventType] || 'tag-neutral';
}

/** 把分钟数格式化为易读时长，如 45分钟 / 1小时30分 / 2天3小时。 */
export function formatMinutes(minutes) {
  if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) return '-';
  const total = Math.round(Number(minutes));
  if (total < 60) return `${total}分钟`;
  const hours = Math.floor(total / 60);
  const restMinutes = total % 60;
  if (hours < 24) return restMinutes ? `${hours}小时${restMinutes}分` : `${hours}小时`;
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours ? `${days}天${restHours}小时` : `${days}天`;
}

export const SEVERITY_TONES = {
  一般: 'tag-neutral',
  严重: 'tag-warning',
  紧急: 'tag-danger',
};

export function statusTone(status) {
  return STATUS_TONES[status] || 'tag-neutral';
}

export function severityTone(severity) {
  return SEVERITY_TONES[severity] || 'tag-neutral';
}

export function scoreTone(score) {
  if (score >= 90) return 'score-high';
  if (score >= 70) return 'score-mid';
  return 'score-low';
}

/** 是否超期未整改。 */
export function isOverdue(deadline, status) {
  if (!deadline) return false;
  if (['已完成', '已关闭'].includes(status)) return false;
  return new Date(deadline).getTime() < Date.now();
}
