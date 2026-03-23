# AskAcademia

An AI-powered academic assistant chatbot for RGUKT (Rajiv Gandhi University of Knowledge Technologies) that helps students with academic queries, rules, and regulations.

## Features

- AI-powered chatbot for academic queries
- Support for multiple engineering departments (Civil, CSE, ECE, EEE, Mechanical, MME)
- Academic rules and regulations information
- Interactive chat interface
- Dark/Light theme support

## Tech Stack

### Backend
- Python
- FastAPI
- ChromaDB for vector storage
- HuggingFace embeddings

### Frontend
- React
- Vite
- Tailwind CSS

## Project Structure

```
Rgukt-bot/
├── app/                    # Backend application
│   ├── app.py             # FastAPI app
│   ├── main.py           # Main application logic
│   ├── models.py         # Data models
│   ├── schemas.py        # Pydantic schemas
│   ├── services.py       # Business logic
│   └── utils.py          # Utilities
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   └── utils/        # Utilities
│   └── package.json
├── server.py              # Server entry point
├── start_server.py       # Server startup script
├── requirements.txt      # Python dependencies
└── README.md
```

## Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the backend server:
```bash
python server.py
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

## Environment Variables

Create a `.env` file in the root directory with the following:
- `GROQ_API_KEY` - Groq API key for LLM
- `HF_TOKEN` - HuggingFace token

## Deployment

### Backend
The backend can be deployed on any Python-supported platform (Render, Railway, Fly.io, etc.)

### Frontend
The frontend can be deployed on Vercel, Netlify, or any static hosting service.

## License

MIT License
