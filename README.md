# Warehouse Management System

Система управления складом — это веб-приложение для учета товаров, движений, пользователей и аудита. Проект состоит из бэкенда (Django) и фронтенда (React с Vite). Приложение поддерживает локализацию (RU/EN), анимации (`framer-motion`), графики (`chart.js`) и адаптивный дизайн (`Tailwind CSS`).

## Требования

- **Python**: 3.10+
- **Node.js**: 18+
- **PostgreSQL**: 13+ (или SQLite для разработки)
- **Операционная система**: Windows/Linux/MacOS
- **Git** (для клонирования репозитория, если применимо)

## Установка

### 1. Клонирование репозитория (если проект в Git)
```bash
git clone <repository-url>
cd гулаша

Если проект уже на вашем компьютере, перейдите в папку:
cd C:\Users\Admin\Desktop\Новая папка\гулайша

2. Настройка бэкенда

Создайте виртуальное окружение:
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/MacOS


Установите зависимости:
pip install -r requirements.txt

Если requirements.txt отсутствует, установите:
pip install django==4.2.16 djangorestframework django-cors-headers psycopg2-binary python-decouple drf-yasg


Настройте .env:В корне проекта создайте файл .env:
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # или postgresql://user:password@localhost:5432/dbname


Примените миграции:
python manage.py makemigrations
python manage.py migrate


Создайте суперпользователя:
python manage.py createsuperuser

Логин: admin, пароль: admin123 (или свои).

Запустите бэкенд:
python manage.py runserver

Сервер доступен на http://localhost:8000.


3. Настройка фронтенда

Перейдите в папку фронтенда:
cd frontend


Установите зависимости:
npm install

Или установите вручную:
npm install react-router-dom axios chart.js react-i18next i18next framer-motion lucide-react


Запустите фронтенд:
npm run dev

Приложение доступно на http://localhost:5176.


4. Проверка работы

Откройте http://localhost:5176 в браузере.
Войдите с учетными данными суперпользователя (admin/admin123).
Проверьте вкладки: Дашборд, Товары, Движения, Низкий запас, Пользователи, Журнал аудита.

Деплой
Бэкенд (Heroku как пример)

Установите Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli
Создайте приложение:heroku create your-app-name


Настройте .env на Heroku:heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
heroku config:set DATABASE_URL=postgresql://...


Разверните бэкенд:git push heroku main
heroku run python manage.py migrate



Фронтенд (Vercel как пример)

Установите Vercel CLI:npm install -g vercel


Разверните фронтенд:cd frontend
vercel


Настройте переменные окружения в Vercel (API_URL: https://your-app-name.herokuapp.com/api).
Укажите в vite.config.js:server: {
  proxy: {
    '/api': {
      target: 'https://your-app-name.herokuapp.com',
      changeOrigin: true,
    },
  },
}



Функционал
1. Аутентификация

Вход: Пользователь вводит логин и пароль (/login).
Выход: Кнопка "Выйти" в Sidebar очищает токен и перенаправляет на /login.
Защита маршрутов: Только авторизованные пользователи имеют доступ к вкладкам (ProtectedRoute).

2. Дашборд

Отображает графики (столбчатая диаграмма запасов, круговая диаграмма по складам) с помощью chart.js.
Кнопка "Скачать CSV" экспортирует данные о запасах.
Анимации появления графиков через framer-motion.

3. Товары

Список товаров с фильтром по поиску (по названию/SKU).
Добавление товара через модальное окно (Modal.jsx).
Пагинация (кнопки "Предыдущая"/"Следующая").

4. Движения

Список движений с фильтрами (склад, операция, даты, поиск).
Добавление движения (приход/расход) через модальное окно.
Пагинация.

5. Низкий запас

Список товаров с количеством ниже минимального запаса.
Пагинация.

6. Пользователи

Список пользователей с возможностью назначения ролей (Кладовщик, Менеджер, Админ).
Добавление пользователя через модальное окно.

7. Журнал аудита

Отображает действия пользователей (кто, что, когда).
Пагинация.

8. Локализация

Переключение языка (RU/EN) в Sidebar и header.
Все тексты переведены (i18n.js).

9. Дизайн

Сворачиваемый Sidebar с анимацией (framer-motion).
Адаптивный интерфейс (Tailwind CSS).
Иконки из lucide-react.
Плавные анимации переходов страниц (AnimatePresence).

Логи

Бэкэнд: C:\Users\Admin\Desktop\Новая папка\гулайша\logs\warehouse.log.
Фронтенд: Консоль браузера (F12`).

Для презентации

Демонстрация:

Войдите как admin/admin123.
Покажите графики на Дашборде, добавление товара/движения, переключение языка.
Откройте/сверните Sidebar.
Покажите адаптивность на мобильном устройстве.


Скриншоты:

Дашборд с графиками.
Список товаров с фильтром.
Модальное окно добавления.
Sidebar в открытом/закрытом состоянии.


Описание в отчете:

Реализована система управления складом с REST API (Django) и фронтендом (React).
Поддержка локализации, анимаций, графиков.
Адаптивный дизайн и защита маршрутов.
Деплой на Heroku/Vercel.



Устранение ошибок

401 Unauthorized: Проверьте токен в localStorage и настройки CORS в settings.py.
Ошибки фронтенда: Откройте консоль (F12) и проверьте логи.
Ошибки бэкенда: Проверьте warehouse.log.

Если возникнут проблемы, свяжитесь с разработчиком или проверьте логи.```
