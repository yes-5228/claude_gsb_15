import { useState } from 'react';
import { Link } from 'react-router-dom';

import { emergencyApi } from '../../api/emergencies.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { EventTypeTag, ResponseTag, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import EmergencyFormModal from './EmergencyFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  status: '',
  event_type: '',
  overdue: '',
  open_only: '',
  recovered: '',
};

export default function EmergencyListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);

  const list = useListQuery((params) => emergencyApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const remove = async (row) => {
    if (!window.confirm(`确认删除应急事件「${row.title}」及其处置记录？`)) return;
    try {
      await emergencyApi.remove(row.id);
      toast.success('删除成功');
      list.reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title="应急情况处置记录"
        description="停水停电、设施爆裂、污损外溢等事件的发现登记、响应计时与恢复闭环"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowForm(true)}
          >
            + 登记应急事件
          </button>
        }
      />
      <div className="content">
        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="标题 / 描述 / 编号 / 发现人 / 处置人"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="事件类型">
              <select
                value={list.filters.event_type}
                onChange={(event) => list.updateFilter('event_type', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.emergency_type || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="处置状态">
              <select
                value={list.filters.status}
                onChange={(event) => list.updateFilter('status', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.emergency_status || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="所属区域">
              <select
                value={list.filters.district}
                onChange={(event) => list.updateFilter('district', event.target.value)}
              >
                <option value="">全部</option>
                {(districts || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="响应时限">
              <select
                value={list.filters.overdue}
                onChange={(event) => list.updateFilter('overdue', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看响应超时</option>
                <option value="false">仅看响应及时</option>
              </select>
            </Field>
            <Field label="处置进展">
              <select
                value={list.filters.open_only}
                onChange={(event) => list.updateFilter('open_only', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看处置中</option>
              </select>
            </Field>
            <Field label="恢复情况">
              <select
                value={list.filters.recovered}
                onChange={(event) => list.updateFilter('recovered', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看已恢复</option>
                <option value="false">仅看未恢复</option>
              </select>
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>
        </section>

        <section className="card">
          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无应急事件记录"
            columns={[
              { key: 'code', title: '编号' },
              {
                key: 'title',
                title: '事件',
                wrap: true,
                render: (row) => <Link to={`/emergencies/${row.id}`}>{row.title}</Link>,
              },
              {
                key: 'restroom',
                title: '公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              { key: 'event_type', title: '类型', render: (row) => <EventTypeTag type={row.event_type} /> },
              {
                key: 'status',
                title: '状态',
                render: (row) => <StatusTag status={row.status} />,
              },
              {
                key: 'response',
                title: '响应耗时',
                render: (row) => (
                  <ResponseTag
                    responded={row.response_time != null}
                    duration={row.response_duration_minutes}
                    limit={row.response_limit_minutes}
                    overdue={row.response_overdue}
                  />
                ),
              },
              { key: 'responder', title: '处置人', render: (row) => row.responder || '-' },
              {
                key: 'discover_time',
                title: '发现时间',
                render: (row) => formatDateTime(row.discover_time),
              },
              {
                key: 'recover_time',
                title: '恢复时间',
                render: (row) => formatDateTime(row.recover_time),
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <Link className="btn-link" to={`/emergencies/${row.id}`}>
                      详情 / 处置
                    </Link>
                    <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                      删除
                    </button>
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <EmergencyFormModal
          onClose={() => setShowForm(false)}
          onSaved={list.reload}
        />
      ) : null}
    </>
  );
}
