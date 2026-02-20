import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  Typography,
  message,
  Table,
  Tag,
  Space,
  Popconfirm,
  Alert,
  Spin,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import apiClient from '@/api/client';

interface WBAccount {
  id: number;
  name: string;
  api_key_masked: string;
  is_active: boolean;
  permissions: string[] | null;
  tax_rate: number | null;
  tariff_rate: number | null;
  created_at: string;
}

interface ValidationResult {
  valid: boolean;
  permissions: string[];
  error: string | null;
}

const PERMISSION_LABELS: Record<string, { label: string; color: string }> = {
  content: { label: 'Контент', color: 'blue' },
  prices: { label: 'Цены и скидки', color: 'green' },
  statistics: { label: 'Статистика', color: 'purple' },
  analytics: { label: 'Аналитика', color: 'orange' },
  marketplace: { label: 'Маркетплейс', color: 'cyan' },
  advert: { label: 'Продвижение', color: 'red' },
  feedbacks: { label: 'Отзывы', color: 'gold' },
  questions: { label: 'Вопросы', color: 'lime' },
  recommendations: { label: 'Рекомендации', color: 'geekblue' },
  returns: { label: 'Возвраты', color: 'volcano' },
};

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<WBAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get('/settings/wb-accounts');
      setAccounts(data.items);
    } catch {
      message.error('Не удалось загрузить аккаунты');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleValidate = async () => {
    const values = await form.validateFields();
    setValidating(true);
    setValidation(null);
    try {
      const { data } = await apiClient.post('/settings/wb-accounts/validate-key', {
        name: values.name,
        api_key: values.api_key,
      });
      setValidation(data);
    } catch {
      message.error('Ошибка проверки ключа');
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post('/settings/wb-accounts', {
        name: values.name,
        api_key: values.api_key,
      });
      message.success('WB аккаунт добавлен');
      form.resetFields();
      setValidation(null);
      fetchAccounts();
    } catch {
      message.error('Не удалось сохранить аккаунт');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.delete(`/settings/wb-accounts/${id}`);
      message.success('Аккаунт удалён');
      fetchAccounts();
    } catch {
      message.error('Не удалось удалить аккаунт');
    }
  };

  const handleUpdateAccount = async (id: number, field: 'tax_rate' | 'tariff_rate', value: number | null) => {
    try {
      await apiClient.patch(`/settings/wb-accounts/${id}`, { [field]: value });
      setAccounts((prev) =>
        prev.map((acc) => (acc.id === id ? { ...acc, [field]: value } : acc))
      );
      message.success('Сохранено');
    } catch {
      message.error('Ошибка сохранения');
    }
  };

  const handleCheckPermissions = async (id: number) => {
    setCheckingId(id);
    try {
      const { data } = await apiClient.post(`/settings/wb-accounts/${id}/check-permissions`);
      setAccounts((prev) =>
        prev.map((acc) =>
          acc.id === id ? { ...acc, permissions: data.permissions } : acc
        )
      );
      if (data.valid) {
        message.success(`Ключ валиден, ${data.permissions.length} разрешений`);
      } else {
        message.warning(data.error || 'Ключ невалиден');
      }
    } catch {
      message.error('Ошибка проверки');
    } finally {
      setCheckingId(null);
    }
  };

  const columns = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'API ключ',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'Налог %',
      dataIndex: 'tax_rate',
      key: 'tax_rate',
      width: 110,
      render: (_: unknown, record: WBAccount) => (
        <InputNumber
          size="small"
          min={0}
          max={50}
          step={0.1}
          placeholder="0"
          value={record.tax_rate}
          onBlur={(e) => {
            const val = e.target.value ? parseFloat(e.target.value) : null;
            if (val !== record.tax_rate) handleUpdateAccount(record.id, 'tax_rate', val);
          }}
          onPressEnter={(e) => {
            const val = (e.target as HTMLInputElement).value ? parseFloat((e.target as HTMLInputElement).value) : null;
            if (val !== record.tax_rate) handleUpdateAccount(record.id, 'tax_rate', val);
          }}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: 'Конструктор %',
      dataIndex: 'tariff_rate',
      key: 'tariff_rate',
      width: 130,
      render: (_: unknown, record: WBAccount) => (
        <InputNumber
          size="small"
          min={0}
          max={50}
          step={0.1}
          placeholder="0"
          value={record.tariff_rate}
          onBlur={(e) => {
            const val = e.target.value ? parseFloat(e.target.value) : null;
            if (val !== record.tariff_rate) handleUpdateAccount(record.id, 'tariff_rate', val);
          }}
          onPressEnter={(e) => {
            const val = (e.target as HTMLInputElement).value ? parseFloat((e.target as HTMLInputElement).value) : null;
            if (val !== record.tariff_rate) handleUpdateAccount(record.id, 'tariff_rate', val);
          }}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: 'Разрешения',
      key: 'permissions',
      render: (_: unknown, record: WBAccount) => (
        <Space wrap>
          {record.permissions
            ? record.permissions.map((p) => (
                <Tag color={PERMISSION_LABELS[p]?.color || 'default'} key={p}>
                  {PERMISSION_LABELS[p]?.label || p}
                </Tag>
              ))
            : <Typography.Text type="secondary">Не проверено</Typography.Text>}
        </Space>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: WBAccount) => (
        <Space>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={checkingId === record.id}
            onClick={() => handleCheckPermissions(record.id)}
          >
            Проверить
          </Button>
          <Popconfirm
            title="Удалить аккаунт?"
            description="API ключ будет удалён безвозвратно"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={3}>Настройки</Typography.Title>

      <Card title="WB API Аккаунты" style={{ marginBottom: 24 }}>
        <Spin spinning={loading}>
          {accounts.length === 0 && !loading ? (
            <Alert
              message="Нет подключённых аккаунтов"
              description="Добавьте WB API ключ ниже, чтобы начать работу с данными"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Table
              columns={columns}
              dataSource={accounts}
              rowKey="id"
              pagination={false}
              size="middle"
              style={{ marginBottom: 16 }}
            />
          )}
        </Spin>
      </Card>

      <Card title="Добавить WB API ключ">
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item
            name="name"
            label="Название аккаунта"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input placeholder="Например: Основной кабинет" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API ключ"
            rules={[{ required: true, message: 'Введите API ключ' }]}
            extra="Ключ хранится в зашифрованном виде (AES-256)"
          >
            <Input.TextArea
              rows={3}
              placeholder="Вставьте API ключ из личного кабинета WB"
            />
          </Form.Item>

          {validation && (
            <div style={{ marginBottom: 16 }}>
              {validation.valid ? (
                <Alert
                  message="Ключ валиден"
                  description={
                    <Space wrap>
                      Доступные API:{' '}
                      {validation.permissions.map((p) => (
                        <Tag color={PERMISSION_LABELS[p]?.color || 'default'} key={p}>
                          {PERMISSION_LABELS[p]?.label || p}
                        </Tag>
                      ))}
                    </Space>
                  }
                  type="success"
                  showIcon
                  icon={<CheckCircleOutlined />}
                />
              ) : (
                <Alert
                  message="Ключ невалиден"
                  description={validation.error}
                  type="error"
                  showIcon
                  icon={<CloseCircleOutlined />}
                />
              )}
            </div>
          )}

          <Form.Item>
            <Space>
              <Button onClick={handleValidate} loading={validating}>
                Проверить ключ
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleSave}
                loading={saving}
                disabled={validation !== null && !validation.valid}
              >
                Сохранить
              </Button>
            </Space>
          </Form.Item>
        </Form>

        <Divider />

        <Typography.Paragraph type="secondary">
          <Typography.Text strong>Как получить API ключ:</Typography.Text>
          <br />
          1. Зайдите в личный кабинет WB Seller → Настройки → Доступ к API
          <br />
          2. Создайте новый токен с нужными правами (Контент, Цены, Статистика, Аналитика, Маркетплейс)
          <br />
          3. Скопируйте токен и вставьте в поле выше
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
