<img width="1892" height="854" alt="image" src="https://github.com/user-attachments/assets/92c5284d-a34e-4d98-b0c2-e94353c3757c" />

# DJ Rest API Boilerplate

A production-ready boilerplate for Django REST APIs with WebSockets and async task support.

## Features

- **Django REST Framework:** For building robust APIs quickly.
- **WebSockets:** Real-time support via Django Channels.
- **Async Tasks:** Background job processing (e.g., Celery).
- **Authentication:** Pre-configured `oauth` module.
- **Modular Design:** Clean, scalable project structure.

## Quick Start

1.  **Clone the repo:**

    ```sh
    git clone [https://github.com/your-username/dj-rest-api.git](https://github.com/your-username/dj-rest-api.git)
    cd dj-rest-api
    ```

2.  **Setup environment & install dependencies:**

    ```sh
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Migrate and run:**
    ```sh
    python manage.py migrate
    python manage.py runserver
    ```

Your API is now live at `http://127.0.0.1:8000`.
