from warehouse.models import User

# Список ролей и соответствующих данных пользователей
users_data = [
    {'username': 'admin_user', 'password': 'Admin123!', 'email': 'admin@example.com', 'role': 'admin'},
    {'username': 'manager_user', 'password': 'Manager123!', 'email': 'manager@example.com', 'role': 'warehouse_manager'},
    {'username': 'clerk_user', 'password': 'Clerk123!', 'email': 'clerk@example.com', 'role': 'clerk'},
    {'username': 'logistician_user', 'password': 'Logistician123!', 'email': 'logistician@example.com', 'role': 'logistician'},
    {'username': 'analyst_user', 'password': 'Analyst123!', 'email': 'analyst@example.com', 'role': 'analyst'},
]

# Создание пользователей
for user_data in users_data:
    if not User.objects.filter(username=user_data['username']).exists():
        user = User.objects.create_user(
            username=user_data['username'],
            password=user_data['password'],
            email=user_data['email'],
            role=user_data['role']
        )
        print(f"Created user: {user.username} with role: {user.role}")
    else:
        print(f"User {user_data['username']} already exists")

exit()