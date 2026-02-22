import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Image,
  message,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Typography,
} from 'antd';
import {
  ShoppingCartOutlined,
  DollarOutlined,
  FundOutlined,
  EyeOutlined,
  ShoppingOutlined,
  ReloadOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Line, Column as ColumnChart } from '@ant-design/charts';
import apiClient from '@/api/client';

// --- Interfaces ---

interface DailyTrend {
  date: string;
  orders: number;
  revenue: number;
  profit: number;
}

interface DailyFunnel {
  date: string;
  views: number;
  cart: number;
  orders: number;
  buyouts: number;
  cart_conversion: number | null;
  order_conversion: number | null;
  buyout_pct: number | null;
}

interface TopProduct {
  product_id: number;
  nm_id: number;
  title: string | null;
  image_url: string | null;
  orders: number;
  revenue: number;
  share_pct: number;
}

interface WeekdayAvg {
  weekday: number;
  weekday_name: string;
  avg_orders: number;
  avg_revenue: number;
}

interface TotalsSummary {
  orders: number;
  revenue: number;
  profit: number;
  avg_check: number;
  views: number;
  cart: number;
  avg_cart_conversion: number | null;
  avg_order_conversion: number | null;
  avg_buyout_pct: number | null;
}

interface AnalyticsData {
  daily_trend: DailyTrend[];
  daily_funnel: DailyFunnel[];
  top_products: TopProduct[];
  weekday_avg: WeekdayAvg[];
  totals: TotalsSummary;
  period: string;
  account_id: number | null;
}

interface WBAccount {
  id: number;
  name: string;
  is_active: boolean;
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

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

// --- Component ---

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<string>('30d');
  const [accounts, setAccounts] = useState<WBAccount[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);

  const fetchAccounts = async () => {
    try {
      const res = await apiClient.get('/settings/wb-accounts');
      setAccounts(res.data.items || []);
    } catch {
      // silently ignore
    }
  };

  const fetchAnalytics = async (p: string, accId: number | null = accountId) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { period: p };
      if (accId !== null) params.account_id = accId;
      const res = await apiClient.get('/analytics/overview', { params });
      setData(res.data);
    } catch {
      message.error('Ошибка загрузки аналитики');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  useEffect(() => {
    fetchAnalytics(period, accountId);
  }, [period, accountId]);

  const totals = data?.totals;

  // --- Chart data: Orders & Revenue trend ---
  const ordersLineData = (data?.daily_trend || []).map((d) => ({
    date: formatDate(d.date),
    value: d.orders,
    type: 'Заказы',
  }));

  const revenueLineData = (data?.daily_trend || []).map((d) => ({
    date: formatDate(d.date),
    value: d.revenue,
    type: 'Выручка',
  }));

  const profitLineData = (data?.daily_trend || []).map((d) => ({
    date: formatDate(d.date),
    value: d.profit,
    type: 'Прибыль',
  }));

  const trendLineData = [...ordersLineData];

  // --- Chart data: Funnel ---
  const funnelLineData: { date: string; value: number; type: string }[] = [];
  for (const d of data?.daily_funnel || []) {
    funnelLineData.push({ date: formatDate(d.date), value: d.views, type: 'Просмотры' });
    funnelLineData.push({ date: formatDate(d.date), value: d.cart, type: 'Корзина' });
    funnelLineData.push({ date: formatDate(d.date), value: d.orders, type: 'Заказы' });
  }

  // --- Chart data: Conversions ---
  const convLineData: { date: string; value: number; type: string }[] = [];
  for (const d of data?.daily_funnel || []) {
    if (d.cart_conversion !== null) {
      convLineData.push({ date: formatDate(d.date), value: d.cart_conversion, type: 'В корзину %' });
    }
    if (d.order_conversion !== null) {
      convLineData.push({ date: formatDate(d.date), value: d.order_conversion, type: 'В заказ %' });
    }
    if (d.buyout_pct !== null) {
      convLineData.push({ date: formatDate(d.date), value: d.buyout_pct, type: 'Выкуп %' });
    }
  }

  // --- Chart data: Top products ---
  const topProductsData = (data?.top_products || []).map((p) => ({
    name: p.title ? (p.title.length > 30 ? p.title.slice(0, 30) + '…' : p.title) : `#${p.nm_id}`,
    orders: p.orders,
  }));

  // --- Chart data: Weekday ---
  const weekdayData = (data?.weekday_avg || []).map((w) => ({
    day: w.weekday_name,
    orders: w.avg_orders,
  }));

  // --- Top products table ---
  const topColumns: ColumnsType<TopProduct> = [
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
    { title: 'Артикул', dataIndex: 'nm_id', key: 'nm_id', width: 110 },
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
      title: 'Доля',
      dataIndex: 'share_pct',
      key: 'share_pct',
      width: 80,
      align: 'right',
      render: (v: number) => `${v}%`,
    },
  ];

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Typography.Title level={3} style={{ margin: 0 }}>Аналитика</Typography.Title>
          {accounts.length > 1 && (
            <Select
              value={accountId}
              onChange={(val) => setAccountId(val)}
              style={{ minWidth: 200 }}
              suffixIcon={<ShopOutlined />}
            >
              <Select.Option value={null}>Все кабинеты</Select.Option>
              {accounts.map((acc) => (
                <Select.Option key={acc.id} value={acc.id}>{acc.name}</Select.Option>
              ))}
            </Select>
          )}
        </Space>
        <Space>
          <Segmented
            options={[
              { label: '7д', value: '7d' },
              { label: '14д', value: '14d' },
              { label: '30д', value: '30d' },
              { label: '60д', value: '60d' },
            ]}
            value={period}
            onChange={(val) => setPeriod(val as string)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchAnalytics(period, accountId)} loading={loading} />
        </Space>
      </Space>

      <Spin spinning={loading}>
        {/* KPI Row 1: Orders, Revenue, Profit, Avg Check */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic
                title="Заказы"
                value={totals?.orders || 0}
                prefix={<ShoppingCartOutlined />}
                suffix="шт."
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic
                title="Выручка"
                value={totals?.revenue || 0}
                prefix={<DollarOutlined />}
                formatter={(val) => `${formatCompact(Number(val))} ₽`}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic
                title="Прибыль"
                value={totals?.profit || 0}
                formatter={(val) => `${formatCompact(Number(val))} ₽`}
                valueStyle={{ color: (totals?.profit || 0) >= 0 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic
                title="Средний чек"
                value={totals?.avg_check || 0}
                formatter={(val) => `${formatPrice(Number(val))} ₽`}
              />
            </Card>
          </Col>
        </Row>

        {/* KPI Row 2: Funnel metrics */}
        {(totals?.views || 0) > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small">
                <Statistic title="Просмотры" value={totals?.views || 0} prefix={<EyeOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small">
                <Statistic title="В корзину" value={totals?.cart || 0} prefix={<ShoppingOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small">
                <Statistic
                  title="Конв. в корзину"
                  value={totals?.avg_cart_conversion ?? 0}
                  suffix="%"
                  prefix={<FundOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small">
                <Statistic
                  title="Конв. в заказ"
                  value={totals?.avg_order_conversion ?? 0}
                  suffix="%"
                  prefix={<FundOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small">
                <Statistic
                  title="Выкуп"
                  value={totals?.avg_buyout_pct ?? 0}
                  suffix="%"
                  prefix={<FundOutlined />}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* Orders trend chart */}
        <Card title="Динамика заказов" size="small" style={{ marginTop: 16 }}>
          {trendLineData.length > 0 ? (
            <>
              <Line
                data={trendLineData}
                xField="date"
                yField="value"
                colorField="type"
                style={{ lineWidth: 2 }}
                axis={{ y: { title: 'Заказы' } }}
                height={280}
              />
            </>
          ) : (
            <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
              Нет данных за выбранный период
            </Typography.Text>
          )}
        </Card>

        {/* Revenue & Profit charts */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="Выручка по дням" size="small">
              {revenueLineData.length > 0 ? (
                <>
                  <Line
                    data={revenueLineData}
                    xField="date"
                    yField="value"
                    colorField="type"
                    style={{ lineWidth: 2 }}
                    scale={{ color: { range: ['#5B8FF9'] } }}
                    axis={{ y: { title: '₽' } }}
                    height={220}
                  />
                </>
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
                  Нет данных
                </Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Прибыль по дням" size="small">
              {profitLineData.length > 0 ? (
                <>
                  <Line
                    data={profitLineData}
                    xField="date"
                    yField="value"
                    colorField="type"
                    style={{ lineWidth: 2 }}
                    scale={{ color: { range: ['#3f8600'] } }}
                    axis={{ y: { title: '₽' } }}
                    height={220}
                  />
                </>
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
                  Нет данных
                </Typography.Text>
              )}
            </Card>
          </Col>
        </Row>

        {/* Funnel & Conversions charts */}
        {funnelLineData.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={14}>
              <Card title="Воронка по дням" size="small">
                <>
                  <Line
                    data={funnelLineData}
                    xField="date"
                    yField="value"
                    colorField="type"
                    style={{ lineWidth: 2 }}
                    scale={{ color: { range: ['#8c8c8c', '#fa8c16', '#5B8FF9'] } }}
                    axis={{ y: { title: 'Количество' } }}
                    height={260}
                  />
                </>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card title="Конверсии по дням" size="small">
                {convLineData.length > 0 ? (
                  <>
                    <Line
                      data={convLineData}
                      xField="date"
                      yField="value"
                      colorField="type"
                      style={{ lineWidth: 2 }}
                      scale={{ color: { range: ['#fa8c16', '#5B8FF9', '#5AD8A6'] } }}
                      axis={{ y: { title: '%' } }}
                      height={260}
                    />
                  </>
                ) : (
                  <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
                    Нет данных
                  </Typography.Text>
                )}
              </Card>
            </Col>
          </Row>
        )}

        {/* Top products & Weekday */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Топ товаров по заказам" size="small">
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
                  Нет данных о заказах
                </Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="Среднее заказов по дням недели" size="small">
              {weekdayData.length > 0 ? (
                <>
                  <ColumnChart
                    data={weekdayData}
                    xField="day"
                    yField="orders"
                    style={{ fill: '#5AD8A6' }}
                    axis={{ y: { title: 'Ср. заказов' } }}
                    height={260}
                  />
                </>
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
                  Нет данных
                </Typography.Text>
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}
