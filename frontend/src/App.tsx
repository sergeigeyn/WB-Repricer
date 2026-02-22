import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import AppLayout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ProductsPage from '@/pages/ProductsPage';
import PromotionsPage from '@/pages/PromotionsPage';
import PromotionDetailPage from '@/pages/PromotionDetailPage';
import StrategiesPage from '@/pages/StrategiesPage';
import StrategyDetailPage from '@/pages/StrategyDetailPage';
import ProductAnalyticsPage from '@/pages/ProductAnalyticsPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import SettingsPage from '@/pages/SettingsPage';

function PrivateRoute({ children }: { children: React.ReactNode }) {
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
                <Route path="/products/:id/analytics" element={<ProductAnalyticsPage />} />
                <Route path="/promotions" element={<PromotionsPage />} />
                <Route path="/promotions/:id" element={<PromotionDetailPage />} />
                <Route path="/strategies" element={<StrategiesPage />} />
                <Route path="/strategies/:id" element={<StrategyDetailPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </AppLayout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
