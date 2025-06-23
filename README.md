Warehouse Management System
A full-stack warehouse management application built with Django REST Framework (backend) and React (frontend). The system allows users to manage products, warehouses, stock movements, transfers, orders, inventory, and more, with role-based access control and multilingual support.
Table of Contents

Features
Tech Stack
Prerequisites
Installation
Running the Application
Usage
Testing
Contributing
License

Features

User Authentication: JWT-based login with role-based access (admin, warehouse_manager, clerk, logistician, analyst).
Warehouse Management: Create, edit, and delete warehouses (admin and warehouse_manager roles).
Product Management: Manage products with categories, SKUs, and QR codes.
Stock Movements: Track incoming and outgoing stock with filtering by warehouse, operation, and date.
Stock Transfers: Transfer products between warehouses (admin, warehouse_manager, logistician).
Orders: Create and manage supply and demand orders.
Inventory Checks: Conduct inventory audits with discrepancy tracking.
Analytics: Visualize stock balance and movements with Chart.js.
Notifications: Real-time notifications for low stock and other events.
Audit Logs: Track user actions (admin only).
Multilingual Support: English and Russian via react-i18next.
Dark/Light Theme: Toggle between themes with persistence.

Tech Stack

Backend:
Django 4.x
Django REST Framework
PostgreSQL/SQLite (configurable)
Redis (for caching and Celery)
Celery (for asynchronous tasks)
Simple JWT (for authentication)


Frontend:
React 18
Vite (build tool)
Tanstack Query (data fetching)
Chart.js (data visualization)
Framer Motion (animations)
React Toastify (notifications)
Tailwind CSS (styling)


Others:
Docker (optional for deployment)
Git (version control)



Prerequisites

Python 3.10+
Node.js 18+
Redis 7.x
PostgreSQL (optional; SQLite used by default)
Git
Docker (optional for containerized setup)

Installation

Clone the Repository:
git clone https://github.com/AdilSatuva/Warehouse-API.git
cd Warehouse-API


Backend Setup:
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

Create a .env file in backend/core:
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0

Run migrations:
python manage.py migrate

Create test users:
python manage.py shell

from warehouse.models import User
users_data = [
    {'username': 'admin_user', 'password': 'Admin123!', 'email': 'admin@example.com', 'role': 'admin'},
    {'username': 'manager_user', 'password': 'Manager123!', 'email': 'manager@example.com', 'role': 'warehouse_manager'},
]
for user_data in users_data:
    if not User.objects.filter(username=user_data['username']).exists():
        User.objects.create_user(**user_data)
exit()


Frontend Setup:
cd ../frontend
npm install

Create a .env file in frontend:
VITE_API_URL=http://localhost:8000


Redis Setup:

Install Redis: Follow instructions for your OS (e.g., brew install redis on macOS, apt install redis-server on Ubuntu).
Start Redis:redis-server





Running the Application

Backend:
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python manage.py runserver


Celery (for async tasks):
cd backend
celery -A core worker --loglevel=info


Frontend:
cd frontend
npm run dev


Access the Application:

Frontend: http://localhost:5177
Backend API: http://localhost:8000/api/
Admin Panel: http://localhost:8000/admin/ (login with admin_user/Admin123!)



Usage

Login:

Navigate to http://localhost:5177/login.
Use credentials:
Admin: admin_user / Admin123!
Manager: manager_user / Manager123!




Manage Warehouses:

Go to /warehouses.
Admins and warehouse managers can add/edit/delete warehouses.
Example: Add a warehouse with Name: Main Storage, Type: storage, Location: City A.


Other Features:

Products: Manage products at /products.
Stock Movements: Track movements at /movements.
Transfers: Transfer stock at /transfers (admin, warehouse_manager, logistician).
Orders: Manage orders at /orders.
Inventory: Conduct audits at /inventory.
Analytics: View charts at /analytics (admin, analyst).
Notifications: Check alerts at /notifications.
Users: Manage users at /users (admin only).
Audit Logs: View logs at /audit (admin only).
Settings: Change language/theme at /settings.



Testing

Backend Tests:
cd backend
python manage.py test


Frontend Tests:

Add testing setup (e.g., Jest, Vitest) if needed:cd frontend
npm install --save-dev vitest
npm run test




Manual Testing:

Test warehouse creation:
Log in as admin_user.
Add a warehouse and verify it appears in the table.


Check API responses using curl:TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ -d '{"username":"admin_user","password":"Admin123!"}' -H "Content-Type: application/json" | jq -r .access)
curl -X GET http://localhost:8000/api/warehouses/ -H "Authorization: Bearer $TOKEN"





Contributing

Fork the repository.
Create a branch: git checkout -b feature/your-feature.
Commit changes: git commit -m "Add your feature".
Push to branch: git push origin feature/your-feature.
Open a pull request.

License
MIT License. See LICENSE for details.