# CLAUDE.md — WB Repricer (PriceForge)

## Описание проекта

Кастомизируемый репрайсер для Wildberries. Частный инструмент для крупного селлера (20-100 млн ₽/мес, 50-300 SKU). Ключевое отличие от конкурентов: ценообразование по динамике скорости продаж, защита от out-of-stock, управление акционными порогами, глубокая аналитика по образцу Indeepa.

**Статус:** Проектирование (Phase 0)
**Кодовое название:** PriceForge

## Технический стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery, aiogram 3.x
- **Frontend:** React 18, TypeScript, Ant Design 5, Recharts, AG Grid, Zustand, Vite
- **Инфраструктура:** Docker, Nginx, PostgreSQL 16, Redis 7, Ubuntu 24.04
- **WB API:** Бесплатный (собственная интеграция продавца, не SaaS)

## Структура проекта

```
WB-Repricer/
├── CLAUDE.md                   # ← Ты здесь
├── ARCHITECTURE.md             # Техническая архитектура
├── ROADMAP.md                  # Дорожная карта с фазами
├── research/                   # Исследования
│   ├── COMPETITOR_ANALYSIS.md  # Анализ 15 конкурентов
│   ├── QUESTIONNAIRE_ANALYSIS.md # Анализ ответов заказчика
│   └── CLIENT_QUESTIONNAIRE.md # Опросник (MD-версия)
├── backend/                    # FastAPI приложение
│   ├── app/
│   │   ├── api/               # API-эндпоинты (роутеры)
│   │   ├── core/              # Конфиг, безопасность, зависимости
│   │   ├── models/            # SQLAlchemy модели
│   │   ├── schemas/           # Pydantic схемы
│   │   ├── services/          # Бизнес-логика
│   │   │   ├── wb_api/        # WB API клиент
│   │   │   ├── price_engine/  # Движок расчёта цен
│   │   │   ├── strategies/    # Стратегии ценообразования
│   │   │   ├── promotions/    # Управление акциями
│   │   │   ├── analytics/     # Аналитика и отчёты
│   │   │   └── notifications/ # Telegram-уведомления
│   │   ├── tasks/             # Celery-задачи
│   │   └── bot/               # Telegram-бот
│   ├── alembic/               # Миграции БД
│   ├── tests/                 # Тесты
│   └── requirements.txt
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── components/        # UI-компоненты
│   │   ├── pages/             # Страницы
│   │   ├── store/             # Zustand стор
│   │   ├── api/               # API-клиент
│   │   ├── hooks/             # React-хуки
│   │   └── utils/             # Утилиты
│   ├── package.json
│   └── vite.config.ts
├── docker/                     # Docker-конфигурации
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx/
└── scripts/                    # Утилитарные скрипты
    ├── deploy.sh
    └── backup.sh
```

## Ключевые архитектурные решения

### 1. Стратегии ценообразования
Стратегии реализуются как отдельные классы с общим интерфейсом:
```python
class BaseStrategy(ABC):
    @abstractmethod
    def calculate_price(self, product: Product, context: PriceContext) -> PriceResult:
        pass
```

Комбинирование: несколько стратегий на товар с приоритетами. Конфликт-резолюция: приоритет → ограничения (min маржа, min/max цена) → лог.

### 2. WB API
- Клиент — абстрактный слой (если WB поменяет API — меняем только клиент)
- API-ключ шифруется AES-256 в БД
- Batch-запросы для минимизации обращений
- Кеширование ответов в Redis

### 3. Данные
- Все исторические данные хранятся (цены, остатки, заказы, конкуренты)
- Проверки: 2 раза в день (Celery Beat)
- Кеш текущих значений: Redis (TTL 1 час)

### 4. Безопасность
- JWT (access 30 мин + refresh 7 дней)
- Роли: admin, manager, viewer
- Аудит-лог всех изменений
- API-ключи WB — зашифрованы

## Правила разработки

### Backend
- **Всегда** использовать Pydantic для валидации входных данных
- **Всегда** использовать async эндпоинты в FastAPI
- Миграции через Alembic (никогда не менять БД напрямую)
- Celery-задачи должны быть идемпотентными
- Логировать все изменения цен с причиной

### Frontend
- Компоненты: функциональные (hooks, no class components)
- Стили: Ant Design токены, CSS modules для кастомных стилей
- Таблицы: AG Grid для больших таблиц, Ant Design Table для маленьких
- Графики: Recharts с единой цветовой палеттой
- API-вызовы: через React Query (кеширование, рефетч)

### Git
- Ветки: `main`, `develop`, `feature/*`, `fix/*`
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`)
- Всегда Co-Authored-By: Claude

### Тестирование
- Backend: pytest + httpx (для async тестов)
- Frontend: Vitest + Testing Library
- E2E: пока не нужно (MVP)

## Текущая фаза

**Фаза 0: Подготовка инфраструктуры**
- [ ] Арендовать VPS
- [ ] Настроить Docker + Docker Compose
- [ ] Домен + SSL
- [ ] Структура проекта
- [ ] Подключить WB API
- [ ] Схема БД + миграции
- [ ] CI/CD
- [ ] Бэкапы

## Зависимости от других проектов

- Проект **НЕ** использует общий n8n-сервер (golosai.online)
- Отдельный VPS, отдельная БД, отдельный Redis
- Полностью изолирован от других проектов в портфолио

## Контакты и ресурсы

- **WB API документация:** https://openapi.wildberries.ru/
- **WB Dev Portal:** https://dev.wildberries.ru/
- **Референс UI:** Indeepa (https://indeepa.com/) — интерфейс и структура
- **Анализ конкурентов:** `research/COMPETITOR_ANALYSIS.md`
- **Требования заказчика:** `research/QUESTIONNAIRE_ANALYSIS.md`
