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
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
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

function fmtDate(d: string): string {
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

const EMPTY = (
  <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
    Нет данных
  </Typography.Text>
);

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

  useEffect(() => { fetchAccounts(); }, []);
  useEffect(() => { fetchAnalytics(period, accountId); }, [period, accountId]);

  const totals = data?.totals;

  // --- Chart data ---
  const trendData = (data?.daily_trend || []).map((d) => ({
    date: fmtDate(d.date),
    orders: d.orders,
    revenue: d.revenue,
    profit: d.profit,
  }));

  const funnelData = (data?.daily_funnel || []).map((d) => ({
    date: fmtDate(d.date),
    views: d.views,
    cart: d.cart,
    orders: d.orders,
  }));

  const convData = (data?.daily_funnel || []).map((d) => ({
    date: fmtDate(d.date),
    cart_conv: d.cart_conversion,
    order_conv: d.order_conversion,
    buyout_pct: d.buyout_pct,
  }));

  const weekdayData = (data?.weekday_avg || []).map((w) => ({
    day: w.weekday_name,
    orders: w.avg_orders,
  }));

  // --- Top products table ---
  const topColumns: ColumnsType<TopProduct> = [
    {
      title: 'Фото', dataIndex: 'image_url', key: 'image_url', width: 50,
      render: (url: string | null) =>
        url ? <Image src={url} width={36} height={36} style={{ objectFit: 'cover', borderRadius: 4 }} preview={false} />
          : <div style={{ width: 36, height: 36, background: '#f0f0f0', borderRadius: 4 }} />,
    },
    { title: 'Артикул', dataIndex: 'nm_id', key: 'nm_id', width: 110 },
    { title: 'Название', dataIndex: 'title', key: 'title', ellipsis: true, render: (t: string | null) => t || '—' },
    { title: 'Заказы', dataIndex: 'orders', key: 'orders', width: 80, align: 'right', render: (v: number) => v.toLocaleString('ru-RU') },
    { title: 'Выручка', dataIndex: 'revenue', key: 'revenue', width: 110, align: 'right', render: (v: number) => `${formatPrice(v)} ₽` },
    { title: 'Доля', dataIndex: 'share_pct', key: 'share_pct', width: 80, align: 'right', render: (v: number) => `${v}%` },
  ];

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Typography.Title level={3} style={{ margin: 0 }}>Аналитика</Typography.Title>
          {accounts.length > 1 && (
            <Select value={accountId} onChange={(val) => setAccountId(val)} style={{ minWidth: 200 }} suffixIcon={<ShopOutlined />}>
              <Select.Option value={null}>Все кабинеты</Select.Option>
              {accounts.map((acc) => <Select.Option key={acc.id} value={acc.id}>{acc.name}</Select.Option>)}
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
        {/* KPI Row 1 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small"><Statistic title="Заказы" value={totals?.orders || 0} prefix={<ShoppingCartOutlined />} suffix="шт." /></Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small"><Statistic title="Выручка" value={totals?.revenue || 0} prefix={<DollarOutlined />} formatter={(val) => `${formatCompact(Number(val))} ₽`} /></Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small"><Statistic title="Прибыль" value={totals?.profit || 0} formatter={(val) => `${formatCompact(Number(val))} ₽`} valueStyle={{ color: (totals?.profit || 0) >= 0 ? '#3f8600' : '#cf1322' }} /></Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small"><Statistic title="Средний чек" value={totals?.avg_check || 0} formatter={(val) => `${formatPrice(Number(val))} ₽`} /></Card>
          </Col>
        </Row>

        {/* KPI Row 2: Funnel metrics */}
        {(totals?.views || 0) > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Просмотры" value={totals?.views || 0} prefix={<EyeOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="В корзину" value={totals?.cart || 0} prefix={<ShoppingOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Конв. в корзину" value={totals?.avg_cart_conversion ?? 0} suffix="%" prefix={<FundOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Конв. в заказ" value={totals?.avg_order_conversion ?? 0} suffix="%" prefix={<FundOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Выкуп" value={totals?.avg_buyout_pct ?? 0} suffix="%" prefix={<FundOutlined />} /></Card></Col>
          </Row>
        )}

        {/* Orders trend */}
        <Card title="Динамика заказов" size="small" style={{ marginTop: 16 }}>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="orders" name="Заказы" stroke="#5B8FF9" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : EMPTY}
        </Card>

        {/* Revenue & Profit */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="Выручка по дням" size="small">
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} tickFormatter={(v) => formatCompact(v)} />
                    <Tooltip formatter={(v) => `${formatPrice(Number(v))} ₽`} />
                    <Line type="monotone" dataKey="revenue" name="Выручка" stroke="#5B8FF9" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : EMPTY}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Прибыль по дням" size="small">
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} tickFormatter={(v) => formatCompact(v)} />
                    <Tooltip formatter={(v) => `${formatPrice(Number(v))} ₽`} />
                    <Line type="monotone" dataKey="profit" name="Прибыль" stroke="#3f8600" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : EMPTY}
            </Card>
          </Col>
        </Row>

        {/* Funnel & Conversions */}
        {funnelData.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={14}>
              <Card title="Воронка по дням" size="small">
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={funnelData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="views" name="Просмотры" stroke="#8c8c8c" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="cart" name="Корзина" stroke="#fa8c16" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="orders" name="Заказы" stroke="#5B8FF9" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card title="Конверсии по дням" size="small">
                {convData.some((d) => d.cart_conv !== null) ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={convData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" fontSize={12} />
                      <YAxis fontSize={12} unit="%" />
                      <Tooltip formatter={(v) => `${v}%`} />
                      <Legend />
                      <Line type="monotone" dataKey="cart_conv" name="В корзину %" stroke="#fa8c16" strokeWidth={2} dot={false} connectNulls />
                      <Line type="monotone" dataKey="order_conv" name="В заказ %" stroke="#5B8FF9" strokeWidth={2} dot={false} connectNulls />
                      <Line type="monotone" dataKey="buyout_pct" name="Выкуп %" stroke="#5AD8A6" strokeWidth={2} dot={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                ) : EMPTY}
              </Card>
            </Col>
          </Row>
        )}

        {/* Top products & Weekday */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Топ товаров по заказам" size="small">
              {data?.top_products && data.top_products.length > 0 ? (
                <Table dataSource={data.top_products} columns={topColumns} rowKey="product_id" pagination={false} size="small" bordered />
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>Нет данных о заказах</Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="Среднее заказов по дням недели" size="small">
              {weekdayData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={weekdayData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" fontSize={12} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="orders" name="Ср. заказов" fill="#5AD8A6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : EMPTY}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}
