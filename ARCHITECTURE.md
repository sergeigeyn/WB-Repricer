# Архитектура: WB Repricer

**Версия:** 1.0
**Дата:** 2026-02-19
**Кодовое название:** PriceForge

---

## 1. Обзор системы

### 1.1 Что строим
Кастомизируемый репрайсер для Wildberries с фокусом на:
- Динамическое ценообразование по скорости продаж (7д/14д)
- Защиту от out-of-stock
- Управление акционными порогами (медианной ценой)
- Глубокую аналитику по образцу Indeepa

### 1.2 Ключевые метрики
- **50-300 SKU** (с ростом до 350+)
- **1 ЛК WB** (архитектура поддерживает мульти-ЛК)
- **2-5 пользователей** одновременно
- **Проверка цен:** 2 раза в день (с возможностью увеличения)
- **Полная автоматика** изменения цен

---

## 2. Технический стек

### 2.1 Backend

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| **API-сервер** | Python 3.12 + FastAPI | Высокая скорость разработки, async, отличная типизация |
| **ORM** | SQLAlchemy 2.0 + Alembic | Миграции, модели, async поддержка |
| **Фоновые задачи** | Celery + Redis (broker) | Расписание, стратегии, сбор данных WB |
| **Расписание** | Celery Beat | Cron-like задачи (проверка цен 2р/день) |
| **Кеш** | Redis | Кеш API-ответов WB, сессии |
| **БД** | PostgreSQL 16 | Надёжность, JSON-поля для гибких настроек |
| **Уведомления** | aiogram 3.x | Telegram-бот для алертов и дайджестов |

### 2.2 Frontend

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| **Фреймворк** | React 18 + TypeScript | Компонентный подход, большая экосистема |
| **UI Kit** | Ant Design 5 | Enterprise-уровень, таблицы, формы, дашборды |
| **Графики** | Recharts | React-native, гибкие, лёгкие |
| **Состояние** | Zustand | Простой, без бойлерплейта |
| **Сборка** | Vite | Быстрая сборка, HMR |
| **Таблицы** | AG Grid (Community) | Сортировка, фильтры, 100+ колонок |
| **HTTP** | Axios + React Query | Кеширование запросов, оптимистичные обновления |

### 2.3 Инфраструктура

| Компонент | Технология |
|-----------|-----------|
| **Контейнеризация** | Docker + Docker Compose |
| **Веб-сервер** | Nginx (reverse proxy, static) |
| **SSL** | Let's Encrypt (certbot) |
| **Мониторинг** | Prometheus + Grafana (опционально) |
| **Логирование** | Python logging → файлы + Loki (опционально) |
| **Бэкапы** | pg_dump + cron → S3/local |

---

## 3. Архитектура системы

### 3.1 Высокоуровневая схема

```
┌─────────────────────────────────────────────────────────┐
│                     КЛИЕНТ (Браузер)                    │
│  React + Ant Design + Recharts + AG Grid                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│                      NGINX                               │
│  SSL termination, static files, reverse proxy           │
└──────┬──────────────────────────────────┬───────────────┘
       │ /api/*                           │ /*
┌──────▼──────────┐              ┌────────▼────────┐
│   FastAPI        │              │  React SPA      │
│   (Backend API)  │              │  (Static files) │
│   Port: 8000     │              │                 │
└──────┬──────────┘              └─────────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│                    СЕРВИСНЫЙ СЛОЙ                         │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Price Engine │  │ Strategy     │  │ Analytics      │ │
│  │ (расчёт цен)│  │ Engine       │  │ Engine         │ │
│  │             │  │ (стратегии)  │  │ (аналитика)    │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬─────────┘ │
│         │                │                  │            │
│  ┌──────▼────────────────▼──────────────────▼─────────┐ │
│  │              DATA ACCESS LAYER                      │ │
│  │         SQLAlchemy + Redis Cache                    │ │
│  └──────┬────────────────────────────────┬────────────┘ │
└─────────│────────────────────────────────│──────────────┘
          │                                │
┌─────────▼──────┐              ┌──────────▼────────┐
│  PostgreSQL 16  │              │     Redis          │
│  (основная БД)  │              │  (кеш + брокер)   │
└────────────────┘              └───────────────────┘
          │
┌─────────▼──────────────────────────────────────────────┐
│              ФОНОВЫЕ ЗАДАЧИ (Celery)                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ WB Data      │  │ Price        │  │ Notification  │ │
│  │ Collector    │  │ Updater      │  │ Service       │ │
│  │ (сбор данных)│  │ (обновление) │  │ (Telegram)    │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘ │
└─────────│──────────────────│──────────────────│─────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────┐
│                    ВНЕШНИЕ API                            │
│                                                          │
│  ┌─────────────────┐  ┌───────────────────────────────┐ │
│  │  WB API v3       │  │  Telegram Bot API             │ │
│  │  (цены, акции,   │  │  (уведомления, дайджесты)    │ │
│  │  статистика)     │  │                               │ │
│  └─────────────────┘  └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Модули системы

#### Модуль 1: WB Data Collector
Сбор данных из WB API с оптимизацией вызовов (платный API!).

```
Задачи (Celery Beat):
├── collect_prices          — 2р/день (утро + вечер)
├── collect_orders          — каждые 4 часа
├── collect_stocks          — 2р/день
├── collect_promotions      — 1р/день
├── collect_commissions     — 1р/неделю
├── collect_logistics_costs — 1р/неделю
└── collect_competitors     — 1р/день
```

**Оптимизация API-вызовов:**
- Пакетные запросы (batch) — минимум обращений
- Кеширование в Redis (TTL по типу данных)
- Дельта-обновления (только изменившиеся данные)
- Стоимость: ~300 SKU × 2р/день × 30 дней = ~1800 операций/мес ≈ 180₽/мес

#### Модуль 2: Price Engine
Расчёт оптимальной цены на основе стратегий.

```
Входные данные:
├── Себестоимость (из CSV/Excel)
├── Комиссии WB (автообновление из API)
├── Логистика WB (из API)
├── Возвраты (из API/статистики)
├── Хранение (из API)
├── Налоги (настройка пользователем)
├── Реклама (из API рекламного кабинета)
├── Прочие расходы (конструктор тарифов)
├── Текущие остатки
├── Скорость продаж (7д/14д)
├── Динамика корзин и заказов
├── Цены конкурентов
└── Акционные параметры

Выходные данные:
├── Рекомендуемая цена до скидки
├── Рекомендуемая скидка
├── Прогноз маржи при новой цене
├── Причина изменения (для лога)
└── Confidence score (уверенность в решении)
```

#### Модуль 3: Strategy Engine
Движок стратегий с поддержкой комбинирования и приоритетов.

```
Стратегии (по приоритету заказчика):
├── [P1] OutOfStockProtection    — защита от out-of-stock
├── [P2] SalesVelocityPricing    — ценообразование по скорости 7д/14д
├── [P3] PromotionBooster        — поднятие медианной цены для акций
├── [P4] CompetitorFollowing     — следование за конкурентами
├── [P5] TargetMargin            — минимальная маржа (floor)
├── [P6] PriceRange              — min/max диапазон
├── [P7] DemandReaction           — реакция на спрос
├── [P8] ScheduledPricing        — по расписанию
├── [P9] LocomotiveProduct       — товары-локомотивы
└── [P10] ABTest                 — A/B-тестирование

Конфликт-резолюция:
1. Применить стратегию с наивысшим приоритетом
2. Проверить ограничения (min маржа, min/max цена)
3. Если нарушение — применить ближайшую допустимую цену
4. Логировать причину и результат
```

#### Модуль 4: Promotion Manager
Управление акциями WB.

```
Функции:
├── Автоматический сбор доступных акций
├── Расчёт маржинальности акционной цены
│   ├── Маржа при текущей цене
│   └── Маржа при акционной цене
├── Автовход в выгодные акции
├── Автовыход при нарушении маржи
├── Поднятие медианной цены перед акцией
├── История участия в акциях + P&L
└── Telegram-уведомление при новой акции
```

#### Модуль 5: Analytics Engine
Аналитика и дашборды (по образцу Indeepa).

```
Графики (для каждого артикула):
├── График 1: Динамика цен (СПП%, цена с СПП, макс. промо-цена)
├── График 2: Основные параметры (выкуп%, скорость 14д, бустинг, оборачиваемость, остатки)
├── График 3: Цена акции (артикул vs акция 1, 2, 3...)
└── График 4: Цена-заказы (цена со скидкой, с СПП, заказы шт., отмены/возвраты)

Борды:
├── Заказы по ценам до СПП (гистограмма)
├── Заказы по ценам с СПП (гистограмма)
├── Пиковые часы заказов (бар-чарт по 24 часам)
└── Пиковые дни (бар-чарт по дням недели)

Отчёты:
├── Unit-экономика по SKU
├── P&L за период
├── ABC/XYZ-анализ
├── Прогноз продаж и выручки
├── Рейтинг по маржинальности
├── Эффективность акций
└── Влияние изменения цены на продажи (до/после)

Разрезы:
├── По складам WB
├── По регионам
├── По брендам
├── По категориям
└── По менеджерам
```

#### Модуль 6: Notification Service
Уведомления и дайджесты.

```
Каналы: Telegram (приоритет)

Триггеры:
├── Маржинальность ниже порога
├── WB изменил комиссию/логистику
├── Остатки ниже порога
├── Ошибка API
└── Репрайсер изменил цену (лог)

Дайджесты:
├── Ежедневный (утренний): заказы, маржа, выручка, ошибки, акции
└── Еженедельный: тренды, P&L, рекомендации
```

---

## 4. Схема базы данных

### 4.1 Основные таблицы

```sql
-- Пользователи и доступ
users (id, email, name, role, password_hash, created_at)
user_sessions (id, user_id, token, expires_at)
audit_log (id, user_id, action, entity, entity_id, old_value, new_value, created_at)

-- Товары и ЛК
wb_accounts (id, name, api_key_encrypted, user_id, is_active)
products (id, account_id, nm_id, vendor_code, brand, category, title,
          cost_price, tax_rate, extra_costs_json, is_active, created_at)

-- Цены и история
price_history (id, product_id, price_before_discount, discount,
               price_after_discount, spp_price, margin_rub, margin_pct,
               change_reason, strategy_id, created_at)
price_snapshots (id, product_id, wb_price, wb_discount, spp_percent,
                 wallet_discount, final_price, collected_at)

-- Стратегии
strategies (id, name, type, config_json, priority, is_active, created_by)
product_strategies (id, product_id, strategy_id, params_json, is_active)

-- Конкуренты
competitors (id, product_id, competitor_nm_id, competitor_brand,
             is_active, added_by)
competitor_prices (id, competitor_id, price, spp_price, stock_quantity,
                   rating, reviews_count, collected_at)

-- Остатки и продажи
stock_history (id, product_id, warehouse_id, quantity, collected_at)
sales_daily (id, product_id, date, orders_count, sales_count,
             returns_count, cancel_count, revenue,
             cart_adds, avg_price_spp)
sales_hourly (id, product_id, date, hour, orders_count, cart_adds)

-- Акции
promotions (id, wb_promo_id, name, start_date, end_date,
            discount_percent, is_active)
promotion_products (id, promotion_id, product_id, promo_price,
                    current_margin, promo_margin, decision, decided_at)

-- Финансы
cost_templates (id, name, items_json, created_by)
-- items_json: [{name: "Упаковка", value: 50, type: "fixed"},
--              {name: "Налог УСН", value: 6, type: "percent"}]

-- Настройки
user_settings (id, user_id, dashboard_config_json, notification_config_json)
system_settings (key, value, updated_at)
```

### 4.2 Индексы

```sql
-- Критические для производительности
CREATE INDEX idx_price_history_product_date ON price_history(product_id, created_at DESC);
CREATE INDEX idx_sales_daily_product_date ON sales_daily(product_id, date DESC);
CREATE INDEX idx_sales_hourly_product_date ON sales_hourly(product_id, date, hour);
CREATE INDEX idx_stock_history_product_date ON stock_history(product_id, collected_at DESC);
CREATE INDEX idx_competitor_prices_date ON competitor_prices(competitor_id, collected_at DESC);
```

---

## 5. API Design (Backend → Frontend)

### 5.1 Основные эндпоинты

```
AUTH:
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

PRODUCTS:
GET    /api/products                    — список товаров с фильтрами
GET    /api/products/:id                — детали товара
PUT    /api/products/:id/cost           — обновить себестоимость
POST   /api/products/import-costs       — загрузка CSV/Excel себестоимостей
GET    /api/products/:id/analytics      — аналитика карточки (4 графика + 4 борда)

STRATEGIES:
GET    /api/strategies                  — список стратегий
POST   /api/strategies                  — создать стратегию
PUT    /api/strategies/:id              — обновить стратегию
POST   /api/products/:id/strategies     — привязать стратегию к товару
PUT    /api/strategies/priorities        — обновить приоритеты

PRICES:
GET    /api/prices/current              — текущие цены всех товаров
GET    /api/prices/history/:product_id  — история цен товара
POST   /api/prices/dry-run             — сухой запуск (предпросмотр)
POST   /api/prices/rollback            — откат к дате
POST   /api/prices/bulk-update         — массовое обновление (Excel)

PROMOTIONS:
GET    /api/promotions                  — активные акции
GET    /api/promotions/:id/forecast     — прогноз маржи акции
POST   /api/promotions/:id/enter        — войти в акцию
POST   /api/promotions/:id/exit         — выйти из акции

COMPETITORS:
GET    /api/competitors/:product_id     — конкуренты товара
POST   /api/competitors/:product_id     — добавить конкурента
GET    /api/competitors/:id/history     — история цен конкурента

ANALYTICS:
GET    /api/analytics/dashboard         — данные дашборда
GET    /api/analytics/pnl               — P&L за период
GET    /api/analytics/abc-xyz           — ABC/XYZ-анализ
GET    /api/analytics/export            — экспорт в Excel

SETTINGS:
GET    /api/settings/dashboard          — настройки дашборда
PUT    /api/settings/dashboard          — сохранить настройки
GET    /api/settings/notifications      — настройки уведомлений
PUT    /api/settings/notifications      — обновить настройки
```

---

## 6. Серверные требования

### 6.1 Минимальная конфигурация (MVP, до 300 SKU)

| Ресурс | Значение | Обоснование |
|--------|----------|-------------|
| **CPU** | 4 vCPU | FastAPI + Celery + PostgreSQL + Redis |
| **RAM** | 8 GB | PostgreSQL ~2GB, Redis ~1GB, App ~2GB, System ~3GB |
| **SSD** | 80 GB | БД ~10GB (год), логи ~5GB, бэкапы ~15GB, система ~20GB |
| **Сеть** | 100 Mbit/s | API-запросы к WB, веб-интерфейс |
| **ОС** | Ubuntu 24.04 LTS | Стабильность, Docker-поддержка |

### 6.2 Рекомендуемая конфигурация (продакшен, рост до 500+ SKU)

| Ресурс | Значение | Обоснование |
|--------|----------|-------------|
| **CPU** | 6 vCPU (или 4 высокочастотных) | Запас для аналитики и графиков |
| **RAM** | 16 GB | Комфортная работа всех компонентов + кеш |
| **SSD NVMe** | 160 GB | Быстрый I/O для PostgreSQL, рост данных |
| **Сеть** | 200 Mbit/s | Быстрая отдача дашбордов |
| **ОС** | Ubuntu 24.04 LTS | |

### 6.3 Docker-контейнеры

```yaml
# docker-compose.yml (схема)
services:
  nginx:          # Reverse proxy + SSL + static
    image: nginx:alpine
    ports: ["443:443", "80:80"]

  backend:        # FastAPI приложение
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis]

  celery-worker:  # Фоновые задачи
    build: ./backend
    command: celery -A app.celery worker
    depends_on: [postgres, redis]

  celery-beat:    # Расписание задач
    build: ./backend
    command: celery -A app.celery beat
    depends_on: [redis]

  frontend:       # React SPA (build → nginx)
    build: ./frontend
    # Static files served by nginx

  postgres:       # База данных
    image: postgres:16-alpine
    volumes: ["pg_data:/var/lib/postgresql/data"]

  redis:          # Кеш + брокер Celery
    image: redis:7-alpine
    volumes: ["redis_data:/data"]

  telegram-bot:   # Уведомления (опционально отдельный контейнер)
    build: ./backend
    command: python -m app.bot
```

### 6.4 WB API: стоимость

**Важно:** С января 2026 WB ввёл платный API (pay-as-you-go), но это касается **только облачных SaaS-сервисов** из Каталога готовых решений WB.

Наш случай — **частный инструмент заказчика**, работающий с **его собственным API-ключом**. Это классифицируется как **собственная интеграция продавца** → **API полностью бесплатный**.

Дополнительно: 19+ методов API остаются бесплатными для всех категорий пользователей.

**Вывод: расходы на WB API = 0 ₽/мес**

> Источники: [WB API News](https://dev.wildberries.ru/en/news/151), [Forbes.ru](https://www.forbes.ru/novosti-kompaniy/553966), [Oborot.ru](https://oborot.ru/news/wildberries-vvodit-oplatu-za-fakticheskoe-ispolzovanie-svoego-api-i262234.html)

### 6.5 Оценка стоимости сервера

| Вариант | Провайдер | Конфигурация | Цена/мес |
|---------|-----------|-------------|----------|
| **Бюджетный** | Timeweb Cloud / Selectel | 4 vCPU, 8GB RAM, 80GB SSD | 2,000–3,000 ₽ |
| **Рекомендуемый** | Selectel / Yandex Cloud | 6 vCPU, 16GB RAM, 160GB NVMe | 4,000–6,000 ₽ |
| **Максимальный** | Yandex Cloud / VK Cloud | 8 vCPU, 32GB RAM, 250GB NVMe | 8,000–12,000 ₽ |

**Общая стоимость эксплуатации (рекомендуемый):**
- Сервер: ~5,000 ₽/мес
- WB API: **0 ₽/мес** (собственная интеграция продавца)
- Домен + SSL: бесплатно (Let's Encrypt)
- **Итого: ~5,000 ₽/мес**

---

## 7. Безопасность

### 7.1 Аутентификация и авторизация
- JWT-токены (access + refresh)
- Роли: admin, manager, viewer
- Гибкие права: просмотр / редактирование / подтверждение

### 7.2 Хранение данных
- API-ключи WB: шифрование AES-256 в БД
- Пароли: bcrypt хэширование
- Все чувствительные переменные — через environment variables

### 7.3 Аудит
- Лог всех изменений цен (кто, когда, что, почему)
- Лог действий пользователей

### 7.4 Бэкапы
- PostgreSQL: pg_dump ежедневно, хранение 30 дней
- Настройки и конфигурации: в Git
- Возможность отката цен к любой дате

---

## 8. Интеграции

### 8.1 WB API v3
```
Используемые разделы:
├── /api/v1/prices          — получение и установка цен
├── /api/v1/discounts       — скидки
├── /api/v1/promotions      — акции
├── /api/v1/stocks          — остатки по складам
├── /api/v1/orders          — заказы
├── /api/v1/sales           — продажи
├── /api/v1/commissions     — комиссии
├── /api/v1/logistics       — стоимость логистики
└── /api/v1/analytics       — аналитика (воронка, позиции)
```

### 8.2 Google Sheets
- Экспорт отчётов в Google Sheets
- Импорт себестоимостей из Sheets (опционально)

### 8.3 Telegram Bot
- Уведомления об изменениях
- Ежедневный/еженедельный дайджест
- Алерты об ошибках

---

## 9. Масштабирование

### 9.1 Текущая архитектура (до 500 SKU)
Один сервер, все контейнеры на одной машине.

### 9.2 При росте (500-2000 SKU)
- Вынести PostgreSQL на отдельный managed DB (Selectel/Yandex)
- Увеличить количество Celery workers
- Добавить кеширование на уровне Nginx

### 9.3 При масштабировании (2000+ SKU)
- Kubernetes / Docker Swarm
- Отдельные серверы для API, workers, DB
- Read replicas для PostgreSQL

---

## 10. Инфраструктурные требования (чеклист)

Помимо основного серверного ПО, для продакшена необходимо настроить:

### 10.1 Защита сервера

| Что | Зачем | Инструмент |
|-----|-------|-----------|
| Firewall | Открыть только 22 (SSH), 80 (HTTP), 443 (HTTPS) | UFW |
| Защита от брутфорса SSH | Блокировка после N неудачных попыток | fail2ban |
| SSH по ключам | Отключить вход по паролю | sshd_config |
| Отдельный sudo-пользователь | Не работать от root | adduser + sudoers |
| Автообновления безопасности | Патчи ОС без вмешательства | unattended-upgrades |

### 10.2 Сеть и домен

| Что | Зачем | Стоимость |
|-----|-------|-----------|
| Домен | Адрес для системы (напр. repricer.example.com) | ~1 500 ₽/год |
| DNS | Привязка домена к IP сервера | Бесплатно (Cloudflare) |
| SSL-сертификат | HTTPS шифрование | Бесплатно (Let's Encrypt) |
| Автопродление SSL | Сертификат обновляется автоматически | certbot --renew (cron) |
| Cloudflare (опционально) | DDoS-защита, CDN, DNS | Бесплатный план |

### 10.3 Бэкапы и восстановление

| Что | Как | Частота |
|-----|-----|---------|
| БД PostgreSQL | pg_dump → gzip → локальная папка | Ежедневно, 03:00 |
| Хранение бэкапов | Локально 30 дней + S3-совместимое хранилище (Selectel/Yandex) | 30 дней локально, 90 дней удалённо |
| Docker volumes | Резервная копия volumes (Redis data, конфиги) | Еженедельно |
| Конфигурации | Git-репозиторий (docker-compose, nginx, .env.example) | Каждое изменение |
| Тестирование восстановления | Проверить что бэкап реально восстанавливается | 1 раз/квартал |

**Сценарий Disaster Recovery:** если сервер умирает →
1. Арендовать новый VPS (10 мин)
2. Развернуть Docker + Docker Compose из Git (15 мин)
3. Восстановить БД из последнего бэкапа в S3 (10 мин)
4. Переключить DNS на новый IP (5 мин + TTL)
5. **Итого: ~40-60 минут до полного восстановления**

### 10.4 Мониторинг и логирование

| Что | Инструмент | Зачем |
|-----|-----------|-------|
| Мониторинг сервера | Prometheus + Node Exporter | CPU, RAM, Disk, Network |
| Визуализация | Grafana | Дашборды мониторинга |
| Алерты инфраструктуры | Grafana Alerting → Telegram | Диск заполнен, RAM исчерпан, контейнер упал |
| Логи приложения | Python logging → файлы + ротация | Дебаг, аудит |
| Ротация логов | logrotate | Не переполнить диск (хранить 14 дней) |
| Health checks | Docker HEALTHCHECK + endpoint /api/health | Автоматический рестарт при падении |
| Uptime мониторинг | UptimeRobot (бесплатно) или аналог | Уведомление если сайт недоступен |

### 10.5 Docker: ресурсные лимиты

```yaml
# Рекомендуемые лимиты в docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits: { cpus: '2', memory: 3G }
        reservations: { memory: 1G }

  redis:
    deploy:
      resources:
        limits: { cpus: '0.5', memory: 1G }
        reservations: { memory: 256M }

  backend:
    deploy:
      resources:
        limits: { cpus: '2', memory: 2G }
        reservations: { memory: 512M }

  celery-worker:
    deploy:
      resources:
        limits: { cpus: '2', memory: 2G }
        reservations: { memory: 512M }
```

Без лимитов один контейнер (например PostgreSQL при тяжёлом запросе) может сожрать всю RAM и уронить остальные.

### 10.6 WB API: устойчивость

| Проблема | Решение |
|----------|---------|
| WB API недоступен (5xx) | Retry с экспоненциальным откатом (1с → 2с → 4с → 8с), макс. 5 попыток |
| Rate limit (429) | Очередь запросов, ожидание cooldown, уважение заголовков Retry-After |
| Таймаут запроса | Таймаут 30с на запрос, fallback на кешированные данные из Redis |
| WB изменил формат ответа | Валидация ответов через Pydantic, алерт в Telegram при ошибке парсинга |
| API-ключ истёк / отозван | Алерт в Telegram, блокировка обновления цен до обновления ключа |

### 10.7 Секреты и переменные окружения

```
НЕ хранить в коде / Git:
├── WB API ключ (шифрован в БД, мастер-ключ в .env)
├── Пароль PostgreSQL (.env)
├── JWT secret key (.env)
├── AES-256 ключ шифрования (.env)
├── Telegram Bot Token (.env)
└── Google OAuth credentials (.env)

Управление:
├── .env файл на сервере (chmod 600, только root)
├── .env.example в Git (без значений, как шаблон)
├── Docker secrets (альтернативно)
└── Никогда не коммитить .env в Git (.gitignore)
```

### 10.8 Среды разработки

| Среда | Назначение | Где |
|-------|-----------|-----|
| **Local (dev)** | Разработка и отладка | Локальный Docker Compose с SQLite или PG |
| **Production** | Боевая система | VPS сервер |
| **Staging** | Не нужен на MVP | В будущем при необходимости |

Для MVP достаточно двух сред: local (разработка) + production (продакшен).

### 10.9 Деплой и обновления

```
Процесс обновления (zero-downtime не нужен для 2-5 пользователей):

1. git pull на сервере
2. docker compose build --no-cache backend
3. docker compose up -d --force-recreate backend celery-worker celery-beat
4. docker compose exec backend alembic upgrade head  (миграции БД)
5. Проверить /api/health
6. Готово (~2-3 минуты даунтайм)

Автоматизация: deploy.sh скрипт (один вызов по SSH)
```

### 10.10 Прочие технические моменты

| Момент | Решение |
|--------|---------|
| Часовой пояс | Сервер и все контейнеры в UTC. Конвертация в Moscow time (UTC+3) на фронтенде |
| Swap | Создать 4GB swap-файл как страховка от OOM killer |
| CORS | Настроить в FastAPI: разрешить только домен фронтенда |
| Rate limiting API | Nginx: limit_req для защиты от перебора |
| Ротация JWT | Refresh-токены привязаны к сессии в БД, можно отозвать |
| Кодировка | Всё в UTF-8 (PostgreSQL, Python, Nginx) |
| Хранение данных (GDPR/ФЗ-152) | Данные хранятся в РФ (VPS в РФ), нет персональных данных покупателей |
