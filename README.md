# Social Saver

![Python](https://img.shields.io/badge/Python-Backend-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Status](https://img.shields.io/badge/Status-Active-success)

Social Saver is a centralized platform designed to save, organize, and manage content from various social media platforms. It utilizes AI to structure saved links and provides a unified interface for accessing collected data from Instagram, YouTube, Twitter, and web blogs.

## Core Features

* **Multi-Platform Support:** Save and categorize links from major social media platforms and blogs.
* **AI-Powered Organization:** Automatic summarization and structured data handling using OpenAI.
* **WhatsApp Integration:** Ability to interact with the service and save content via Twilio for WhatsApp.
* **Hybrid Database Support:** Flexible configuration for local development with SQLite or production deployment with PostgreSQL.
* **Visual Dashboard:** Interactive web interface for managing saved items and viewing AI-generated summaries.

---

## <img src="https://img.icons8.com/ios-filled/20/000000/picture.png"/> Interface

### Dashboard

![Dashboard](./Dashboard.png)

### Chat Window

![Chat Window](./Chatwindow.png)

### AI Summary

![AI Summary](./AiSummary.png)

---

## <img src="https://img.icons8.com/ios-filled/20/000000/info.png"/> Overview

This project provides a system for saving and organizing links from multiple platforms.
It focuses on structured storage and AI-assisted organization of saved content.

---

## <img src="https://img.icons8.com/ios-filled/20/000000/settings.png"/> Setup

### 1. Create a `.env` file

```
SECRET_KEY=your_random_secret_key
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# PostgreSQL — leave blank to use local SQLite
# DATABASE_URL=postgresql://avnadmin:<password>@<host>:<port>/defaultdb?sslmode=require
```

On Render: add `DATABASE_URL` as an Environment Variable using your Aiven connection string.
Locally: leave it unset — SQLite is used automatically.

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Start the app

```bash
uvicorn app.main:app --reload --port 8000
```

Open:
http://localhost:8000

---

## <img src="https://img.icons8.com/ios-filled/20/000000/database.png"/> Configuration Notes

* Uses SQLite by default when `DATABASE_URL` is not provided
* Supports PostgreSQL via environment configuration
* External services require valid API keys

---

## <img src="https://img.icons8.com/ios-filled/20/000000/link.png"/> Purpose

The repository demonstrates:

* Link storage and retrieval workflow
* Integration with external APIs
* AI-based processing for organizing saved content
* Backend service setup and configuration

---
