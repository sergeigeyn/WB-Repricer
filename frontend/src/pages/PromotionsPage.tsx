import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  DatePicker,
  Form,
  Input,
  message,
  Modal,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'antd';
import { PlusOutlined, UploadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload';
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
  import: 'Импорт',
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
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();

  const fetchPromotions = async (status?: string) => {
    setLoading(true);
    try {
      const params = status && status !== 'all' ? { status } : {};
      const res = await apiClient.get('/promotions', { params });
      setPromotions(res.data.items || []);
    } catch {
      message.error('Ошибка загрузки акций');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPromotions(activeTab);
  }, [activeTab]);

  const handleImport = async () => {
    try {
      const values = await form.validateFields();
      if (!fileList.length) {
        message.warning('Выберите файл');
        return;
      }

      setImporting(true);
      const formData = new FormData();
      formData.append('file', fileList[0].originFileObj as File);
      formData.append('name', values.name);
      if (values.dates?.[0]) {
        formData.append('start_date', values.dates[0].format('YYYY-MM-DD'));
      }
      if (values.dates?.[1]) {
        formData.append('end_date', values.dates[1].format('YYYY-MM-DD'));
      }

      const res = await apiClient.post('/promotions/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = res.data;
      message.success(`Импортировано ${data.imported} товаров в акцию "${data.name}"`);
      if (data.errors?.length) {
        message.warning(`Ошибки: ${data.errors.length} строк`);
      }

      setImportOpen(false);
      form.resetFields();
      setFileList([]);
      // Switch to "all" tab to see the imported promotion
      setActiveTab('all');
      fetchPromotions('all');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Ошибка импорта');
    } finally {
      setImporting(false);
    }
  };

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
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Акции</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setImportOpen(true)}>
          Загрузить акцию
        </Button>
      </Space>

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

      <Modal
        title="Загрузить акцию из Excel/CSV"
        open={importOpen}
        onCancel={() => {
          setImportOpen(false);
          form.resetFields();
          setFileList([]);
        }}
        onOk={handleImport}
        okText="Загрузить"
        cancelText="Отмена"
        confirmLoading={importing}
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Название акции"
            rules={[{ required: true, message: 'Введите название акции' }]}
          >
            <Input placeholder="Например: Весенняя распродажа 2026" />
          </Form.Item>

          <Form.Item name="dates" label="Период акции">
            <DatePicker.RangePicker
              style={{ width: '100%' }}
              format="DD.MM.YYYY"
              placeholder={['Дата начала', 'Дата окончания']}
            />
          </Form.Item>

          <Form.Item label="Файл акции (Excel или CSV)" required>
            <Upload
              fileList={fileList}
              beforeUpload={(file) => {
                const valid = /\.(xlsx|xls|csv)$/i.test(file.name);
                if (!valid) {
                  message.error('Поддерживаются файлы .xlsx, .xls, .csv');
                  return Upload.LIST_IGNORE;
                }
                setFileList([file as any]);
                return false;
              }}
              onRemove={() => setFileList([])}
              maxCount={1}
              accept=".xlsx,.xls,.csv"
            >
              <Button icon={<UploadOutlined />}>Выбрать файл</Button>
            </Upload>
            <Typography.Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
              Файл из кабинета WB с колонками: Артикул WB, Плановая цена, Скидка, Текущая цена, Участвует
            </Typography.Text>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
