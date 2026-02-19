import { Card, Col, Row, Statistic, Typography } from 'antd';
import {
  ArrowUpOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  WarningOutlined,
} from '@ant-design/icons';

export default function DashboardPage() {
  return (
    <div>
      <Typography.Title level={3}>Дашборд</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Выручка за сегодня"
              value={0}
              prefix={<DollarOutlined />}
              suffix="₽"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Заказы"
              value={0}
              prefix={<ShoppingCartOutlined />}
              suffix="шт."
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Средняя маржа"
              value={0}
              prefix={<ArrowUpOutlined />}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Товары с низкой маржой"
              value={0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 24 }}>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center', padding: 40 }}>
          Подключите WB API ключ для загрузки данных.
          <br />
          Система работает в mock-режиме.
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
