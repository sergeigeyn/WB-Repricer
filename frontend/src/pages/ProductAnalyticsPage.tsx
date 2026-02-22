import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Card,
  Col,
  Image,
  message,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DashboardOutlined,
  EyeOutlined,
  FieldTimeOutlined,
  InboxOutlined,
  ReloadOutlined,
  ShoppingOutlined,
} from '@ant-design/icons';
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

interface DailyDataPoint {
  date: string;
  orders: number;
  returns: number;
  net_orders: number;
  price: number | null;
  spp_price: number | null;
}

interface PricePoint {
  date: string;
  final_price: number;
  spp_pct: number | null;
  spp_price: number | null;
}

interface PromoInfo {
  promo_name: string;
  promo_price: number | null;
  start_date: string | null;
  end_date: string | null;
  promo_margin_pct: number | null;
}

interface PriceOrderBucket {
  price: number;
  spp_price: number | null;
  orders_count: number;
}

interface WeekdayOrders {
  weekday: number;
  weekday_name: string;
  avg_orders: number;
}

interface FunnelDataPoint {
  date: string;
  views: number;
  cart: number;
  orders: number;
  buyouts: number;
  cancels: number;
  wishlist: number;
  orders_sum_rub: number;
  buyouts_sum_rub: number;
  cart_conversion: number | null;
  order_conversion: number | null;
  buyout_pct: number | null;
}

interface FunnelTotals {
  views: number;
  cart: number;
  orders: number;
  buyouts: number;
  cancels: number;
  avg_cart_conversion: number | null;
  avg_order_conversion: number | null;
  avg_buyout_pct: number | null;
  orders_sum_rub: number;
  buyouts_sum_rub: number;
}

interface AnalyticsData {
  product_id: number;
  nm_id: number;
  title: string | null;
  image_url: string | null;
  margin_pct: number | null;
  margin_rub: number | null;
  total_stock: number;
  sales_velocity_7d: number;
  sales_velocity_14d: number;
  velocity_trend_pct: number | null;
  turnover_days: number | null;
  daily_data: DailyDataPoint[];
  price_history: PricePoint[];
  promo_prices: PromoInfo[];
  orders_by_price: PriceOrderBucket[];
  orders_by_weekday: WeekdayOrders[];
  funnel_data: FunnelDataPoint[];
  totals_funnel: FunnelTotals | null;
  days: number;
}

// --- Helpers ---

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

export default function ProductAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState<number>(30);

  const fetchAnalytics = async (d: number) => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/products/${id}/analytics`, { params: { days: d } });
      setData(res.data);
    } catch {
      message.error('Ошибка загрузки аналитики');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (id) fetchAnalytics(days); }, [id, days]);

  if (!data && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Typography.Text type="secondary">Товар не найден</Typography.Text>
      </div>
    );
  }

  // --- Chart data ---
  const ordersData = (data?.daily_data || []).map((d) => ({
    date: fmtDate(d.date),
    orders: d.net_orders,
  }));

  const priceData = (data?.price_history || []).map((p) => ({
    date: fmtDate(p.date),
    price: p.final_price,
    spp_price: p.spp_price,
  }));

  const ordersByPriceData = (data?.orders_by_price || []).map((b) => ({
    price: `${formatPrice(b.price)} ₽`,
    orders: b.orders_count,
  }));

  const weekdayData = (data?.orders_by_weekday || []).map((w) => ({
    day: w.weekday_name,
    orders: w.avg_orders,
  }));

  const funnelData = (data?.funnel_data || []).map((d) => ({
    date: fmtDate(d.date),
    views: d.views,
    cart: d.cart,
    orders: d.orders,
    buyouts: d.buyouts,
  }));

  const convData = (data?.funnel_data || []).map((d) => ({
    date: fmtDate(d.date),
    cart_conv: d.cart_conversion,
    order_conv: d.order_conversion,
    buyout_pct: d.buyout_pct,
  }));

  const marginColor =
    data?.margin_pct == null ? undefined
      : data.margin_pct < 0 ? '#cf1322'
        : data.margin_pct < 10 ? '#fa8c16' : '#3f8600';

  const tf = data?.totals_funnel;

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/products')}>Товары</Button>
          {data?.image_url && (
            <Image src={data.image_url} width={40} height={40} style={{ objectFit: 'cover', borderRadius: 6 }} preview={false} />
          )}
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>{data?.title || `Товар #${id}`}</Typography.Title>
            <Typography.Text type="secondary">Артикул: {data?.nm_id}</Typography.Text>
          </div>
        </Space>
        <Space>
          <Segmented
            options={[
              { label: '7д', value: 7 },
              { label: '14д', value: 14 },
              { label: '30д', value: 30 },
              { label: '60д', value: 60 },
            ]}
            value={days}
            onChange={(val) => setDays(val as number)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchAnalytics(days)} loading={loading} />
        </Space>
      </Space>

      <Spin spinning={loading}>
        {/* Metrics Row */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={4}>
            <Card size="small">
              <Statistic title="Маржа" value={data?.margin_pct ?? 0} suffix="%" prefix={<DashboardOutlined />} valueStyle={{ color: marginColor }} />
              {data?.margin_rub != null && (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>{data.margin_rub > 0 ? '+' : ''}{formatPrice(data.margin_rub)} ₽</Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small"><Statistic title="Скорость 7д" value={data?.sales_velocity_7d ?? 0} suffix="шт/день" prefix={<FieldTimeOutlined />} /></Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small">
              <Statistic title="Скорость 14д" value={data?.sales_velocity_14d ?? 0} suffix="шт/день" prefix={<FieldTimeOutlined />} />
              {data?.velocity_trend_pct != null && (
                <div style={{ marginTop: 4 }}>
                  {data.velocity_trend_pct >= 0
                    ? <Tag color="green" icon={<ArrowUpOutlined />}>+{data.velocity_trend_pct}%</Tag>
                    : <Tag color="red" icon={<ArrowDownOutlined />}>{data.velocity_trend_pct}%</Tag>}
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small"><Statistic title="Оборачиваемость" value={data?.turnover_days ?? 0} suffix="дней" /></Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small"><Statistic title="Остаток" value={data?.total_stock ?? 0} prefix={<InboxOutlined />} suffix="шт." /></Card>
          </Col>
        </Row>

        {/* Funnel metrics */}
        {tf && tf.views > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Просмотры" value={tf.views} prefix={<EyeOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="В корзину" value={tf.cart} prefix={<ShoppingOutlined />} /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Конв. в корзину" value={tf.avg_cart_conversion ?? 0} suffix="%" /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Конв. в заказ" value={tf.avg_order_conversion ?? 0} suffix="%" /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Выкуп" value={tf.avg_buyout_pct ?? 0} suffix="%" /></Card></Col>
            <Col xs={24} sm={8} lg={4}><Card size="small"><Statistic title="Выкупы ₽" value={tf.buyouts_sum_rub} formatter={(val) => formatPrice(Number(val))} suffix="₽" /></Card></Col>
          </Row>
        )}

        {/* Promotions */}
        {data?.promo_prices && data.promo_prices.length > 0 && (
          <Card size="small" title="Активные акции" style={{ marginTop: 16 }}>
            <Space wrap>
              {data.promo_prices.map((p, i) => (
                <Tag key={i} color={p.promo_margin_pct != null && p.promo_margin_pct >= 0 ? 'green' : 'red'}>
                  {p.promo_name}: {p.promo_price ? `${formatPrice(p.promo_price)} ₽` : '—'}
                  {p.promo_margin_pct != null && ` (маржа ${p.promo_margin_pct}%)`}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        {/* Orders bar chart */}
        <Card title="Заказы по дням" size="small" style={{ marginTop: 16 }}>
          {ordersData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={ordersData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="orders" name="Заказы" fill="#5B8FF9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : EMPTY}
        </Card>

        {/* Price dynamics + Orders by price */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Динамика цен" size="small">
              {priceData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={priceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} />
                    <Tooltip formatter={(v) => `${formatPrice(Number(v))} ₽`} />
                    <Legend />
                    <Line type="monotone" dataKey="price" name="Цена" stroke="#E8684A" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="spp_price" name="Цена с СПП" stroke="#5AD8A6" strokeWidth={2} dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              ) : EMPTY}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="Заказы по ценам" size="small">
              {ordersByPriceData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={ordersByPriceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="price" fontSize={11} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="orders" name="Заказы" fill="#5B8FF9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : EMPTY}
            </Card>
          </Col>
        </Row>

        {/* Weekday chart */}
        <Card title="Среднее количество заказов по дням недели" size="small" style={{ marginTop: 16 }}>
          {weekdayData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
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

        {/* Funnel charts */}
        {funnelData.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={14}>
              <Card title="Воронка карточки" size="small">
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
                    <Line type="monotone" dataKey="buyouts" name="Выкупы" stroke="#5AD8A6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card title="Конверсии" size="small">
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
      </Spin>
    </div>
  );
}
