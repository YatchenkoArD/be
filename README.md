# Beauty Platform API 
 
## Установка и запуск 
 
1. Создание виртуального окружения: 
```bash 
python -m venv venv 
``` 
 
2. Активация виртуального окружения: 
- Windows: `venv\Scripts\activate` 
- Linux/Mac: `source venv/bin/activate` 
 
3. Установка зависимостей: 
```bash 
pip install -r requirements.txt 
``` 
 
4. Запуск приложения: 
```bash 
python main.py 
``` 
 
## API Endpoints 
- GET /api/v1/users/ - список пользователей 
- GET /api/v1/services/ - список услуг 
- GET /api/v1/appointments/ - список записей 
## надо будет сделать Конвертации времени сейчас у нас строка