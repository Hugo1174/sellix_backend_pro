# Sellix — Backend (MVP)

Мультиарендная B2B2C e-commerce платформа на **Django 5.2 + Django REST Framework**.
Соединяет четыре роли: Покупатель, Продавец, Производитель, Суперадмин.
Ключевой принцип — «один товар → много магазинов» (товар не копируется, а связывается
через `StoreProduct`).

## Архитектура

Модульный монолит. Локальные приложения в `apps/`:

| Приложение      | Назначение |
|-----------------|------------|
| `common`        | Базовые модели (UUID + timestamps), пагинация, обработка ошибок, права доступа по ролям, денежные хелперы |
| `accounts`      | Пользователь (единая учётка для всех ролей), OAuth (Яндекс ID / VK ID), JWT, выбор роли, адреса покупателя |
| `tenants`       | Магазин (`Store`), производитель (`Producer`), интеграции оплаты/доставки (`ShopIntegration`) |
| `integrations`  | Коннекторы провайдеров оплаты (ЮKassa/Т-Касса/CloudPayments) и доставки (СДЭК/Почта/Я.Доставка/Boxberry) с sandbox-режимом |
| `catalog`       | Категории, товары производителя (общий пул), фото, `StoreProduct` (наценка/видимость) |
| `storefront`    | Публичная витрина магазина по slug + корзина |
| `orders`        | **Ядро**: заказ, позиции со снимками цен, отгрузки по производителям, машина состояний, checkout |
| `payments`      | Платежи, webhook, sandbox-подтверждение, возвраты |
| `finance`       | Выплаты (`Payout`), реестр, расчёт «наценка → продавцу, отпускная цена → производителю» |
| `logistics`     | Webhook/опрос статусов доставки |
| `notifications` | Журнал и отправка статусных уведомлений (sandbox-лог) |
| `adminpanel`    | Дашборд, управление сущностями, блокировки, реестр выплат, карточка спора, аудит-лог |

Денежный поток (PRD 5): покупатель платит одной суммой → платформа удерживает →
после завершения заказа формируются выплаты (наценка продавцу + отпускная цена
каждому производителю + доставка перевозчику). Комиссия платформы на MVP — 0%.

## Установка

```bash
# 1. Зависимости
pip install -r requirements.txt

# 2. Конфигурация
cp .env.example .env          # отредактировать SECRET_KEY и БД при необходимости

# 3. БД (PostgreSQL уже настроена в .env: sellix_db / sellix_user)
python manage.py makemigrations
python manage.py migrate

# 4. Сид: суперадмин + категории
python manage.py seed_sellix --email admin@mysellix.ru --password admin12345

# 5. Запуск
python manage.py runserver        # dev
# gunicorn config.wsgi:application  # prod (gunicorn в requirements)
```

Документация API (Swagger): `/api/docs/`  ·  схема OpenAPI: `/api/schema/`
Все эндпоинты — под префиксом `/api/v1/`.

## Sandbox-режим

При `USE_SANDBOX_PROVIDERS=True` (по умолчанию) OAuth, оплата и доставка работают
без реальных ключей: можно пройти весь путь end-to-end. Для боевого режима —
выставить `False` и заполнить ключи провайдеров в `.env`.

## Сквозной тест (sandbox)

```bash
# 1. Вход покупателя (любой code принимается в sandbox)
curl -X POST /api/v1/auth/oauth/ -H 'Content-Type: application/json' \
  -d '{"provider":"yandex","code":"test123"}'
# → tokens.access, is_new=true

# Продавец и производитель: войти так же, затем выбрать роль:
curl -X POST /api/v1/me/role/ -H 'Authorization: Bearer <ACCESS>' \
  -d '{"role":"seller"}'      # и аналогично "producer" для второго пользователя

# 2. Производитель: профиль (авто-одобрение) → товар → фото → публикация
POST /api/v1/producer/profile/        {"company_name":"ООО Ромашка"}
POST /api/v1/producer/products/       {category, name, description, base_price, stock, weight_grams}
POST /api/v1/producer/products/<id>/images/   (multipart image)
POST /api/v1/producer/products/<id>/publish/

# 3. Продавец: магазин → подключить оплату → добавить товар из пула → наценка → видимость → публикация
POST /api/v1/seller/store/            {"name":"Мой магазин"}
POST /api/v1/integrations/            {"kind":"payment","provider":"yookassa","credentials":{}}
POST /api/v1/seller/products/add/     {"product_id":"<pool product id>"}
PATCH /api/v1/seller/products/<sp_id>/  {"markup_percent":"30","is_visible":true}
POST /api/v1/seller/store/publish/

# 4. Покупатель: витрина → checkout (создаёт заказ + платёж)
GET  /api/v1/shop/<slug>/products/
POST /api/v1/checkout/  {"store_slug":"<slug>","items":[{"store_product_id":"<id>","quantity":1}],
                         "address":{"full_name":"Иван","phone":"+7...","city":"Москва","address_line":"ул. ..."}}
# → payment.id, payment.confirmation_url

# 5. Эмуляция оплаты (sandbox) → заказ paid → авто sent_to_producer
POST /api/v1/payments/<payment_id>/sandbox-confirm/

# 6. Производитель: отгрузка
GET  /api/v1/producer/shipments/
POST /api/v1/producer/shipments/<id>/assemble/
POST /api/v1/producer/shipments/<id>/ship/      # генерит трек-номер

# 7. Доставка → delivered (webhook перевозчика) → авто completed → выплаты
POST /api/v1/logistics/webhook/cdek/  {"tracking_number":"<track>","status":"delivered"}

# 8. Суперадмин: дашборд и подтверждение выплат
POST /api/v1/auth/admin/  {"email":"admin@mysellix.ru","password":"admin12345"}
GET  /api/v1/admin-panel/dashboard/
GET  /api/v1/admin-panel/payouts/?status=pending
POST /api/v1/admin-panel/payouts/<id>/confirm/
```

## Машина состояний заказа (PRD 6.6)

```
created → paid → sent_to_producer → assembling → shipped → in_transit
        → ready_for_pickup → delivered → completed     (+ cancelled)
```
На MVP `completed == delivered` (авто-завершение). Переходы валидируются и пишутся
в журнал `OrderStatusEvent`.

## Замечания по продакшену

- Webhook оплаты (`/payments/webhook/<provider>/`) на MVP не проверяет подпись —
  перед боевым запуском добавить верификацию по секрету провайдера.
- `DISABLE_REDIS=True` использует локальный кэш в памяти; для прода — Redis.
- Реальные OAuth/оплата/доставка включаются переключателем `USE_SANDBOX_PROVIDERS=False`.
