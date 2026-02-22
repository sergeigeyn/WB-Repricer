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
import { Line, Column as ColumnChart } from '@ant-design/charts';
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

// --- Helpers ---

function formatPrice(v: number): string {
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

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

  useEffect(() => {
    if (id) fetchAnalytics(days);
  }, [id, days]);

  if (!data && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Typography.Text type="secondary">Товар не найден</Typography.Text>
      </div>
    );
  }

  // --- Chart data: Orders bar chart ---
  const ordersChartData = (data?.daily_data || []).map((d) => ({
    date: formatDate(d.date),
    value: d.net_orders,
    type: 'Заказы',
  }));

  // --- Chart data: Price line (on same dates as orders) ---
  const priceLineData: { date: string; value: number; type: string }[] = [];
  for (const p of data?.price_history || []) {
    priceLineData.push({ date: formatDate(p.date), value: p.final_price, type: 'Цена' });
    if (p.spp_price) {
      priceLineData.push({ date: formatDate(p.date), value: p.spp_price, type: 'Цена с СПП' });
    }
  }

  // --- Chart: Orders by Price (Column) ---
  const ordersByPriceData = (data?.orders_by_price || []).map((b) => ({
    price: `${formatPrice(b.price)} ₽`,
    orders: b.orders_count,
  }));

  // --- Chart: Orders by Weekday (Column) ---
  const weekdayData = (data?.orders_by_weekday || []).map((w) => ({
    day: w.weekday_name,
    orders: w.avg_orders,
  }));

  const marginColor =
    data?.margin_pct == null
      ? undefined
      : data.margin_pct < 0
        ? '#cf1322'
        : data.margin_pct < 10
          ? '#fa8c16'
          : '#3f8600';

  // --- Chart data: Funnel ---
  const funnelLineData: { date: string; value: number; type: string }[] = [];
  for (const d of data?.funnel_data || []) {
    funnelLineData.push({ date: formatDate(d.date), value: d.views, type: 'Просмотры' });
    funnelLineData.push({ date: formatDate(d.date), value: d.cart, type: 'Корзина' });
    funnelLineData.push({ date: formatDate(d.date), value: d.orders, type: 'Заказы' });
    funnelLineData.push({ date: formatDate(d.date), value: d.buyouts, type: 'Выкупы' });
  }

  const conversionLineData: { date: string; value: number; type: string }[] = [];
  for (const d of data?.funnel_data || []) {
    if (d.cart_conversion !== null) conversionLineData.push({ date: formatDate(d.date), value: d.cart_conversion, type: 'В корзину %' });
    if (d.order_conversion !== null) conversionLineData.push({ date: formatDate(d.date), value: d.order_conversion, type: 'В заказ %' });
    if (d.buyout_pct !== null) conversionLineData.push({ date: formatDate(d.date), value: d.buyout_pct, type: 'Выкуп %' });
  }

  const tf = data?.totals_funnel;

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/products')}>
            Товары
          </Button>
          {data?.image_url && (
            <Image
              src={data.image_url}
              width={40}
              height={40}
              style={{ objectFit: 'cover', borderRadius: 6 }}
              preview={false}
            />
          )}
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {data?.title || `Товар #${id}`}
            </Typography.Title>
            <Typography.Text type="secondary">
              Артикул: {data?.nm_id}
            </Typography.Text>
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
              <Statistic
                title="Маржа"
                value={data?.margin_pct ?? 0}
                suffix="%"
                prefix={<DashboardOutlined />}
                valueStyle={{ color: marginColor }}
              />
              {data?.margin_rub != null && (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {data.margin_rub > 0 ? '+' : ''}{formatPrice(data.margin_rub)} ₽
                </Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small">
              <Statistic
                title="Скорость 7д"
                value={data?.sales_velocity_7d ?? 0}
                suffix="шт/день"
                prefix={<FieldTimeOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small">
              <Statistic
                title="Скорость 14д"
                value={data?.sales_velocity_14d ?? 0}
                suffix="шт/день"
                prefix={<FieldTimeOutlined />}
              />
              {data?.velocity_trend_pct != null && (
                <div style={{ marginTop: 4 }}>
                  {data.velocity_trend_pct >= 0 ? (
                    <Tag color="green" icon={<ArrowUpOutlined />}>+{data.velocity_trend_pct}%</Tag>
                  ) : (
                    <Tag color="red" icon={<ArrowDownOutlined />}>{data.velocity_trend_pct}%</Tag>
                  )}
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small">
              <Statistic
                title="Оборачиваемость"
                value={data?.turnover_days ?? 0}
                suffix="дней"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={5}>
            <Card size="small">
              <Statistic
                title="Остаток"
                value={data?.total_stock ?? 0}
                prefix={<InboxOutlined />}
                suffix="шт."
              />
            </Card>
          </Col>
        </Row>

        {/* Funnel metrics */}
        {tf && tf.views > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="Просмотры" value={tf.views} prefix={<EyeOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="В корзину" value={tf.cart} prefix={<ShoppingOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="Конв. в корзину" value={tf.avg_cart_conversion ?? 0} suffix="%" /></Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="Конв. в заказ" value={tf.avg_order_conversion ?? 0} suffix="%" /></Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="Выкуп" value={tf.avg_buyout_pct ?? 0} suffix="%" /></Card>
            </Col>
            <Col xs={24} sm={8} lg={4}>
              <Card size="small"><Statistic title="Выкупы ₽" value={tf.buyouts_sum_rub} formatter={(val) => formatPrice(Number(val))} suffix="₽" /></Card>
            </Col>
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

        {/* Main Chart: Orders */}
        <Card title="Заказы по дням" size="small" style={{ marginTop: 16 }}>
          {ordersChartData.length > 0 ? (
            <>
              <ColumnChart
                data={ordersChartData}
                xField="date"
                yField="value"
                style={{ fill: '#5B8FF9', fillOpacity: 0.85 }}
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

        {/* Second row: Price dynamics + Orders by price */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Динамика цен" size="small">
              {priceLineData.length > 0 ? (
                <>
                  <Line
                    data={priceLineData}
                    xField="date"
                    yField="value"
                    colorField="type"
                    style={{ lineWidth: 2 }}
                    axis={{ y: { title: '₽' } }}
                    scale={{ color: { range: ['#E8684A', '#5AD8A6'] } }}
                    height={260}
                  />
                </>
              ) : (
                <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
                  Нет данных о ценах
                </Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="Заказы по ценам" size="small">
              {ordersByPriceData.length > 0 ? (
                <>
                  <ColumnChart
                    data={ordersByPriceData}
                    xField="price"
                    yField="orders"
                    style={{ fill: '#5B8FF9' }}
                    axis={{ y: { title: 'Заказы' } }}
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

        {/* Third row: Weekday chart */}
        <Card title="Среднее количество заказов по дням недели" size="small" style={{ marginTop: 16 }}>
          {weekdayData.length > 0 ? (
            <>
              <ColumnChart
                data={weekdayData}
                xField="day"
                yField="orders"
                style={{ fill: '#5AD8A6' }}
                axis={{ y: { title: 'Ср. заказов' } }}
                height={220}
              />
            </>
          ) : (
            <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 48 }}>
              Нет данных
            </Typography.Text>
          )}
        </Card>
        {/* Funnel charts */}
        {funnelLineData.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={14}>
              <Card title="Воронка карточки" size="small">
                <>
                  <Line
                    data={funnelLineData}
                    xField="date"
                    yField="value"
                    colorField="type"
                    style={{ lineWidth: 2 }}
                    scale={{ color: { range: ['#8c8c8c', '#fa8c16', '#5B8FF9', '#5AD8A6'] } }}
                    axis={{ y: { title: 'Количество' } }}
                    height={260}
                  />
                </>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card title="Конверсии" size="small">
                {conversionLineData.length > 0 ? (
                  <>
                    <Line
                      data={conversionLineData}
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
                    Нет данных о конверсиях
                  </Typography.Text>
                )}
              </Card>
            </Col>
          </Row>
        )}
      </Spin>
    </div>
  );
}
