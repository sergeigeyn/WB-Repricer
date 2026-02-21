import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlusOutlined, PlayCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import apiClient from '@/api/client';

interface Strategy {
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

const execStatusColors: Record<string, string> = {
  completed: 'green',
  running: 'processing',
  failed: 'red',
};

function formatDateTime(d: string | null): string {
  if (!d) return '—';
  return new Date(d).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function StrategiesPage() {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [selectedType, setSelectedType] = useState<string>('out_of_stock');

  const fetchStrategies = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/strategies');
      setStrategies(res.data.items || []);
    } catch {
      message.error('Ошибка загрузки стратегий');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);

      const configFields: Record<string, any> = {};
      if (values.type === 'out_of_stock') {
        if (values.threshold_days !== undefined) configFields.threshold_days = values.threshold_days;
        if (values.critical_days !== undefined) configFields.critical_days = values.critical_days;
        if (values.price_increase_pct !== undefined) configFields.price_increase_pct = values.price_increase_pct;
        if (values.critical_increase_pct !== undefined) configFields.critical_increase_pct = values.critical_increase_pct;
        if (values.max_price_increase_pct !== undefined) configFields.max_price_increase_pct = values.max_price_increase_pct;
        if (values.min_margin_pct !== undefined) configFields.min_margin_pct = values.min_margin_pct;
      }

      await apiClient.post('/strategies', {
        name: values.name,
        type: values.type,
        priority: values.priority || 5,
        config_json: Object.keys(configFields).length > 0 ? configFields : null,
      });

      message.success('Стратегия создана');
      setCreateOpen(false);
      form.resetFields();
      fetchStrategies();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Ошибка создания');
    } finally {
      setCreating(false);
    }
  };

  const handleRun = async (id: number) => {
    setRunningId(id);
    try {
      const res = await apiClient.post(`/strategies/${id}/run`);
      const data = res.data;
      message.success(
        `Выполнено: ${data.products_processed} товаров, ${data.recommendations_created} рекомендаций`
      );
      fetchStrategies();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Ошибка запуска');
    } finally {
      setRunningId(null);
    }
  };

  const columns: ColumnsType<Strategy> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      ellipsis: true,
      render: (name: string, record) => (
        <a onClick={() => navigate(`/strategies/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      width: 200,
      render: (t: string) => strategyTypeLabels[t] || t,
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      align: 'center',
    },
    {
      title: 'Товаров',
      dataIndex: 'products_count',
      key: 'products_count',
      width: 90,
      align: 'right',
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>{active ? 'Активна' : 'Неактивна'}</Tag>
      ),
    },
    {
      title: 'Последний запуск',
      key: 'last_exec',
      width: 180,
      render: (_, r) => {
        if (!r.last_execution_at) return '—';
        return (
          <Space size={4}>
            <span>{formatDateTime(r.last_execution_at)}</span>
            <Tag color={execStatusColors[r.last_execution_status || ''] || 'default'}>
              {r.last_execution_status === 'completed' ? 'OK' : r.last_execution_status}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_, r) => (
        <Button
          type="link"
          icon={<PlayCircleOutlined />}
          loading={runningId === r.id}
          onClick={() => handleRun(r.id)}
          disabled={!r.is_active}
        >
          Запустить
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Стратегии</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Создать стратегию
        </Button>
      </Space>

      <Spin spinning={loading}>
        <Table
          dataSource={strategies}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="middle"
          bordered
          scroll={{ x: 1100 }}
        />
      </Spin>

      <Modal
        title="Создать стратегию"
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        okText="Создать"
        cancelText="Отмена"
        confirmLoading={creating}
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}
          initialValues={{ type: 'out_of_stock', priority: 5 }}
        >
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название стратегии' }]}
          >
            <Input placeholder="Например: Защита от out-of-stock (основная)" />
          </Form.Item>

          <Form.Item name="type" label="Тип стратегии" rules={[{ required: true }]}>
            <Select onChange={(v) => setSelectedType(v)}>
              {Object.entries(strategyTypeLabels).map(([key, label]) => (
                <Select.Option key={key} value={key}>{label}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="priority" label="Приоритет (1 — высший)">
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>

          {selectedType === 'out_of_stock' && (
            <>
              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                Параметры защиты от out-of-stock
              </Typography.Text>
              <Space wrap style={{ width: '100%' }}>
                <Form.Item name="threshold_days" label="Порог (дней)" initialValue={7}>
                  <InputNumber min={1} max={90} />
                </Form.Item>
                <Form.Item name="critical_days" label="Критично (дней)" initialValue={3}>
                  <InputNumber min={1} max={30} />
                </Form.Item>
                <Form.Item name="price_increase_pct" label="Повышение %" initialValue={15}>
                  <InputNumber min={1} max={100} />
                </Form.Item>
                <Form.Item name="critical_increase_pct" label="Крит. повышение %" initialValue={30}>
                  <InputNumber min={1} max={100} />
                </Form.Item>
                <Form.Item name="max_price_increase_pct" label="Макс повышение %" initialValue={50}>
                  <InputNumber min={1} max={200} />
                </Form.Item>
                <Form.Item name="min_margin_pct" label="Мин маржа %" initialValue={5}>
                  <InputNumber min={0} max={100} />
                </Form.Item>
              </Space>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
}
