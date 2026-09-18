import { EVENT_TYPE_TONES, isOverdue, scoreTone, severityTone, statusTone } from '../utils/format.js';

export function StatusTag({ status }) {
  return <span className={`tag ${statusTone(status)}`}>{status}</span>;
}

export function EventTypeTag({ type }) {
  return <span className={`tag ${EVENT_TYPE_TONES[type] || 'tag-neutral'}`}>{type}</span>;
}

/** 应急响应标签：展示响应耗时并按是否超过时限着色。 */
export function ResponseTag({ duration, limit, overdue, responded }) {
  if (!responded) {
    return overdue ? <span className="tag tag-danger">未到场·超时</span> : <span className="tag tag-info">待响应</span>;
  }
  const text = `响应 ${duration} 分钟 / 时限 ${limit} 分钟`;
  return <span className={`tag ${overdue ? 'tag-danger' : 'tag-success'}`}>{text}</span>;
}

export function SeverityTag({ severity }) {
  return <span className={`tag ${severityTone(severity)}`}>{severity}</span>;
}

export function ScorePill({ score }) {
  return <span className={`score-pill ${scoreTone(score)}`}>{Number(score).toFixed(1)}</span>;
}

export function OverdueTag({ deadline, status }) {
  if (!isOverdue(deadline, status)) return null;
  return <span className="tag tag-danger">已超期</span>;
}

export function GradeTag({ grade }) {
  const tone =
    grade === '优秀'
      ? 'tag-success'
      : grade === '良好'
        ? 'tag-primary'
        : grade === '合格'
          ? 'tag-warning'
          : 'tag-danger';
  return <span className={`tag ${tone}`}>{grade || '未评级'}</span>;
}
