import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Typography,
  Input,
  Tag,
  Image,
  Space,
  Button,
  Switch,
  message,
} from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
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
  total_stock: number;
  is_active: boolean;
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [search, setSearch] = useState('');
  const [inStock, setInStock] = useState(false);
  const [page, setPage] = useState(1);
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
      const { data } = await apiClient.get('/products', { params });
      setProducts(data.items);
      setTotal(data.total);
    } catch {
      message.error('Не удалось загрузить товары');
    } finally {
      setLoading(false);
    }
  }, [page, search, inStock]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleCollect = async () => {
    setCollecting(true);
    try {
      const { data } = await apiClient.post('/data/collect');
      message.success(
        `Собрано: ${data.products_synced} товаров, ${data.price_snapshots} цен`
      );
      fetchProducts();
    } catch {
      message.error('Ошибка сбора данных');
    } finally {
      setCollecting(false);
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
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
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
      title: 'Категория',
      dataIndex: 'category',
      key: 'category',
      width: 180,
      ellipsis: true,
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
      sorter: (a, b) => a.total_stock - b.total_stock,
    },
    {
      title: 'Цена до скидки',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 130,
      align: 'right',
      render: formatPrice,
      sorter: (a, b) => (a.current_price || 0) - (b.current_price || 0),
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
      sorter: (a, b) => (a.final_price || 0) - (b.final_price || 0),
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
            }}
            checkedChildren="В наличии"
            unCheckedChildren="Все"
          />
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
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: setPage,
          showTotal: (t) => `Всего ${t} товаров`,
          showSizeChanger: false,
        }}
      />
    </div>
  );
}
