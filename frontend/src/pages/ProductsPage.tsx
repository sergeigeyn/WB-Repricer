import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Table,
  Typography,
  Input,
  InputNumber,
  Tag,
  Image,
  Space,
  Button,
  Switch,
  Upload,
  Modal,
  Dropdown,
  message,
} from 'antd';
import {
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';
import apiClient from '@/api/client';

interface Product {
  id: number;
  nm_id: number;
  vendor_code: string | null;
  brand: string | null;
  category: string | null;
  title: string | null;
  image_url: string | null;
  cost_price: number | null;
  current_price: number | null;
  discount_pct: number | null;
  final_price: number | null;
  commission_pct: number | null;
  logistics_cost: number | null;
  storage_cost: number | null;
  storage_daily: number | null;
  ad_pct: number | null;
  total_stock: number;
  orders_7d: number;
  margin_pct: number | null;
  margin_rub: number | null;
  is_active: boolean;
}

interface ImportResult {
  updated: number;
  skipped: number;
  errors: string[];
}

export default function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [search, setSearch] = useState('');
  const [inStock, setInStock] = useState(searchParams.get('in_stock') === 'true');
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const pageSize = 20;

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
      };
      if (search) params.search = search;
      if (inStock) params.in_stock = true;
      if (sortField) params.sort_by = sortField;
      if (sortOrder) params.sort_order = sortOrder;
      const { data } = await apiClient.get('/products', { params });
      setProducts(data.items);
      setTotal(data.total);
    } catch {
      message.error('Не удалось загрузить товары');
    } finally {
      setLoading(false);
    }
  }, [page, search, inStock, sortField, sortOrder]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleCollect = async () => {
    setCollecting(true);
    try {
      const { data } = await apiClient.post('/data/collect');
      message.success(
        `Собрано: ${data.products_synced} товаров, ${data.price_snapshots} цен, ${data.orders_synced} заказов`
      );
      fetchProducts();
    } catch {
      message.error('Ошибка сбора данных');
    } finally {
      setCollecting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await apiClient.get('/products/cost-template', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'cost_template.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('Ошибка скачивания шаблона');
    }
  };

  const handleExport = async () => {
    try {
      const response = await apiClient.get('/products/export-costs', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'products_costs.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('Ошибка экспорта');
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.csv,.xlsx,.xls',
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError }) => {
      const formData = new FormData();
      formData.append('file', file as File);
      try {
        const { data } = await apiClient.post('/products/import-costs', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setImportResult(data);
        if (data.updated > 0) {
          message.success(`Обновлено ${data.updated} товаров`);
          fetchProducts();
        }
        onSuccess?.(data);
      } catch {
        message.error('Ошибка импорта файла');
        onError?.(new Error('Upload failed'));
      }
    },
  };

  const handleUpdateCost = async (productId: number, field: string, value: number | null) => {
    try {
      const { data } = await apiClient.put(`/products/${productId}/cost`, { [field]: value });
      setProducts((prev) =>
        prev.map((p) => (p.id === productId ? { ...p, ...data } : p))
      );
    } catch {
      message.error('Ошибка сохранения');
    }
  };

  const formatPrice = (val: number | null) => {
    if (val === null || val === undefined) return '—';
    return `${val.toLocaleString('ru-RU')} ₽`;
  };

  const columns: ColumnsType<Product> = [
    {
      title: 'Фото',
      dataIndex: 'image_url',
      key: 'image',
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
      width: 120,
      render: (id: number) => (
        <a href={`https://www.wildberries.ru/catalog/${id}/detail.aspx`} target="_blank" rel="noopener noreferrer">
          {id}
        </a>
      ),
    },
    {
      title: 'Артикул',
      dataIndex: 'vendor_code',
      key: 'vendor_code',
      width: 100,
    },
    {
      title: 'Бренд',
      dataIndex: 'brand',
      key: 'brand',
      width: 120,
      render: (brand: string | null) =>
        brand ? <Tag color="blue">{brand}</Tag> : '—',
    },
    {
      title: 'Остаток',
      dataIndex: 'total_stock',
      key: 'total_stock',
      width: 90,
      align: 'center',
      render: (val: number) => {
        if (!val) return <Tag color="red">0</Tag>;
        const color = val <= 5 ? 'orange' : 'green';
        return <Tag color={color}>{val}</Tag>;
      },
      sorter: true,
    },
    {
      title: 'Заказы 7д',
      dataIndex: 'orders_7d',
      key: 'orders_7d',
      width: 100,
      align: 'center',
      render: (val: number) => {
        if (!val) return <Typography.Text type="secondary">0</Typography.Text>;
        return <Typography.Text strong>{val}</Typography.Text>;
      },
      sorter: true,
    },
    {
      title: 'Цена до скидки',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 130,
      align: 'right',
      render: formatPrice,
      sorter: true,
    },
    {
      title: 'Скидка',
      dataIndex: 'discount_pct',
      key: 'discount_pct',
      width: 90,
      align: 'center',
      render: (val: number | null) => {
        if (val === null || val === undefined) return '—';
        const color = val >= 50 ? 'red' : val >= 30 ? 'orange' : 'green';
        return <Tag color={color}>{val}%</Tag>;
      },
    },
    {
      title: 'Итоговая цена',
      dataIndex: 'final_price',
      key: 'final_price',
      width: 130,
      align: 'right',
      render: (val: number | null) => (
        <Typography.Text strong>{formatPrice(val)}</Typography.Text>
      ),
      sorter: true,
    },
    {
      title: 'Себест.',
      dataIndex: 'cost_price',
      key: 'cost_price',
      width: 100,
      align: 'right',
      render: formatPrice,
    },
    {
      title: 'Комис. %',
      dataIndex: 'commission_pct',
      key: 'commission_pct',
      width: 85,
      align: 'center',
      render: (val: number | null) => {
        if (val === null || val === undefined) return '—';
        return <Typography.Text type="secondary">{val}%</Typography.Text>;
      },
    },
    {
      title: 'Логист.',
      dataIndex: 'logistics_cost',
      key: 'logistics_cost',
      width: 90,
      align: 'right',
      render: (val: number | null) => {
        if (val === null || val === undefined) return <Typography.Text type="secondary">—</Typography.Text>;
        return <Typography.Text>{val} ₽</Typography.Text>;
      },
    },
    {
      title: 'Хранение',
      key: 'storage',
      width: 110,
      align: 'right',
      render: (_: unknown, record: Product) => {
        const daily = record.storage_daily;
        const perSale = record.storage_cost;
        if (daily === null && perSale === null) return <Typography.Text type="secondary">—</Typography.Text>;
        return (
          <div>
            {daily !== null && (
              <div style={{ fontSize: 11, color: '#888' }}>{daily} ₽/сут</div>
            )}
            {perSale !== null && (
              <div style={{ fontWeight: 500 }}>{perSale} ₽/прод</div>
            )}
          </div>
        );
      },
    },
    {
      title: 'Рекл. %',
      dataIndex: 'ad_pct',
      key: 'ad_pct',
      width: 90,
      align: 'center',
      render: (_: number | null, record: Product) => (
        <InputNumber
          size="small"
          min={0}
          max={100}
          step={0.5}
          placeholder="0"
          value={record.ad_pct}
          onBlur={(e) => {
            const val = e.target.value ? parseFloat(e.target.value) : null;
            if (val !== record.ad_pct) handleUpdateCost(record.id, 'ad_pct', val);
          }}
          onPressEnter={(e) => {
            const val = (e.target as HTMLInputElement).value ? parseFloat((e.target as HTMLInputElement).value) : null;
            if (val !== record.ad_pct) handleUpdateCost(record.id, 'ad_pct', val);
          }}
          style={{ width: 60 }}
          suffix="%"
        />
      ),
    },
    {
      title: 'Маржа',
      dataIndex: 'margin_pct',
      key: 'margin_pct',
      width: 90,
      align: 'center',
      render: (val: number | null, record: Product) => {
        if (val === null || val === undefined) return '—';
        const color = val < 10 ? 'red' : val < 25 ? 'orange' : 'green';
        return (
          <Typography.Text>
            <Tag color={color}>{val}%</Tag>
            {record.margin_rub !== null && record.margin_rub !== undefined && (
              <div style={{ fontSize: 11, color: '#888' }}>{record.margin_rub} ₽</div>
            )}
          </Typography.Text>
        );
      },
      sorter: true,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Товары
        </Typography.Title>
        <Space>
          <Input
            placeholder="Поиск по названию, артикулу, бренду"
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            style={{ width: 300 }}
            allowClear
          />
          <Switch
            checked={inStock}
            onChange={(checked) => {
              setInStock(checked);
              setPage(1);
              setSearchParams(checked ? { in_stock: 'true' } : {}, { replace: true });
            }}
            checkedChildren="В наличии"
            unCheckedChildren="Все"
          />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'template',
                  icon: <DownloadOutlined />,
                  label: 'Скачать шаблон CSV',
                  onClick: handleDownloadTemplate,
                },
                {
                  key: 'export',
                  icon: <DownloadOutlined />,
                  label: 'Экспорт товаров CSV',
                  onClick: handleExport,
                },
              ],
            }}
          >
            <Button icon={<FileExcelOutlined />}>Себестоимость</Button>
          </Dropdown>
          <Upload {...uploadProps}>
            <Button icon={<UploadOutlined />}>Импорт CSV/Excel</Button>
          </Upload>
          <Button
            icon={<ReloadOutlined />}
            loading={collecting}
            onClick={handleCollect}
          >
            Обновить из WB
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={products}
        rowKey="id"
        loading={loading}
        size="middle"
        scroll={{ x: 1800 }}
        onChange={(pagination, _filters, sorter) => {
          // Обновляем страницу из пагинации
          if (pagination.current) {
            setPage(pagination.current);
          }
          // Обновляем сортировку — сброс на стр.1 только при смене сортировки
          if (!Array.isArray(sorter)) {
            const newField = sorter.order ? (sorter.field as string) : null;
            const newOrder = sorter.order || null;
            if (newField !== sortField || newOrder !== sortOrder) {
              setSortField(newField);
              setSortOrder(newOrder);
              setPage(1);
            }
          }
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showTotal: (t) => `Всего ${t} товаров`,
          showSizeChanger: false,
        }}
      />

      <Modal
        title="Результат импорта"
        open={importResult !== null}
        onOk={() => setImportResult(null)}
        onCancel={() => setImportResult(null)}
        cancelButtonProps={{ style: { display: 'none' } }}
      >
        {importResult && (
          <div>
            <p><strong>Обновлено:</strong> {importResult.updated} товаров</p>
            <p><strong>Пропущено:</strong> {importResult.skipped}</p>
            {importResult.errors.length > 0 && (
              <>
                <p><strong>Ошибки:</strong></p>
                <ul style={{ maxHeight: 200, overflow: 'auto' }}>
                  {importResult.errors.map((err, i) => (
                    <li key={i} style={{ color: 'red' }}>{err}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
