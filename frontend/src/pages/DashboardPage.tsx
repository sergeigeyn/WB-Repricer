import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Col,
  Image,
  List,
  message,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  Button,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DollarOutlined,
  ShoppingCartOutlined,
  FundOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  InboxOutlined,
  ReloadOutlined,
  TagOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import apiClient from '@/api/client';

// --- Interfaces ---

interface DashboardKPI {
  total_orders: number;
  total_revenue: number;
  total_profit: number;
  avg_margin_pct: number | null;
  orders_change_pct: number | null;
  revenue_change_pct: number | null;
  profit_change_pct: number | null;
  active_products: number;
  total_products: number;
  total_stock: number;
  price_changes_today: number;
}

interface DashboardAlert {
  type: string;
  severity: string;
  product_id: number;
  nm_id: number;
  title: string | null;
  image_url: string | null;
  value: number | null;
  detail: string | null;
}

interface DashboardPromotion {
  id: number;
  name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  in_action_count: number;
  total_available: number;
  avg_promo_margin: number | null;
  profitable_count: number;
}

interface DashboardTopProduct {
  product_id: number;
  nm_id: number;
  title: string | null;
  image_url: string | null;
  orders: number;
  revenue: number;
  margin_pct: number | null;
  margin_rub: number | null;
}

interface DashboardData {
  kpi: DashboardKPI;
  alerts: DashboardAlert[];
  active_promotions: DashboardPromotion[];
  top_products: DashboardTopProduct[];
  products_without_strategy: number;
  products_without_cost: number;
  period: string;
}

// --- Helpers ---

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toFixed(0);
}

function formatPrice(v: number): string {
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

function formatDate(d: string | null): string {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

const periodLabels: Record<string, string> = {
  today: 'Вчера',
  '7d': '7 дней',
  '30d': '30 дней',
};

// --- Component ---

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<string>('7d');

  const fetchDashboard = async (p: string) => {
    setLoading(true);
    try {
      const res = await apiClient.get('/dashboard', { params: { period: p } });
      setData(res.data);
    } catch {
      message.error('Ошибка загрузки дашборда');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard(period);
  }, [period]);

  const handlePeriodChange = (val: string | number) => {
    setPeriod(val as string);
  };

  // --- Top products table ---
  const topColumns: ColumnsType<DashboardTopProduct> = [
    {
      title: 'Фото',
      dataIndex: 'image_url',
      key: 'image_url',
      width: 50,
      render: (url: string | null) =>
        url ? (
          <Image src={url} width={36} height={36} style={{ objectFit: 'cover', borderRadius: 4 }} preview={false} />
        ) : (
          <div style={{ width: 36, height: 36, background: '#f0f0f0', borderRadius: 4 }} />
        ),
    },
    {
      title: 'Артикул',
      dataIndex: 'nm_id',
      key: 'nm_id',
      width: 110,
    },
    {
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (t: string | null) => t || '—',
    },
    {
      title: 'Заказы',
      dataIndex: 'orders',
      key: 'orders',
      width: 80,
      align: 'right',
      render: (v: number) => v.toLocaleString('ru-RU'),
    },
    {
      title: 'Выручка',
      dataIndex: 'revenue',
      key: 'revenue',
      width: 110,
      align: 'right',
      render: (v: number) => `${formatPrice(v)} ₽`,
    },
    {
      title: 'Маржа',
      dataIndex: 'margin_pct',
      key: 'margin_pct',
      width: 90,
      align: 'right',
      render: (v: number | null) => {
        if (v === null) return '—';
        const color = v < 0 ? '#cf1322' : v < 10 ? '#fa8c16' : '#3f8600';
        return <span style={{ color, fontWeight: 600 }}>{v}%</span>;
      },
    },
  ];

  const kpi = data?.kpi;

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Дашборд</Typography.Title>
        <Space>
          <Segmented
            options={[
              { label: 'Вчера', value: 'today' },
              { label: '7 дней', value: '7d' },
              { label: '30 дней', value: '30d' },
            ]}
            value={period}
            onChange={handlePeriodChange}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchDashboard(period)} loading={loading}>
            Обновить
          </Button>
        </Space>
      </Space>

      <Spin spinning={loading}>
        {/* KPI Row */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={`Заказы за ${periodLabels[period] || period}`}
                value={kpi?.total_orders || 0}
                prefix={<ShoppingCartOutlined />}
                suffix="шт."
              />
              {kpi?.orders_change_pct !== null && kpi?.orders_change_pct !== undefined && (
                <div style={{ marginTop: 4 }}>
                  {kpi.orders_change_pct >= 0 ? (
                    <Tag color="green" icon={<ArrowUpOutlined />}>+{kpi.orders_change_pct}%</Tag>
                  ) : (
                    <Tag color="red" icon={<ArrowDownOutlined />}>{kpi.orders_change_pct}%</Tag>
                  )}
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Выручка"
                value={kpi?.total_revenue || 0}
                prefix={<DollarOutlined />}
                formatter={(val) => `${formatCompact(Number(val))} ₽`}
              />
              {kpi?.revenue_change_pct !== null && kpi?.revenue_change_pct !== undefined && (
                <div style={{ marginTop: 4 }}>
                  {kpi.revenue_change_pct >= 0 ? (
                    <Tag color="green" icon={<ArrowUpOutlined />}>+{kpi.revenue_change_pct}%</Tag>
                  ) : (
                    <Tag color="red" icon={<ArrowDownOutlined />}>{kpi.revenue_change_pct}%</Tag>
                  )}
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Прибыль"
                value={kpi?.total_profit || 0}
                formatter={(val) => `${formatCompact(Number(val))} ₽`}
                valueStyle={{ color: (kpi?.total_profit || 0) >= 0 ? '#3f8600' : '#cf1322' }}
              />
              {kpi?.profit_change_pct !== null && kpi?.profit_change_pct !== undefined && (
                <div style={{ marginTop: 4 }}>
                  {kpi.profit_change_pct >= 0 ? (
                    <Tag color="green" icon={<ArrowUpOutlined />}>+{kpi.profit_change_pct}%</Tag>
                  ) : (
                    <Tag color="red" icon={<ArrowDownOutlined />}>{kpi.profit_change_pct}%</Tag>
                  )}
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Средняя маржа"
                value={kpi?.avg_margin_pct ?? 0}
                suffix="%"
                prefix={<FundOutlined />}
                valueStyle={{
                  color: (kpi?.avg_margin_pct ?? 0) < 0
                    ? '#cf1322'
                    : (kpi?.avg_margin_pct ?? 0) < 10
                      ? '#fa8c16'
                      : '#3f8600',
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* Operational KPI Row */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Statistic
                title="Общий остаток"
                value={kpi?.total_stock || 0}
                prefix={<InboxOutlined />}
                suffix="шт."
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Statistic
                title="Товаров в наличии"
                value={kpi?.active_products || 0}
                prefix={<AppstoreOutlined />}
                suffix={`/ ${kpi?.total_products || 0}`}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Statistic
                title="Изменений цен сегодня"
                value={kpi?.price_changes_today || 0}
                prefix={<TagOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* Alerts + Promotions */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* Left: Alerts */}
          <Col xs={24} lg={14}>
            <Card
              title="Требуют внимания"
              size="small"
              extra={
                <Space>
                  {(data?.products_without_cost || 0) > 0 && (
                    <Tag
                      color="blue"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate('/products')}
                    >
                      Без себестоимости: {data?.products_without_cost}
                    </Tag>
                  )}
                  {(data?.products_without_strategy || 0) > 0 && (
                    <Tag
                      color="orange"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate('/strategies')}
                    >
                      Без стратегии: {data?.products_without_strategy}
                    </Tag>
                  )}
                </Space>
              }
            >
              {data?.alerts && data.alerts.length > 0 ? (
                <List
                  size="small"
                  dataSource={data.alerts}
                  renderItem={(alert) => (
                    <List.Item
                      style={{ cursor: 'pointer', padding: '6px 0' }}
                      onClick={() => navigate('/products')}
                    >
                      <Space>
                        {alert.severity === 'critical' ? (
                          <ExclamationCircleOutlined style={{ color: '#cf1322', fontSize: 16 }} />
                        ) : alert.severity === 'warning' ? (
                          <WarningOutlined style={{ color: '#fa8c16', fontSize: 16 }} />
                        ) : (
                          <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 16 }} />
                        )}
                        {alert.image_url && (
                          <Image
                            src={alert.image_url}
                            width={28}
                            height={28}
                            style={{ objectFit: 'cover', borderRadius: 4 }}
                            preview={false}
                          />
                        )}
                        <Typography.Text ellipsis style={{ maxWidth: 200 }}>
                          {alert.title || `#${alert.nm_id}`}
                        </Typography.Text>
                        <Tag color={alert.severity === 'critical' ? 'red' : 'orange'}>
                          {alert.detail}
                        </Tag>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
                  Проблемных товаров нет
                </Typography.Text>
              )}
            </Card>
          </Col>

          {/* Right: Active promotions */}
          <Col xs={24} lg={10}>
            <Card title="Активные акции" size="small">
              {data?.active_promotions && data.active_promotions.length > 0 ? (
                <List
                  size="small"
                  dataSource={data.active_promotions}
                  renderItem={(promo) => (
                    <List.Item
                      style={{ cursor: 'pointer', padding: '8px 0' }}
                      onClick={() => navigate(`/promotions/${promo.id}`)}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <span>{promo.name}</span>
                            <Tag color={promo.status === 'active' ? 'green' : 'blue'}>
                              {promo.status === 'active' ? 'Идёт' : 'Скоро'}
                            </Tag>
                          </Space>
                        }
                        description={
                          <Space split="·">
                            <span>{formatDate(promo.start_date)} — {formatDate(promo.end_date)}</span>
                            <span>{promo.in_action_count}/{promo.total_available} товаров</span>
                            {promo.avg_promo_margin !== null && (
                              <span style={{ color: promo.avg_promo_margin >= 0 ? '#3f8600' : '#cf1322' }}>
                                маржа {promo.avg_promo_margin}%
                              </span>
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
                  Нет активных акций
                </Typography.Text>
              )}
            </Card>
          </Col>
        </Row>

        {/* Top Products */}
        <Card title={`Топ товаров по заказам за ${periodLabels[period] || period}`} size="small" style={{ marginTop: 16 }}>
          {data?.top_products && data.top_products.length > 0 ? (
            <Table
              dataSource={data.top_products}
              columns={topColumns}
              rowKey="product_id"
              pagination={false}
              size="small"
              bordered
            />
          ) : (
            <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
              Нет данных о заказах за выбранный период
            </Typography.Text>
          )}
        </Card>
      </Spin>
    </div>
  );
}
