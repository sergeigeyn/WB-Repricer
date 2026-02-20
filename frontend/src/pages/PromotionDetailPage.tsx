import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Image,
  message,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import apiClient from '@/api/client';

interface PromotionInfo {
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

interface PromoProduct {
  nm_id: number;
  vendor_code: string | null;
  title: string | null;
  image_url: string | null;
  plan_price: number | null;
  plan_discount: number | null;
  current_price: number | null;
  in_action: boolean;
  current_margin_pct: number | null;
  current_margin_rub: number | null;
  promo_margin_pct: number | null;
  promo_margin_rub: number | null;
  decision: string;
}

const statusLabels: Record<string, string> = {
  active: 'Активная',
  upcoming: 'Будущая',
  ended: 'Завершена',
};

const statusColors: Record<string, string> = {
  active: 'green',
  upcoming: 'orange',
  ended: 'default',
};

const decisionLabels: Record<string, { text: string; color: string }> = {
  enter: { text: 'Входим', color: 'green' },
  skip: { text: 'Пропуск', color: 'red' },
  pending: { text: 'Решение', color: 'default' },
};

function formatDate(d: string | null): string {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU');
}

function marginColor(v: number | null): string {
  if (v === null) return 'inherit';
  return v > 0 ? '#3f8600' : '#cf1322';
}

export default function PromotionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [promo, setPromo] = useState<PromotionInfo | null>(null);
  const [products, setProducts] = useState<PromoProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedKeys, setSelectedKeys] = useState<number[]>([]);
  const [deciding, setDeciding] = useState(false);
  const [filter, setFilter] = useState('all');

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/promotions/${id}`);
      setPromo(res.data.promotion);
      setProducts(res.data.products || []);
    } catch {
      message.error('Ошибка загрузки акции');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  const updateDecisions = async (nmIds: number[], decision: string) => {
    setDeciding(true);
    try {
      await apiClient.post(`/promotions/${id}/decisions`, {
        nm_ids: nmIds,
        decision,
      });
      message.success(
        decision === 'enter'
          ? `${nmIds.length} товаров отмечены "Входим"`
          : `${nmIds.length} товаров отмечены "Пропуск"`
      );
      await fetchData();
      setSelectedKeys([]);
    } catch {
      message.error('Ошибка обновления решений');
    } finally {
      setDeciding(false);
    }
  };

  const handleEnterProfitable = () => {
    const nmIds = products
      .filter((p) => p.promo_margin_pct !== null && p.promo_margin_pct > 0)
      .map((p) => p.nm_id);
    if (!nmIds.length) {
      message.info('Нет выгодных товаров');
      return;
    }
    updateDecisions(nmIds, 'enter');
  };

  const handleSkipUnprofitable = () => {
    const nmIds = products
      .filter(
        (p) => p.promo_margin_pct === null || p.promo_margin_pct <= 0
      )
      .map((p) => p.nm_id);
    if (!nmIds.length) {
      message.info('Нет убыточных товаров');
      return;
    }
    updateDecisions(nmIds, 'skip');
  };

  const filteredProducts = products.filter((p) => {
    if (filter === 'profitable') return p.promo_margin_pct !== null && p.promo_margin_pct > 0;
    if (filter === 'unprofitable') return p.promo_margin_pct === null || p.promo_margin_pct <= 0;
    if (filter === 'in_action') return p.in_action;
    return true;
  });

  const columns: ColumnsType<PromoProduct> = [
    {
      title: 'Товар',
      key: 'group_product',
      children: [
        {
          title: 'Фото',
          dataIndex: 'image_url',
          key: 'image_url',
          width: 60,
          render: (url: string | null) =>
            url ? (
              <Image src={url} width={40} height={40} style={{ objectFit: 'cover', borderRadius: 4 }} preview={false} />
            ) : (
              <div style={{ width: 40, height: 40, background: '#f0f0f0', borderRadius: 4 }} />
            ),
        },
        {
          title: 'Артикул WB',
          dataIndex: 'nm_id',
          key: 'nm_id',
          width: 110,
        },
        {
          title: 'Название',
          dataIndex: 'title',
          key: 'title',
          width: 200,
          ellipsis: true,
          render: (t: string | null) => t || '—',
        },
      ],
    },
    {
      title: 'Цены',
      key: 'group_prices',
      children: [
        {
          title: 'Текущая',
          dataIndex: 'current_price',
          key: 'current_price',
          width: 90,
          align: 'right',
          render: (v: number | null) => (v !== null ? `${v} ₽` : '—'),
        },
        {
          title: 'Акц. цена',
          dataIndex: 'plan_price',
          key: 'plan_price',
          width: 100,
          align: 'right',
          render: (v: number | null) =>
            v !== null ? (
              <span style={{ background: '#fffbe6', padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                {v} ₽
              </span>
            ) : '—',
        },
        {
          title: 'Скидка',
          dataIndex: 'plan_discount',
          key: 'plan_discount',
          width: 70,
          align: 'right',
          render: (v: number | null) => (v !== null ? `${v}%` : '—'),
        },
      ],
    },
    {
      title: 'Маржа',
      key: 'group_margin',
      children: [
        {
          title: 'Тек. ₽',
          dataIndex: 'current_margin_rub',
          key: 'current_margin_rub',
          width: 80,
          align: 'right',
          render: (v: number | null) => (v !== null ? `${v}` : '—'),
        },
        {
          title: 'Тек. %',
          dataIndex: 'current_margin_pct',
          key: 'current_margin_pct',
          width: 70,
          align: 'right',
          render: (v: number | null) => (v !== null ? `${v}%` : '—'),
        },
        {
          title: 'Акц. ₽',
          dataIndex: 'promo_margin_rub',
          key: 'promo_margin_rub',
          width: 80,
          align: 'right',
          render: (v: number | null) => {
            if (v === null) return '—';
            return <span style={{ color: marginColor(v), fontWeight: 600 }}>{v}</span>;
          },
        },
        {
          title: 'Акц. %',
          dataIndex: 'promo_margin_pct',
          key: 'promo_margin_pct',
          width: 70,
          align: 'right',
          render: (v: number | null) => {
            if (v === null) return '—';
            return <span style={{ color: marginColor(v), fontWeight: 600 }}>{v}%</span>;
          },
        },
      ],
    },
    {
      title: 'Статус',
      key: 'group_status',
      children: [
        {
          title: 'В акции',
          dataIndex: 'in_action',
          key: 'in_action',
          width: 70,
          align: 'center',
          render: (v: boolean) =>
            v ? (
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#d9d9d9' }} />
            ),
        },
        {
          title: 'Решение',
          dataIndex: 'decision',
          key: 'decision',
          width: 90,
          align: 'center',
          render: (d: string) => {
            const info = decisionLabels[d] || { text: d, color: 'default' };
            return <Tag color={info.color}>{info.text}</Tag>;
          },
        },
      ],
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/promotions')}>
          Назад
        </Button>
      </Space>

      <Spin spinning={loading}>
        {promo && (
          <Card style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {promo.name}
              </Typography.Title>
              <Space size={16}>
                <Tag color={statusColors[promo.status || ''] || 'default'}>
                  {statusLabels[promo.status || ''] || promo.status}
                </Tag>
                <Typography.Text type="secondary">
                  {formatDate(promo.start_date)} — {formatDate(promo.end_date)}
                </Typography.Text>
                <Typography.Text type="secondary">
                  Товаров: {promo.products_count}
                </Typography.Text>
                {promo.avg_promo_margin !== null && (
                  <Typography.Text style={{ color: marginColor(promo.avg_promo_margin), fontWeight: 600 }}>
                    Ср. маржа акц.: {promo.avg_promo_margin.toFixed(1)}%
                  </Typography.Text>
                )}
                <Typography.Text type="secondary">
                  Выгодных: {promo.profitable_count} / {promo.products_count}
                </Typography.Text>
              </Space>
            </Space>
          </Card>
        )}

        <Space style={{ marginBottom: 12 }}>
          <Button
            type="primary"
            onClick={handleEnterProfitable}
            loading={deciding}
          >
            Войти выгодным
          </Button>
          <Button
            danger
            onClick={handleSkipUnprofitable}
            loading={deciding}
          >
            Пропустить убыточные
          </Button>
          {selectedKeys.length > 0 && (
            <>
              <Button
                onClick={() => updateDecisions(selectedKeys, 'enter')}
                loading={deciding}
              >
                Войти ({selectedKeys.length})
              </Button>
              <Button
                onClick={() => updateDecisions(selectedKeys, 'skip')}
                loading={deciding}
              >
                Пропустить ({selectedKeys.length})
              </Button>
            </>
          )}
        </Space>

        <Tabs
          activeKey={filter}
          onChange={setFilter}
          size="small"
          items={[
            { key: 'all', label: `Все (${products.length})` },
            {
              key: 'profitable',
              label: `Выгодные (${products.filter((p) => p.promo_margin_pct !== null && p.promo_margin_pct > 0).length})`,
            },
            {
              key: 'unprofitable',
              label: `Убыточные (${products.filter((p) => p.promo_margin_pct === null || p.promo_margin_pct <= 0).length})`,
            },
            {
              key: 'in_action',
              label: `В акции (${products.filter((p) => p.in_action).length})`,
            },
          ]}
        />

        <Table
          dataSource={filteredProducts}
          columns={columns as any[]}
          rowKey="nm_id"
          pagination={{ pageSize: 50, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
          size="small"
          bordered
          scroll={{ x: 1200 }}
          rowSelection={{
            selectedRowKeys: selectedKeys,
            onChange: (keys) => setSelectedKeys(keys as number[]),
          }}
        />
      </Spin>
    </div>
  );
}
