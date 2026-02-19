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

## Изоляция и рабочее окружение

**КРИТИЧЕСКИ ВАЖНО:** Этот проект полностью изолирован от остальных проектов в портфолио.

### Рабочая директория
- **Путь:** `/Users/sergeigein/Documents/Project Claude/WB-Repricer/`
- Работаем **ТОЛЬКО** в этой директории и её поддиректориях
- **НЕ трогать** файлы и сервисы других проектов (YoutubeComment, FullFilment, Personal Assistent и т.д.)

### Репозиторий
- **GitHub:** `https://github.com/sergeigeyn/WB-Repricer.git`
- **Remote:** `origin`
- **Основная ветка:** `main`

### Сервер PriceForge
- Проект развёрнут на **ОТДЕЛЬНОМ сервере** (НЕ 83.222.25.226 / golosai.online)
- **НЕ использует** общий n8n-сервер, общий PostgreSQL, общий Redis других проектов
- Отдельный VPS, отдельная БД, отдельный Redis

### Локальные файлы с секретами (НЕ в git!)
Все чувствительные данные хранятся ТОЛЬКО локально, НИКОГДА не коммитятся:
- **`.server-credentials`** — SSH-доступ к серверу (IP, логин, пароль)
- **`scripts/ssh_cmd.sh`** — скрипт SSH-подключения (содержит пароль)
- **`backend/.env`** — переменные окружения для локальной разработки
Все эти файлы перечислены в `.gitignore`.

### Правила безопасности при git push
1. **НИКОГДА** не коммитить файлы с паролями, API-ключами, токенами
2. **ВСЕГДА** проверять `git diff --cached` перед коммитом на наличие секретов
3. **НЕ добавлять** IP-адрес сервера, SSH-пароли, production-пароли в коммиты
4. В `.env.example` только плейсхолдеры (`change-me-in-production`)

### Правила изоляции
1. **НЕ подключаться** к серверу 83.222.25.226 — это сервер других проектов
2. **НЕ использовать** n8n API ключи из `FullFilment/config/`
3. **НЕ использовать** SSH-доступ `root@83.222.25.226`
4. **НЕ создавать** таблицы в общей БД n8n
5. Все ресурсы (сервер, БД, Redis, домен) — свои собственные, отдельные

## Контакты и ресурсы

- **WB API документация:** https://openapi.wildberries.ru/
- **WB Dev Portal:** https://dev.wildberries.ru/
- **Референс UI:** Indeepa (https://indeepa.com/) — интерфейс и структура
- **Анализ конкурентов:** `research/COMPETITOR_ANALYSIS.md`
- **Требования заказчика:** `research/QUESTIONNAIRE_ANALYSIS.md`
