# PodBin — Autonomous Podcast Operations Platform

> An agentic AI operating system for podcasters. Autonomous research, production, and distribution — with human-in-the-loop control.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Authentication & Security](#authentication--security)
- [Environment Configuration](#environment-configuration)
- [Development Guidelines](#development-guidelines)
- [Deployment](#deployment)

---

## Overview

**PodBin** is an autonomous podcast management platform that streamlines the entire podcast workflow—from content creation to distribution. The platform uses AI agents (LangGraph) to automate research, transcription, editing, and social media clip generation, while providing creators with full control and oversight.

### Key Value Proposition

- **Autonomous Workflow**: Automatically processes podcast episodes through research, transcription, and clip generation
- **Multi-Platform Distribution**: Schedule and publish clips across TikTok, YouTube, Instagram, and Twitter
- **Smart Clip Generation**: AI-powered extraction of engaging snippets with platform-specific optimization
- **Creator Control**: Human-in-the-loop approvals and override capabilities at every stage
- **Analytics Dashboard**: Track performance metrics across platforms and episodes

---

## Features

### Core Features

#### 📊 Dashboard
- Workspace overview with episode count and project status
- Real-time analytics on clip performance
- Recently generated clips display with platform distribution
- Quick-access upload interface

#### 🎙️ Episode Management
- Create episodes with guest information
- Support for audio/video uploads (URL or file)
- Raw media transcription and processing
- Episode status tracking (Pre-Production → Production → Post-Production → Growth)

#### 🎬 Clip Generation
- Autonomous clip creation from episodes
- Multi-platform support (TikTok, YouTube, Instagram, Twitter)
- Duration-based optimization per platform
- Batch processing with progress tracking

#### 👥 User & Admin Management
- Role-based access control (Admin, User)
- API key management with format validation
- Real API validation (OpenAI, Deepgram, ElevenLabs)
- User invitation system

#### 🔌 Integrations
- **OpenAI**: GPT-4 for content analysis and clip generation
- **Deepgram**: Speech-to-text transcription
- **ElevenLabs**: Text-to-speech for voice-overs
- **Distribution Channels**: TikTok, YouTube, Instagram, Twitter APIs

#### 🔐 Security
- JWT-based authentication with 30-minute token expiration
- API key validation against actual service endpoints
- Environment-based secret management
- Role-based endpoint protection

---

## Tech Stack

### Backend
- **Framework**: FastAPI 0.100.0+
- **Server**: Uvicorn
- **AI Orchestration**: LangGraph + LangChain
- **Language Models**: OpenAI API
- **Database**: MongoDB (via Motor/Beanie ORM)
- **Authentication**: PyJWT 2.13.0
- **HTTP Client**: httpx 0.25.0+
- **Environment**: Python 3.9+

### Frontend
- **Framework**: React 18+ with TypeScript
- **Router**: TanStack React Router
- **State Management**: TanStack React Query
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **Icons**: Lucide React
- **UI Components**: Custom Shadcn/ui-inspired components

### DevOps
- **Containerization**: Docker & Docker Compose
- **Environment Management**: Python venv
- **Package Management**: pip (Python), npm (Node.js)

---

## Architecture

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PodBin Platform                          │
├──────────────────────┬──────────────────┬──────────────────┤
│   Frontend (React)   │  Backend (FastAPI)  │  AI Agents    │
│                      │                      │ (LangGraph)   │
├──────────────────────┼──────────────────┬──────────────────┤
│ • Dashboard          │ • REST API       │ • Research      │
│ • Episodes           │ • Auth System    │ • Transcription │
│ • Clips Management   │ • File Upload    │ • Clip Gen      │
│ • Settings           │ • Admin Panel    │ • Distribution  │
└──────────────────────┴──────────────────┴──────────────────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ MongoDB │         │ OpenAI  │         │ Social  │
   │         │         │ Deepgram│         │ Media   │
   │ (Data)  │         │ 11Labs  │         │ APIs    │
   └─────────┘         └─────────┘         └─────────┘
```

### Data Flow

1. **Episode Ingestion**: User uploads audio/video file
2. **Transcription**: Deepgram processes media → transcription
3. **Analysis**: OpenAI analyzes content for key points
4. **Clip Generation**: AI extracts and optimizes clips for platforms
5. **Approval**: Admin reviews and approves clips
6. **Distribution**: Scheduled publication across social platforms
7. **Analytics**: Performance tracking and reporting

---

## Project Structure

```
podbin/
├── backend/                          # Python FastAPI backend
│   ├── main.py                       # Entry point
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Container image
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app setup
│   │   ├── agents/                   # LangGraph AI agents
│   │   │   ├── __init__.py
│   │   │   ├── graph.py             # Agent workflow
│   │   │   └── state.py             # Agent state definitions
│   │   ├── api/                      # REST API endpoints
│   │   │   ├── v1/
│   │   │   │   ├── admin.py         # Admin endpoints
│   │   │   │   ├── agents.py        # Agent management
│   │   │   │   ├── approvals.py     # Approval workflows
│   │   │   │   ├── auth.py          # Authentication
│   │   │   │   ├── distribution.py  # Social media APIs
│   │   │   │   ├── episodes.py      # Episode CRUD
│   │   │   │   ├── integrations.py  # Third-party integrations
│   │   │   │   └── settings.py      # User settings
│   │   ├── core/
│   │   │   ├── config.py            # Configuration
│   │   │   └── security.py          # JWT & API key validation
│   │   ├── models/                  # Database models
│   │   │   ├── episode.py
│   │   │   └── user.py
│   │   ├── services/                # Business logic
│   │   │   ├── db.py               # Database service
│   │   │   ├── distribution.py     # Distribution logic
│   │   │   ├── env_manager.py      # Environment management
│   │   │   └── llm.py              # LLM interactions
│   └── static/                       # Static files
│       ├── avatars/
│       └── uploads/
│
├── frontend/                         # React TypeScript frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── main.tsx                 # React entry
│   │   ├── router.tsx               # Route definitions
│   │   ├── server.ts                # SSR server
│   │   ├── start.ts                 # Start config
│   │   ├── styles.css               # Global styles
│   │   ├── components/
│   │   │   ├── Layout.tsx           # Main layout wrapper
│   │   │   ├── theme-provider.tsx  # Theme context
│   │   │   ├── NotificationModal.tsx
│   │   │   ├── layout/
│   │   │   │   ├── AdminLayout.tsx
│   │   │   │   └── UserLayout.tsx
│   │   │   └── ui/                 # Reusable UI components
│   │   ├── context/
│   │   │   ├── AuthContext.tsx     # Auth state
│   │   │   └── NotificationContext.tsx
│   │   ├── hooks/
│   │   │   └── use-mobile.tsx
│   │   ├── lib/
│   │   │   ├── api.ts              # API client
│   │   │   ├── error-capture.ts
│   │   │   ├── error-page.ts
│   │   │   ├── status-badge.ts
│   │   │   └── utils.ts
│   │   ├── routes/
│   │   │   ├── __root.tsx          # Root layout
│   │   │   ├── admin.tsx           # Admin dashboard
│   │   │   ├── agents.tsx          # Agents management
│   │   │   ├── analytics.tsx       # Analytics page
│   │   │   ├── approvals.tsx       # Approval queue
│   │   │   ├── budget.tsx          # Budget tracking
│   │   │   ├── dashboard.tsx       # User dashboard
│   │   │   ├── episodes.tsx        # Episodes listing
│   │   │   ├── index.tsx           # Home page
│   │   │   ├── login.tsx           # Login page
│   │   │   ├── settings.tsx        # User settings
│   │   │   ├── admin/              # Admin sub-routes
│   │   │   ├── dashboard/          # Dashboard sub-routes
│   │   │   └── episodes/           # Episodes sub-routes
│   │   └── assets/                 # Images, fonts
│   └── Dockerfile
│
├── docker-compose.yml               # Multi-container setup
└── README.md                        # This file
```

---

## Setup & Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Node.js**: 18 or higher
- **npm**: 9 or higher
- **Docker** & **Docker Compose** (optional, for containerized setup)
- **MongoDB**: Local or Atlas (cloud)

### Backend Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure environment** (create `.env`):
   ```env
   # Database
   MONGODB_URI=mongodb://localhost:27017/podbin
   
   # Authentication
   SECRET_KEY=your-secret-key-change-in-production
   
   # API Keys
   OPENAI_API_KEY=sk-...
   DEEPGRAM_API_KEY=dg-...
   ELEVENLABS_API_KEY=xi-...
   
   # Server
   DEBUG=True
   HOST=0.0.0.0
   PORT=8000
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment** (create `.env.local`):
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_APP_NAME=PodBin
   ```

3. **Build/dev setup**:
   ```bash
   npm run dev      # Development server
   npm run build    # Production build
   npm run preview  # Preview production build
   ```

---

## Running the Application

### Local Development (Terminal 1 - Backend)

```bash
cd backend
# Activate venv first
python main.py
# Backend runs on http://localhost:8000
```

### Local Development (Terminal 2 - Frontend)

```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5173
```

### Using Docker Compose

```bash
# From project root
docker-compose up

# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# MongoDB: localhost:27017
```

---

## API Documentation

### Base URL

Development: `http://localhost:8000`

### Authentication

All endpoints (except `/auth/login`) require JWT token in Authorization header:

```
Authorization: Bearer <token>
```

Tokens expire after 30 minutes and must be refreshed via login.

### Core Endpoints

#### Authentication

- **POST** `/auth/login`
  - Request: `{ email: string, password: string }`
  - Response: `{ access_token: string, user: UserObject }`

- **GET** `/auth/me`
  - Response: `UserObject`
  - Requires: Valid JWT token

#### Episodes

- **GET** `/v1/episodes`
  - Get all episodes
  - Query params: `search`, `stage`, `status`

- **POST** `/v1/episodes`
  - Create new episode
  - Body: `{ title, guest, audioUrl?, audioFile?, videoUrl? }`

- **GET** `/v1/episodes/{id}`
  - Get episode details

- **PUT** `/v1/episodes/{id}`
  - Update episode

- **DELETE** `/v1/episodes/{id}`
  - Delete episode

#### Clips

- **GET** `/v1/episodes/{id}/clips`
  - Get clips for episode

- **POST** `/v1/episodes/{id}/clips`
  - Generate clips for episode
  - Body: `{ count: number, platforms: string[] }`

#### Admin (requires admin role)

- **GET** `/v1/admin/users`
  - List all users

- **PUT** `/v1/admin/users/{user_id}/role`
  - Update user role

- **GET** `/v1/admin/api-keys`
  - Get API keys (masked)

- **PUT** `/v1/admin/api-keys`
  - Update API keys
  - Validates against actual services (OpenAI, Deepgram, ElevenLabs)

#### Settings

- **GET** `/v1/settings`
  - Get user settings

- **PUT** `/v1/settings`
  - Update settings

- **POST** `/v1/settings/api-connections`
  - Add API connection with validation

---

## Authentication & Security

### JWT Token System

- **Algorithm**: HS256
- **Expiration**: 30 minutes
- **Payload**: `{ user_id, exp, iat }`
- **Secret**: Environment variable `SECRET_KEY`

### API Key Validation

The system validates API keys against actual service endpoints:

1. **OpenAI** (`sk-*` prefix)
   - Test endpoint: `GET /v1/models`

2. **Deepgram** (`dg-*` prefix)
   - Test endpoint: `GET /v1/models`

3. **ElevenLabs** (`xi-*` or `pat-*` prefix)
   - Test endpoint: `GET /v1/user`

Invalid keys are rejected before storage with descriptive error messages.

### Security Best Practices

- ✅ Never commit `.env` files to version control
- ✅ Rotate `SECRET_KEY` in production
- ✅ Use HTTPS in production
- ✅ Implement rate limiting on public endpoints
- ✅ Sanitize user inputs
- ✅ Store sensitive data in environment variables

---

## Environment Configuration

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | Yes | N/A | MongoDB connection string |
| `SECRET_KEY` | Yes | N/A | JWT signing secret |
| `OPENAI_API_KEY` | No | N/A | OpenAI API key |
| `DEEPGRAM_API_KEY` | No | N/A | Deepgram API key |
| `ELEVENLABS_API_KEY` | No | N/A | ElevenLabs API key |
| `DEBUG` | No | False | Debug mode |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |

### Frontend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes | N/A | Backend API URL |
| `VITE_APP_NAME` | No | PodBin | Application name |

---

## Development Guidelines

### Code Style

- **Backend**: Follow PEP 8 conventions
- **Frontend**: Use ESLint and Prettier configs provided
- **Commits**: Use clear, descriptive commit messages

### Database Models

#### User Model
```python
{
  _id: ObjectId,
  email: string,
  password_hash: string,
  role: "User" | "Admin" | "Super Admin",
  status: "active" | "inactive",
  api_keys: { type: string, masked_key: string },
  created_at: datetime,
  updated_at: datetime
}
```

#### Episode Model
```python
{
  _id: ObjectId,
  title: string,
  guest: string,
  stage: "Pre-Prod" | "Post-Prod" | "Growth",
  status: "DRAFT" | "PROCESSING" | "LIVE",
  raw_audio_url: string,
  raw_video_url: string,
  duration: number,
  clips: Clip[],
  created_at: datetime,
  updated_at: datetime
}
```

#### Clip Model
```python
{
  _id: ObjectId,
  title: string,
  duration: number,
  thumbnail: string,
  status: "completed" | "processing" | "scheduled",
  platforms: string[],  // ["tiktok", "youtube", "instagram", "twitter"]
  created_at: datetime
}
```

### Adding New Endpoints

1. Create endpoint function in appropriate module (`api/v1/*.py`)
2. Add proper authentication with `verify_token()` or `verify_admin_token()`
3. Include request/response validation with Pydantic models
4. Add error handling with appropriate HTTP status codes
5. Document in API section of this README

### Frontend Component Guidelines

- Use TypeScript for type safety
- Keep components focused and composable
- Use React Query for server state management
- Implement error boundaries for error handling
- Use tailwind utility classes for styling

---

## Deployment

### Docker Deployment

1. **Build images**:
   ```bash
   docker build -t podbin-backend:latest ./backend
   docker build -t podbin-frontend:latest ./frontend
   ```

2. **Push to registry** (if needed):
   ```bash
   docker tag podbin-backend:latest your-registry/podbin-backend:latest
   docker push your-registry/podbin-backend:latest
   ```

3. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### Production Checklist

- [ ] Set `DEBUG=False` in backend environment
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure MongoDB for production (Atlas or self-hosted with replication)
- [ ] Set up log aggregation and monitoring
- [ ] Configure backup strategy for MongoDB
- [ ] Implement rate limiting and DDoS protection
- [ ] Set up CI/CD pipeline for automated deployments
- [ ] Configure environment-specific secrets management
- [ ] Implement health checks for containers
- [ ] Set up uptime monitoring and alerting

### Database Backup

```bash
# Backup MongoDB
mongodump --uri "mongodb://localhost:27017/podbin" --out ./backups

# Restore MongoDB
mongorestore --uri "mongodb://localhost:27017/podbin" ./backups/podbin
```

---

## Troubleshooting

### Backend Issues

**"Cannot import PyJWT"**
- Solution: `pip install PyJWT>=2.8.0`

**"API key validation fails"**
- Check that API keys are valid and have correct prefixes
- Verify network connectivity to external APIs
- Check API key permissions/scope

**"MongoDB connection refused"**
- Ensure MongoDB is running: `mongod`
- Check `MONGODB_URI` in `.env`
- Verify network connectivity

### Frontend Issues

**"Frontend cannot reach backend API"**
- Verify backend is running on configured port
- Check `VITE_API_URL` environment variable
- Check browser console for CORS errors

**"Theme not applying"**
- Clear browser cache and localStorage
- Check that `theme-provider.tsx` is properly loaded

**"Upload failed - HTTP error 413 (Payload Too Large)"**
- **Cause**: The uploaded media file (audio/video) exceeds the max payload size configured on the web server or reverse proxy.
- **Nginx Solution**: Add `client_max_body_size 500M;` (or `1G`) in your Nginx site configuration block (`/etc/nginx/sites-available/default`) and reload Nginx (`sudo nginx -s reload`).
- **Apache / cPanel Solution**: Add `LimitRequestBody 524288000` to `.htaccess`.
- **Workaround**: Alternatively, paste a public media URL (S3, Cloudflare, Drive) into the URL field in the upload modal instead of uploading a raw file directly.


---

## Support & Documentation

- **Issues**: Report bugs on GitHub Issues
- **Questions**: Check existing documentation and FAQ
- **Contributing**: Follow CONTRIBUTING.md guidelines

---

## License

PodBin is proprietary software. All rights reserved.

---

## Version Info

- **Backend**: FastAPI 0.100.0+
- **Frontend**: React 18+
- **Python**: 3.9+
- **Node.js**: 18+

Last Updated: July 2026
