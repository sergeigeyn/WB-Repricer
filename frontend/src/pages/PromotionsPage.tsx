import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Tabs, Typography, Spin, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import apiClient from '@/api/client';

interface Promotion {
  id: number;
  wb_promo_id: string | null;
  name: string;
  start_date: string | null;
  end_date: string | null;
  promo_type: string | null;
  status: string | null;
  in_action_count: number;
  total_available: number;
  products_count: number;
  avg_current_margin: number | null;
  avg_promo_margin: number | null;
  profitable_count: number;
}

const statusColors: Record<string, string> = {
  active: 'green',
  upcoming: 'orange',
  ended: 'default',
};

const statusLabels: Record<string, string> = {
  active: 'Активная',
  upcoming: 'Будущая',
  ended: 'Завершена',
};

const typeLabels: Record<string, string> = {
  regular: 'Обычная',
  auto: 'Авто',
};

function formatDate(d: string | null): string {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

export default function PromotionsPage() {
  const navigate = useNavigate();
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active');

  const fetchPromotions = async (status?: string) => {
    setLoading(true);
    try {
      const params = status && status !== 'all' ? { status } : {};
      const res = await apiClient.get('/promotions', { params });
      setPromotions(res.data.items || []);
    } catch (e: any) {
      message.error('Ошибка загрузки акций');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPromotions(activeTab);
  }, [activeTab]);

  const columns: ColumnsType<Promotion> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      width: 280,
      ellipsis: true,
      render: (name: string, record) => (
        <a onClick={() => navigate(`/promotions/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'promo_type',
      key: 'promo_type',
      width: 90,
      render: (t: string) => typeLabels[t] || t || '—',
    },
    {
      title: 'Период',
      key: 'period',
      width: 120,
      render: (_, r) => `${formatDate(r.start_date)} — ${formatDate(r.end_date)}`,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{statusLabels[s] || s}</Tag>
      ),
    },
    {
      title: 'Товаров',
      dataIndex: 'products_count',
      key: 'products_count',
      width: 80,
      align: 'right',
    },
    {
      title: 'В акции',
      dataIndex: 'in_action_count',
      key: 'in_action_count',
      width: 80,
      align: 'right',
    },
    {
      title: 'Маржа тек.',
      dataIndex: 'avg_current_margin',
      key: 'avg_current_margin',
      width: 100,
      align: 'right',
      render: (v: number | null) =>
        v !== null ? `${v.toFixed(1)}%` : '—',
    },
    {
      title: 'Маржа акц.',
      dataIndex: 'avg_promo_margin',
      key: 'avg_promo_margin',
      width: 100,
      align: 'right',
      render: (v: number | null) => {
        if (v === null) return '—';
        const color = v > 0 ? '#3f8600' : '#cf1322';
        return <span style={{ color, fontWeight: 600 }}>{v.toFixed(1)}%</span>;
      },
    },
    {
      title: 'Выгодных',
      dataIndex: 'profitable_count',
      key: 'profitable_count',
      width: 90,
      align: 'right',
      render: (v: number, r) => {
        if (!r.products_count) return '—';
        return `${v} / ${r.products_count}`;
      },
    },
  ];

  return (
    <div>
      <Typography.Title level={3}>Акции</Typography.Title>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'active', label: 'Активные' },
          { key: 'upcoming', label: 'Будущие' },
          { key: 'ended', label: 'Завершённые' },
          { key: 'all', label: 'Все' },
        ]}
      />
      <Spin spinning={loading}>
        <Table
          dataSource={promotions}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="middle"
          bordered
          scroll={{ x: 1100 }}
        />
      </Spin>
    </div>
  );
}
