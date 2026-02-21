# CLAUDE.md — WB Repricer (PriceForge)

## Описание проекта

Кастомизируемый репрайсер для Wildberries. Частный инструмент для крупного селлера (20-100 млн руб/мес, 50-300 SKU). Ключевое отличие от конкурентов: ценообразование по динамике скорости продаж, защита от out-of-stock, управление акционными порогами, глубокая аналитика по образцу Indeepa.

**Статус:** Фаза 1 (MVP) — Sprint 1.2 завершён
**Кодовое название:** PriceForge
**Дата последнего обновления:** 2026-02-21

## Технический стек

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (async), Pydantic 2.10, Celery, aiogram 3.17
- **Frontend:** React 18, TypeScript 5.6, Ant Design 5, Vite 6, React Router 6, Zustand 5, React Query 5, Axios
- **Инфраструктура:** Docker Compose, PostgreSQL 16, Redis 7, Nginx, Ubuntu 24.04
- **WB API:** HTTPx 0.28 (собственная интеграция, бесплатный API продавца)

## Развёрнутая инфраструктура

### Серверы

| Компонент | URL / Адрес |
|-----------|-------------|
| Backend API | `https://45-12-72-202.sslip.io/api` |
| Frontend | `https://wb-repricer.vercel.app` |
| VPS | `45.12.72.202` (Ubuntu 24.04) |
| GitHub | `sergeigeyn/WB-Repricer` |

### Docker-контейнеры (на VPS)
```
/opt/priceforge/docker/
├── pf-backend     (FastAPI, port 8000)
├── pf-postgres    (PostgreSQL 16, port 5432)
├── pf-redis       (Redis 7, port 6379)
├── pf-celery      (Celery worker)
└── pf-celerybeat  (Celery Beat scheduler)
```

### Доступ (хранится ТОЛЬКО в `.server-credentials`, НЕ в git!)
- SSH, пароли, DB credentials — в файле `.server-credentials`
- Admin-аккаунт для фронтенда — в `.server-credentials`

### Деплой Backend
```bash
# На сервере:
cd /opt/priceforge && git pull origin main && cd docker && docker compose up -d --build backend
```

### Деплой Frontend
Frontend хостится на Vercel — автодеплой при push в `main`.

## Структура проекта

```
WB-Repricer/
├── CLAUDE.md                   # ← Ты здесь
├── ARCHITECTURE.md             # Техническая архитектура
├── ROADMAP.md                  # Дорожная карта с фазами
├── .server-credentials         # SSH/DB доступ (НЕ в git!)
├── .gitignore
├── research/                   # Исследования
│   ├── COMPETITOR_ANALYSIS.md
│   ├── QUESTIONNAIRE_ANALYSIS.md
│   ├── CLIENT_QUESTIONNAIRE.md
│   └── PRODUCT_SPEC_FOR_CLIENT.md
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── api/                # API-эндпоинты
│   │   │   ├── router.py       # Главный роутер
│   │   │   ├── auth.py         # JWT аутентификация
│   │   │   ├── products.py     # Товары, юнит-экономика
│   │   │   ├── promotions.py   # Акции (API + Excel/CSV import)
│   │   │   ├── settings.py     # Настройки, WB-аккаунты
│   │   │   ├── data.py         # Сбор данных (collect_all)
│   │   │   └── health.py       # Health-check
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings
│   │   │   ├── database.py     # SQLAlchemy async engine
│   │   │   ├── security.py     # JWT, AES-256 шифрование API-ключей
│   │   │   └── seed.py         # Инициализация admin
│   │   ├── models/
│   │   │   ├── user.py         # User
│   │   │   ├── product.py      # Product, WBAccount
│   │   │   ├── price.py        # PriceSnapshot
│   │   │   ├── stock.py        # Stock
│   │   │   ├── sales.py        # SalesDaily
│   │   │   ├── promotion.py    # Promotion, PromotionProduct
│   │   │   ├── competitor.py   # Competitor
│   │   │   ├── strategy.py     # PricingStrategy
│   │   │   └── settings.py     # Settings
│   │   ├── schemas/
│   │   │   ├── auth.py         # Login, Token
│   │   │   ├── user.py         # User DTO
│   │   │   ├── product.py      # Product DTO, ExtraCostItem
│   │   │   ├── promotion.py    # Promotion/PromotionProduct DTO
│   │   │   └── wb_account.py   # WBAccount DTO
│   │   ├── services/
│   │   │   ├── data_collector.py       # Оркестратор сбора данных
│   │   │   ├── promotion_collector.py  # Синхронизация акций + расчёт маржи
│   │   │   └── wb_api/
│   │   │       ├── client.py           # WB API клиент (реальный)
│   │   │       └── mock_client.py      # Mock для dev
│   │   ├── tasks/
│   │   │   └── celery_app.py   # Celery конфигурация
│   │   └── bot/
│   │       └── __init__.py     # Telegram-бот (aiogram)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Маршруты
│   │   ├── main.tsx            # Entry point
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx           # /login
│   │   │   ├── DashboardPage.tsx       # / и /dashboard
│   │   │   ├── ProductsPage.tsx        # /products
│   │   │   ├── PromotionsPage.tsx      # /promotions
│   │   │   ├── PromotionDetailPage.tsx # /promotions/:id
│   │   │   └── SettingsPage.tsx        # /settings
│   │   ├── components/
│   │   │   └── Layout.tsx      # Sidebar + Header layout
│   │   ├── store/
│   │   │   └── authStore.ts    # Zustand auth store
│   │   ├── api/
│   │   │   └── client.ts       # Axios API client
│   │   └── utils/
│   │       └── token.ts        # JWT token management
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── nginx/nginx.conf
└── scripts/
    ├── deploy.sh
    └── ssh_cmd.sh              # НЕ в git!
```

## WB API — домены и методы

### Домены
```python
WB_CONTENT    = "https://content-api.wildberries.ru"           # Карточки товаров
WB_PRICES     = "https://discounts-prices-api.wildberries.ru"  # Цены и скидки
WB_STATISTICS = "https://statistics-api.wildberries.ru"        # Заказы, продажи, остатки
WB_MARKETPLACE= "https://marketplace-api.wildberries.ru"       # FBO/FBS, склады
WB_COMMON     = "https://common-api.wildberries.ru"            # Тарифы, комиссии
WB_ANALYTICS  = "https://seller-analytics-api.wildberries.ru"  # Аналитика, хранение
WB_CALENDAR   = "https://dp-calendar-api.wildberries.ru"       # Акции (календарь)
```

### Важные особенности Calendar API (акции)
- **Разрешение:** Требует токен категории **"Цены и скидки"** (НЕ отдельный "Календарь")
- **Обязательные параметры `get_promotions()`:**
  - `allPromo=true`, `startDateTime` (RFC3339), `endDateTime` (RFC3339), `limit`, `offset`
- **`get_promotion_details()`:** Параметр `promotionIDs` (мн. число!), не `promotionID`
- **`get_promotion_nomenclatures()`:** Требует `inAction` (true/false), надо делать 2 запроса
  - Некоторые акции возвращают 422 — обработка `httpx.HTTPStatusError`
- **Rate limit:** 10 запросов / 6 сек → `asyncio.sleep(1.5)` между вызовами

### Реализованные API-методы в `WBApiClient`
| Метод | WB API | Назначение |
|-------|--------|-----------|
| `get_products()` | Content API | Карточки товаров (курсорная пагинация) |
| `get_prices()` | Prices API | Цены и скидки (offset-пагинация) |
| `get_supplier_stocks()` | Statistics API | Остатки по складам |
| `get_orders(date_from)` | Statistics API | Заказы |
| `get_sales(date_from)` | Statistics API | Продажи и возвраты |
| `get_report_detail(from, to)` | Statistics API v5 | Фин. отчёт (логистика, СПП, комиссии) |
| `get_commissions()` | Common API | Комиссии WB по категориям |
| `get_paid_storage(from, to)` | Analytics API | Платное хранение (async task API) |
| `get_box_tariffs()` | Common API | Тарифы короба |
| `get_promotions()` | Calendar API | Список акций |
| `get_promotion_details(id)` | Calendar API | Детали акции |
| `get_promotion_nomenclatures(id)` | Calendar API | Товары в акции |
| `upload_promotion_nomenclatures(id, items)` | Calendar API | Вход в акцию |

## API-эндпоинты Backend

### Auth
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/login` | JWT-авторизация |
| GET | `/auth/me` | Текущий пользователь |

### Products
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/products` | Каталог товаров с юнит-экономикой |
| GET | `/products/{id}` | Детали товара |
| PUT | `/products/{id}/costs` | Обновить себестоимость |
| POST | `/products/import-costs` | Импорт себестоимостей из Excel/CSV |
| PUT | `/products/{id}/extra-costs` | Обновить прочие расходы |

### Promotions
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/promotions` | Список акций с агрегатами маржи |
| GET | `/promotions/{id}` | Детали акции + товары с маржами |
| POST | `/promotions/{id}/decisions` | Установить решение (enter/skip) |
| POST | `/promotions/import` | Импорт акции из Excel/CSV |

### Data
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/data/collect` | Запуск полного сбора данных |

### Settings
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/settings/accounts` | Список WB-аккаунтов |
| POST | `/settings/accounts` | Добавить WB-аккаунт |
| PUT | `/settings/accounts/{id}` | Обновить аккаунт (налог, тариф) |

## Сбор данных — `collect_all()`

Файл: `backend/app/services/data_collector.py`

Оркестратор последовательно выполняет для каждого аккаунта:
1. `sync_products()` — карточки товаров (Content API)
2. `sync_prices()` — цены и скидки → PriceSnapshot
3. `sync_stocks()` — остатки по складам (Statistics API)
4. `sync_orders()` — заказы/возвраты → SalesDaily
5. `sync_tariffs()` — комиссии WB по категориям (Common API)
6. `sync_financial_costs()` — логистика, СПП из фин. отчёта (Statistics API v5)
7. `sync_paid_storage()` — платное хранение (Analytics API, async task)
8. `sync_promotions()` — список акций (Calendar API)
9. `sync_promotion_products()` — товары для active/upcoming акций + расчёт маржи

**Предупреждение:** `collect_all()` может занимать 3-5 минут (paid storage polling + множество акций). Для прод-среды выносить в Celery-задачу. Прямой вызов через `POST /data/collect` может таймаутить по nginx.

## Расчёт маржи — формула

Файл: `backend/app/services/promotion_collector.py` → `calculate_promo_margin()`

```
spp_price = price * (1 - spp_pct / 100)    # Цена покупателя после СПП
tax       = spp_price * account_tax / 100    # Налог считается от spp_price!
commission = price * commission_pct / 100
tariff     = price * account_tariff / 100
ad         = price * ad_pct / 100

total_costs = cost_price + tax + commission + tariff + logistics + storage + ad + extra_costs
margin_rub  = price - total_costs
margin_pct  = margin_rub / price * 100
```

Та же формула используется в `products.py` → `_enrich_with_prices()` для текущей маржи.

## Ключевые архитектурные решения

### 1. WB API клиент
- Абстрактный интерфейс `BaseWBClient` + реализация `WBApiClient`
- API-ключ шифруется AES-256 в БД (`core/security.py`)
- Отдельный `MockWBClient` для разработки без ключа
- HTTPx async клиент с таймаутами (30с обычные, 60-120с для тяжёлых отчётов)

### 2. Акции — два источника данных
- **Автоматический:** Calendar API синхронизирует акции при каждом `collect_all()`
- **Ручной:** Excel/CSV импорт через `POST /promotions/import` (для случаев когда API недоступен или нужен ручной разбор)
- Flexible column matching с русскими/английскими заголовками

### 3. Безопасность
- JWT (access 30 мин + refresh 7 дней)
- Роли: admin, manager, viewer
- API-ключи WB — зашифрованы AES-256
- `.server-credentials` и `.env` — в `.gitignore`

### 4. Frontend — Ant Design таблицы
- Группированные колонки через `children` (Товар → Фото/Артикул/Название, Маржа → Тек/Акц и т.д.)
- Цветовая индикация: зелёный для положительной маржи, красный для отрицательной
- `Tag` для статусов (active/upcoming/ended)

## Правила разработки

### Backend
- Все эндпоинты — async
- Pydantic для валидации входных данных
- SQLAlchemy 2.0 async session (asyncpg)
- Логирование через `logging` (не print)
- WB API: обработка 422/429/400 с graceful fallback

### Frontend
- Компоненты: функциональные (hooks)
- Стили: Ant Design токены
- API-вызовы: через `api/client.ts` (axios с interceptors для JWT)
- Маршрутизация: React Router 6

### Git
- Ветка: `main` (прямые пуши, без PR для MVP)
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`)
- Всегда `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

## Текущий статус (Sprint 1.2 завершён)

### Phase 0: Инфраструктура — DONE
- [x] VPS арендован (45.12.72.202)
- [x] Docker + Docker Compose настроен
- [x] SSL через sslip.io
- [x] Структура проекта создана
- [x] WB API подключен (все ключевые эндпоинты)
- [x] Схема БД + прямые SQL миграции
- [x] Git + GitHub (sergeigeyn/WB-Repricer)
- [x] Deploy script

### Sprint 1.1: Каталог товаров и юнит-экономика — DONE
- [x] Data Collector: сбор товаров, цен, остатков, заказов
- [x] Каталог товаров с фото, артикулами, ценами
- [x] Загрузка себестоимости (inline + Excel/CSV импорт)
- [x] Юнит-экономика: маржа = цена - (себестоимость + налог + комиссия + тариф + логистика + хранение + реклама + прочие)
- [x] Комиссии WB автоматически из API
- [x] Логистика и СПП из финансового отчёта
- [x] Платное хранение из Analytics API (async task)
- [x] Прочие расходы (конструктор: фиксированные + процентные)
- [x] Группированные колонки в таблице (Ant Design)

### Sprint 1.2: Прогноз маржи при входе в акцию — DONE
- [x] Calendar API интеграция (4 метода)
- [x] Автосинхронизация акций в `collect_all()` (158 акций получено)
- [x] Excel/CSV ручной импорт акций
- [x] Расчёт маржи при текущей vs акционной цене
- [x] UI: список акций с Tabs (Активные/Будущие/Завершённые)
- [x] UI: детали акции с товарами и двойной маржей
- [x] Массовые действия: "Войти выгодным" / "Пропустить убыточные"
- [ ] Автовход/автовыход (Sprint 1.2.4 — будущий спринт)
- [ ] История акций и P&L (Sprint 1.2.5 — будущий спринт)

### Следующие спринты (не начаты)
- Sprint 1.3: Защита от out-of-stock
- Sprint 1.4: Акционный бустинг (медианная цена)
- Sprint 1.5: Ценообразование по скорости продаж
- Sprint 1.6: Управление ценами через WB API

## Известные ограничения

1. **`collect_all()` таймаутит через nginx** — для прод-среды выносить в Celery. Временный workaround: `docker exec pf-backend python -c "..."` напрямую в контейнере
2. **Платное хранение** — async task API WB, polling каждые 10 сек, до 2 мин ожидания
3. **Calendar API rate limit** — 10 req / 6 sec, при 30+ активных акциях sync занимает минуту+
4. **Некоторые акции возвращают пустые nomenclatures** — если все товары уже auto-enrolled

## Изоляция и рабочее окружение

**КРИТИЧЕСКИ ВАЖНО:** Этот проект полностью изолирован от остальных проектов в портфолио.

### Рабочая директория
- **Путь:** `/Users/sergeigein/Documents/Project Claude/WB-Repricer/`
- Работаем **ТОЛЬКО** в этой директории и её поддиректориях
- **НЕ трогать** файлы и сервисы других проектов

### Репозиторий
- **GitHub:** `https://github.com/sergeigeyn/WB-Repricer.git`
- **Remote:** `origin`
- **Основная ветка:** `main`

### Правила безопасности при git push
1. **НИКОГДА** не коммитить файлы с паролями, API-ключами, токенами
2. **ВСЕГДА** проверять `git diff --cached` перед коммитом на наличие секретов
3. **НЕ добавлять** IP-адрес сервера, SSH-пароли, production-пароли в коммиты
4. В `.env.example` только плейсхолдеры

### Локальные файлы с секретами (НЕ в git!)
- **`.server-credentials`** — SSH, DB, admin доступ к серверу
- **`scripts/ssh_cmd.sh`** — скрипт SSH-подключения
- **`backend/.env`** — переменные окружения

## Контакты и ресурсы

- **WB API документация:** https://openapi.wildberries.ru/
- **WB Dev Portal:** https://dev.wildberries.ru/
- **Референс UI:** Indeepa (https://indeepa.com/)
- **Анализ конкурентов:** `research/COMPETITOR_ANALYSIS.md`
- **Требования заказчика:** `research/QUESTIONNAIRE_ANALYSIS.md`
