# Reward Activity / Vertex

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)

## Introduction
Reward Activity / Vertex is a Django-based platform that enables users to manage and track reward activities efficiently. The application is designed to be scalable and easy to use.

## Features
- User authentication and authorization
- Reward management
- Activity tracking
- Admin interface for easy management
- API endpoints for integration

## Setup and Installation
### Prerequisites
- Python 3.8 or higher
- Django 3.2 or higher
- PostgreSQL
- Redis (for caching and task queue)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/reward-activity-vertex.git
   cd reward-activity-vertex
   ```
2. Create a virtual environment and activate it
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the dependencies
  ```bash
  pip install -r requirements.txt
  ```
4. Setup the database
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Run the development Server
   ```bash
   python manage.py runserver
   ```
## Usage
Visit http://localhost:8000 to access the application.
Use the admin interface at http://localhost:8000/admin to manage reward activities and users.
## Running Tests
To run the tests, use the following command:
```bash
python manage.py test
```
## License
This project is licensed under the MIT License.


