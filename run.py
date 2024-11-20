# run.py

from app import create_app, db

app = create_app()

# Создание базы данных при старте приложения
with app.app_context():
    db.create_all()  # Создает все таблицы, указанные в моделях

if __name__ == "__main__":
    app.run(debug=True)
