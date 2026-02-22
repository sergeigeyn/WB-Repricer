import { lazy, Suspense, Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { useAuthStore } from '@/store/authStore';
import AppLayout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ProductsPage from '@/pages/ProductsPage';
import PromotionsPage from '@/pages/PromotionsPage';
import PromotionDetailPage from '@/pages/PromotionDetailPage';
import StrategiesPage from '@/pages/StrategiesPage';
import StrategyDetailPage from '@/pages/StrategyDetailPage';
import SettingsPage from '@/pages/SettingsPage';

const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'));
const ProductAnalyticsPage = lazy(() => import('@/pages/ProductAnalyticsPage'));

class ChartErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: string }
> {
  state = { hasError: false, error: '' };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Chart loading error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="warning"
          title="Ошибка загрузки графиков"
          subTitle={this.state.error}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              Перезагрузить
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}

function LazyPage({ children }: { children: ReactNode }) {
  return (
    <ChartErrorBoundary>
      <Suspense fallback={<Spin size="large" style={{ display: 'block', textAlign: 'center', padding: 80 }} />}>
        {children}
      </Suspense>
    </ChartErrorBoundary>
  );
}

function PrivateRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/products" element={<ProductsPage />} />
                <Route path="/products/:id/analytics" element={<LazyPage><ProductAnalyticsPage /></LazyPage>} />
                <Route path="/promotions" element={<PromotionsPage />} />
                <Route path="/promotions/:id" element={<PromotionDetailPage />} />
                <Route path="/strategies" element={<StrategiesPage />} />
                <Route path="/strategies/:id" element={<StrategyDetailPage />} />
                <Route path="/analytics" element={<LazyPage><AnalyticsPage /></LazyPage>} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </AppLayout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
