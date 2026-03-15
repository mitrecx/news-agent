# News Agent - Vue.js Frontend

Modern Vue.js 3 + Vite + Element Plus frontend for the News Agent application.

## 🎯 Features

- ✅ **User Authentication** - JWT-based login system
- ✅ **Real-time Chat** - SSE streaming responses
- ✅ **Modern UI** - Element Plus component library
- ✅ **Responsive Design** - Mobile-friendly interface
- ✅ **TypeScript** - Full type safety
- ✅ **State Management** - Pinia with persistence
- ✅ **Gradient Theme** - Beautiful purple gradient design

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend server running on `http://localhost:8000`

### Installation

```bash
cd src/frontend-vue
npm install
```

### Development

```bash
# Start frontend (port 5173)
npm run dev

# Start backend (port 8000)
cd ../..
uv run python run.py
```

### Access

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Login

Use the test credentials:
- Username: `test`
- Password: `test123456`

## 📁 Project Structure

```
src/frontend-vue/
├── src/
│   ├── api/              # API client modules
│   │   ├── auth.ts       # Authentication API
│   │   └── chat.ts       # Chat API with SSE
│   ├── components/       # Vue components
│   │   ├── ChatInput.vue     # Message input component
│   │   └── ChatMessage.vue   # Message bubble component
│   ├── composables/      # Vue composables
│   │   ├── useChatStream.ts  # SSE streaming logic
│   │   └── useHealthCheck.ts # Health check polling
│   ├── router/           # Vue Router
│   │   └── index.ts      # Route definitions
│   ├── stores/           # Pinia stores
│   │   ├── auth.ts       # Authentication state
│   │   └── chat.ts       # Chat state
│   ├── types/            # TypeScript types
│   │   └── index.ts      # Type definitions
│   ├── utils/            # Utility functions
│   │   └── request.ts    # Axios instance with interceptors
│   ├── views/            # Page components
│   │   ├── LoginView.vue # Login page
│   │   └── ChatView.vue  # Chat page
│   ├── App.vue           # Root component
│   ├── main.ts           # Entry point
│   └── style.css         # Global styles
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript config
└── package.json          # Dependencies
```

## 🛠️ Tech Stack

- **Framework**: Vue 3 with Composition API
- **Build Tool**: Vite
- **UI Library**: Element Plus
- **State Management**: Pinia
- **Routing**: Vue Router
- **HTTP Client**: Axios
- **SSE**: @microsoft/fetch-event-source
- **Markdown**: markdown-it
- **Language**: TypeScript

## 🎨 Key Features

### Authentication

- JWT token stored in localStorage
- Automatic token injection via Axios interceptors
- Protected routes with navigation guards
- Token refresh and error handling

### Chat Interface

- Real-time streaming responses via SSE
- Message history management
- Auto-scroll to latest message
- Markdown rendering for AI responses
- Syntax highlighting for code blocks

### UI/UX

- Gradient purple theme matching original design
- Responsive layout for mobile and desktop
- Smooth animations and transitions
- Loading states and error handling
- Health status indicator

## 📦 Build for Production

```bash
npm run build
```

The build output will be in `dist/`.

### Serve Static Files

You can serve the built frontend with the FastAPI backend:

```bash
# Build the frontend
npm run build

# Copy to backend static directory
cp -r dist/* ../frontend/

# Or serve via nginx
```

## 🔧 Configuration

### Vite Config

[vite.config.ts](vite.config.ts)
- API proxy to `http://localhost:8000`
- Path alias `@/` for `src/`
- Dev server on port 5173

### Environment Variables

No environment variables needed for development. The API proxy handles all backend communication.

## 🧪 Testing

```bash
# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123456"}'

# Test health endpoint
curl http://localhost:8000/health

# Test SSE streaming
curl -N http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

## 📝 API Endpoints

### Authentication

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user

### Chat

- `POST /api/chat/stream` - Send message with streaming response

### Health

- `GET /health` - Check server and agent status

## 🐛 Troubleshooting

### CORS Issues

If you encounter CORS errors, ensure the backend has CORS configured for `http://localhost:5173`.

### Port Conflicts

If port 5173 is in use, modify `vite.config.ts`:

```typescript
server: {
  port: 3000,  // Change to available port
  // ...
}
```

### Module Resolution

If you see import errors, ensure `@/` alias is configured in both:
- `vite.config.ts` - Vite resolution
- `tsconfig.app.json` - TypeScript resolution

## 🚀 Deployment

### Development

1. Start backend: `uv run python run.py`
2. Start frontend: `npm run dev`
3. Open: http://localhost:5173

### Production

1. Build: `npm run build`
2. Deploy `dist/` to static file server (Nginx, S3, etc.)
3. Configure backend CORS for production domain
4. Update API base URL if needed

## 📄 License

Same as parent project.

## 🤝 Contributing

1. Follow Vue 3 Composition API patterns
2. Use TypeScript for type safety
3. Test on mobile devices
4. Maintain gradient theme consistency

