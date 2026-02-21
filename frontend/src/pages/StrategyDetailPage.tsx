import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Checkbox,
  Descriptions,
  Image,
  InputNumber,
  message,
  Modal,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import apiClient from '@/api/client';

// --- Interfaces ---

interface StrategyInfo {
  id: number;
  name: string;
  type: string;
  config_json: Record<string, any> | null;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  products_count: number;
  last_execution_at: string | null;
  last_execution_status: string | null;
}

interface AssignedProduct {
  id: number;
  nm_id: number;
  vendor_code: string | null;
  title: string | null;
  image_url: string | null;
  total_stock: number;
  current_price: number | null;
}

interface Recommendation {
  product_id: number;
  nm_id: number;
  vendor_code: string | null;
  title: string | null;
  image_url: string | null;
  total_stock: number;
  velocity_7d: number;
  days_remaining: number | null;
  current_price: number | null;
  recommended_price: number | null;
  price_change_pct: number | null;
  current_margin_pct: number | null;
  new_margin_pct: number | null;
  new_margin_rub: number | null;
  alert_level: string | null;
  reason: string | null;
  is_applied: boolean;
}

interface Execution {
  id: number;
  strategy_id: number;
  status: string;
  products_processed: number;
  recommendations_created: number;
  errors_count: number;
  executed_at: string;
  completed_at: string | null;
  triggered_by: string;
}

interface CatalogProduct {
  id: number;
  nm_id: number;
  vendor_code: string | null;
  title: string | null;
  image_url: string | null;
  total_stock: number;
}

// --- Constants ---

const strategyTypeLabels: Record<string, string> = {
  out_of_stock: 'Защита от out-of-stock',
  sales_velocity: 'По скорости продаж',
  promotion_booster: 'Акционный бустинг',
  competitor_following: 'Следование за конкурентом',
  target_margin: 'Целевая маржа',
  price_range: 'Диапазон цен',
  demand_reaction: 'Реакция на спрос',
  scheduled: 'По расписанию',
  locomotive: 'Товар-локомотив',
  ab_test: 'A/B тест',
};

const alertColors: Record<string, string> = {
  safe: 'green',
  warning: 'orange',
  critical: 'red',
};

const alertLabels: Record<string, string> = {
  safe: 'Норма',
  warning: 'Внимание',
  critical: 'Критично',
};

const configLabels: Record<string, string> = {
  threshold_days: 'Порог (дней)',
  critical_days: 'Критично (дней)',
  price_increase_pct: 'Повышение %',
  critical_increase_pct: 'Крит. повышение %',
  max_price_increase_pct: 'Макс повышение %',
  min_margin_pct: 'Мин маржа %',
  use_7d_velocity: 'Скорость за 7 дней',
  exclude_zero_stock: 'Исключать нулевые',
};

function formatDateTime(d: string | null): string {
  if (!d) return '—';
  return new Date(d).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function marginColor(v: number | null): string {
  if (v === null) return 'inherit';
  return v > 0 ? '#3f8600' : '#cf1322';
}

// --- Component ---

export default function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [strategy, setStrategy] = useState<StrategyInfo | null>(null);
  const [assignedProducts, setAssignedProducts] = useState<AssignedProduct[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [lastExecution, setLastExecution] = useState<Execution | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('products');

  // Add products modal
  const [addOpen, setAddOpen] = useState(false);
  const [catalog, setCatalog] = useState<CatalogProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>([]);

  // Edit config modal
  const [editConfigOpen, setEditConfigOpen] = useState(false);
  const [editConfig, setEditConfig] = useState<Record<string, any>>({});
  const [savingConfig, setSavingConfig] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/strategies/${id}`);
      const data = res.data;
      setStrategy(data.strategy);
      setAssignedProducts(data.assigned_products || []);
      setRecommendations(data.recommendations || []);
      setLastExecution(data.last_execution || null);
    } catch {
      message.error('Ошибка загрузки стратегии');
    } finally {
      setLoading(false);
    }
  };

  const fetchExecutions = async () => {
    try {
      const res = await apiClient.get(`/strategies/${id}/executions`);
      setExecutions(res.data || []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    if (id) {
      fetchData();
      fetchExecutions();
    }
  }, [id]);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await apiClient.post(`/strategies/${id}/run`);
      const data = res.data;
      message.success(
        `Выполнено: ${data.products_processed} товаров, ${data.recommendations_created} рекомендаций`
      );
      fetchData();
      fetchExecutions();
      setActiveTab('results');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Ошибка запуска');
    } finally {
      setRunning(false);
    }
  };

  // --- Add products ---

  const openAddProducts = async () => {
    setAddOpen(true);
    setCatalogLoading(true);
    try {
      const res = await apiClient.get('/products', { params: { limit: 500, in_stock: true } });
      const items = res.data.items || [];
      const existingIds = new Set(assignedProducts.map((p) => p.id));
      setCatalog(items.filter((p: any) => !existingIds.has(p.id)));
    } catch {
      message.error('Ошибка загрузки каталога');
    } finally {
      setCatalogLoading(false);
    }
  };

  const handleAddProducts = async () => {
    if (!selectedProductIds.length) {
      message.warning('Выберите товары');
      return;
    }
    try {
      const res = await apiClient.post(`/strategies/${id}/products`, {
        product_ids: selectedProductIds,
      });
      message.success(res.data.message);
      setAddOpen(false);
      setSelectedProductIds([]);
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleRemoveProducts = async (productIds: number[]) => {
    try {
      const res = await apiClient.delete(`/strategies/${id}/products`, {
        data: { product_ids: productIds },
      });
      message.success(res.data.message);
      fetchData();
    } catch {
      message.error('Ошибка отвязки');
    }
  };

  // --- Edit config ---

  const openEditConfig = () => {
    setEditConfig(strategy?.config_json || {});
    setEditConfigOpen(true);
  };

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await apiClient.put(`/strategies/${id}`, { config_json: editConfig });
      message.success('Конфигурация сохранена');
      setEditConfigOpen(false);
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSavingConfig(false);
    }
  };

  // --- Products tab columns ---

  const productColumns: ColumnsType<AssignedProduct> = [
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
    { title: 'Артикул WB', dataIndex: 'nm_id', key: 'nm_id', width: 120 },
    { title: 'Название', dataIndex: 'title', key: 'title', width: 250, ellipsis: true, render: (t: string | null) => t || '—' },
    { title: 'Остаток', dataIndex: 'total_stock', key: 'total_stock', width: 90, align: 'right' },
    {
      title: 'Цена',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 100,
      align: 'right',
      render: (v: number | null) => (v ? `${v} ₽` : '—'),
    },
    {
      title: '',
      key: 'actions',
      width: 80,
      render: (_, r) => (
        <Button type="link" danger size="small" onClick={() => handleRemoveProducts([r.id])}>
          Убрать
        </Button>
      ),
    },
  ];

  // --- Recommendations tab columns ---

  const recColumns: ColumnsType<Recommendation> = [
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
        { title: 'Артикул WB', dataIndex: 'nm_id', key: 'nm_id', width: 110 },
        { title: 'Название', dataIndex: 'title', key: 'title', width: 180, ellipsis: true, render: (t: string | null) => t || '—' },
      ],
    },
    {
      title: 'Остатки',
      key: 'group_stock',
      children: [
        { title: 'Остаток', dataIndex: 'total_stock', key: 'total_stock', width: 80, align: 'right' },
        {
          title: 'Скорость/д',
          dataIndex: 'velocity_7d',
          key: 'velocity_7d',
          width: 90,
          align: 'right',
          render: (v: number) => (v > 0 ? v.toFixed(1) : '—'),
        },
        {
          title: 'Дней ост.',
          dataIndex: 'days_remaining',
          key: 'days_remaining',
          width: 90,
          align: 'right',
          render: (v: number | null) => {
            if (v === null) return '—';
            const color = v < 3 ? '#cf1322' : v < 7 ? '#fa8c16' : '#3f8600';
            return <span style={{ color, fontWeight: 600 }}>{v.toFixed(1)}</span>;
          },
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
          render: (v: number | null) => (v ? `${v} ₽` : '—'),
        },
        {
          title: 'Рекоменд.',
          dataIndex: 'recommended_price',
          key: 'recommended_price',
          width: 100,
          align: 'right',
          render: (v: number | null) =>
            v ? (
              <span style={{ background: '#f6ffed', padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                {v} ₽
              </span>
            ) : '—',
        },
        {
          title: 'Изм. %',
          dataIndex: 'price_change_pct',
          key: 'price_change_pct',
          width: 70,
          align: 'right',
          render: (v: number | null) => (v ? `+${v}%` : '—'),
        },
      ],
    },
    {
      title: 'Маржа',
      key: 'group_margin',
      children: [
        {
          title: 'Тек. %',
          dataIndex: 'current_margin_pct',
          key: 'current_margin_pct',
          width: 70,
          align: 'right',
          render: (v: number | null) => (v !== null ? `${v}%` : '—'),
        },
        {
          title: 'Новая %',
          dataIndex: 'new_margin_pct',
          key: 'new_margin_pct',
          width: 80,
          align: 'right',
          render: (v: number | null) => {
            if (v === null) return '—';
            return <span style={{ color: marginColor(v), fontWeight: 600 }}>{v}%</span>;
          },
        },
        {
          title: 'Новая ₽',
          dataIndex: 'new_margin_rub',
          key: 'new_margin_rub',
          width: 80,
          align: 'right',
          render: (v: number | null) => {
            if (v === null) return '—';
            return <span style={{ color: marginColor(v), fontWeight: 600 }}>{v}</span>;
          },
        },
      ],
    },
    {
      title: 'Уровень',
      dataIndex: 'alert_level',
      key: 'alert_level',
      width: 100,
      align: 'center',
      render: (v: string | null) => {
        if (!v) return '—';
        return <Tag color={alertColors[v] || 'default'}>{alertLabels[v] || v}</Tag>;
      },
    },
  ];

  // --- Execution history columns ---

  const execColumns: ColumnsType<Execution> = [
    { title: 'Дата', dataIndex: 'executed_at', key: 'executed_at', width: 160, render: formatDateTime },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag color={s === 'completed' ? 'green' : s === 'failed' ? 'red' : 'processing'}>
          {s === 'completed' ? 'OK' : s === 'failed' ? 'Ошибка' : 'В работе'}
        </Tag>
      ),
    },
    { title: 'Товаров', dataIndex: 'products_processed', key: 'products_processed', width: 90, align: 'right' },
    { title: 'Рекоменд.', dataIndex: 'recommendations_created', key: 'recommendations_created', width: 100, align: 'right' },
    { title: 'Ошибок', dataIndex: 'errors_count', key: 'errors_count', width: 80, align: 'right' },
    {
      title: 'Триггер',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
      width: 100,
      render: (v: string) => (v === 'manual' ? 'Ручной' : 'Расписание'),
    },
  ];

  // --- Catalog columns (add products modal) ---

  const catalogColumns: ColumnsType<CatalogProduct> = [
    {
      title: 'Фото',
      dataIndex: 'image_url',
      key: 'image_url',
      width: 60,
      render: (url: string | null) =>
        url ? (
          <Image src={url} width={36} height={36} style={{ objectFit: 'cover', borderRadius: 4 }} preview={false} />
        ) : (
          <div style={{ width: 36, height: 36, background: '#f0f0f0', borderRadius: 4 }} />
        ),
    },
    { title: 'Артикул', dataIndex: 'nm_id', key: 'nm_id', width: 110 },
    { title: 'Название', dataIndex: 'title', key: 'title', ellipsis: true, render: (t: string | null) => t || '—' },
    { title: 'Остаток', dataIndex: 'total_stock', key: 'total_stock', width: 80, align: 'right' },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/strategies')}>
          Назад
        </Button>
      </Space>

      <Spin spinning={loading}>
        {strategy && (
          <Card style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {strategy.name}
                </Typography.Title>
                <Space>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={running}
                    onClick={handleRun}
                    disabled={!strategy.is_active}
                  >
                    Запустить
                  </Button>
                  <Button icon={<SettingOutlined />} onClick={openEditConfig}>
                    Настройки
                  </Button>
                </Space>
              </Space>
              <Space size={16}>
                <Tag color={strategy.is_active ? 'green' : 'default'}>
                  {strategy.is_active ? 'Активна' : 'Неактивна'}
                </Tag>
                <Typography.Text type="secondary">
                  Тип: {strategyTypeLabels[strategy.type] || strategy.type}
                </Typography.Text>
                <Typography.Text type="secondary">
                  Приоритет: {strategy.priority}
                </Typography.Text>
                <Typography.Text type="secondary">
                  Товаров: {strategy.products_count}
                </Typography.Text>
                {lastExecution && (
                  <Typography.Text type="secondary">
                    Посл. запуск: {formatDateTime(lastExecution.executed_at)}
                    {' '}({lastExecution.recommendations_created} рекоменд.)
                  </Typography.Text>
                )}
              </Space>
            </Space>
          </Card>
        )}

        <Tabs
          activeKey={activeTab}
          onChange={(key) => {
            setActiveTab(key);
            if (key === 'history' && !executions.length) fetchExecutions();
          }}
          items={[
            {
              key: 'products',
              label: `Товары (${assignedProducts.length})`,
              children: (
                <>
                  <Space style={{ marginBottom: 12 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={openAddProducts}>
                      Добавить товары
                    </Button>
                  </Space>
                  <Table
                    dataSource={assignedProducts}
                    columns={productColumns}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    bordered
                  />
                </>
              ),
            },
            {
              key: 'results',
              label: `Результаты (${recommendations.length})`,
              children: (
                <>
                  {lastExecution && (
                    <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                      Запуск: {formatDateTime(lastExecution.executed_at)} | Товаров: {lastExecution.products_processed} | Рекомендаций: {lastExecution.recommendations_created}
                    </Typography.Text>
                  )}
                  <Table
                    dataSource={recommendations}
                    columns={recColumns as any[]}
                    rowKey="product_id"
                    pagination={{ pageSize: 50, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
                    size="small"
                    bordered
                    scroll={{ x: 1300 }}
                  />
                </>
              ),
            },
            {
              key: 'config',
              label: 'Конфигурация',
              children: strategy?.config_json ? (
                <Descriptions bordered size="small" column={2}>
                  {Object.entries(strategy.config_json).map(([key, val]) => (
                    <Descriptions.Item key={key} label={configLabels[key] || key}>
                      {typeof val === 'boolean' ? (val ? 'Да' : 'Нет') : String(val)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              ) : (
                <Typography.Text type="secondary">Конфигурация по умолчанию</Typography.Text>
              ),
            },
            {
              key: 'history',
              label: 'История',
              children: (
                <Table
                  dataSource={executions}
                  columns={execColumns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  bordered
                />
              ),
            },
          ]}
        />
      </Spin>

      {/* Add products modal */}
      <Modal
        title="Добавить товары в стратегию"
        open={addOpen}
        onCancel={() => {
          setAddOpen(false);
          setSelectedProductIds([]);
        }}
        onOk={handleAddProducts}
        okText={`Добавить (${selectedProductIds.length})`}
        cancelText="Отмена"
        width={700}
      >
        <Spin spinning={catalogLoading}>
          <Table
            dataSource={catalog}
            columns={catalogColumns}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10 }}
            scroll={{ y: 400 }}
            rowSelection={{
              selectedRowKeys: selectedProductIds,
              onChange: (keys) => setSelectedProductIds(keys as number[]),
            }}
          />
        </Spin>
      </Modal>

      {/* Edit config modal */}
      <Modal
        title="Настройки стратегии"
        open={editConfigOpen}
        onCancel={() => setEditConfigOpen(false)}
        onOk={handleSaveConfig}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={savingConfig}
        width={480}
      >
        {strategy?.type === 'out_of_stock' && (
          <Space direction="vertical" style={{ width: '100%', marginTop: 16 }} size={12}>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Порог (дней):</Typography.Text>
              <InputNumber
                value={editConfig.threshold_days ?? 7}
                min={1} max={90}
                onChange={(v) => setEditConfig({ ...editConfig, threshold_days: v })}
              />
            </Space>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Критично (дней):</Typography.Text>
              <InputNumber
                value={editConfig.critical_days ?? 3}
                min={1} max={30}
                onChange={(v) => setEditConfig({ ...editConfig, critical_days: v })}
              />
            </Space>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Повышение %:</Typography.Text>
              <InputNumber
                value={editConfig.price_increase_pct ?? 15}
                min={1} max={100}
                onChange={(v) => setEditConfig({ ...editConfig, price_increase_pct: v })}
              />
            </Space>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Крит. повышение %:</Typography.Text>
              <InputNumber
                value={editConfig.critical_increase_pct ?? 30}
                min={1} max={100}
                onChange={(v) => setEditConfig({ ...editConfig, critical_increase_pct: v })}
              />
            </Space>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Макс повышение %:</Typography.Text>
              <InputNumber
                value={editConfig.max_price_increase_pct ?? 50}
                min={1} max={200}
                onChange={(v) => setEditConfig({ ...editConfig, max_price_increase_pct: v })}
              />
            </Space>
            <Space>
              <Typography.Text style={{ width: 160, display: 'inline-block' }}>Мин маржа %:</Typography.Text>
              <InputNumber
                value={editConfig.min_margin_pct ?? 5}
                min={0} max={100}
                onChange={(v) => setEditConfig({ ...editConfig, min_margin_pct: v })}
              />
            </Space>
            <Space>
              <Checkbox
                checked={editConfig.exclude_zero_stock ?? true}
                onChange={(e) => setEditConfig({ ...editConfig, exclude_zero_stock: e.target.checked })}
              >
                Исключать товары с нулевым остатком
              </Checkbox>
            </Space>
          </Space>
        )}
        {strategy?.type !== 'out_of_stock' && (
          <Typography.Text type="secondary">
            Настройка этого типа стратегии будет доступна позже.
          </Typography.Text>
        )}
      </Modal>
    </div>
  );
}
