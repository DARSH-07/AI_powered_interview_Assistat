# AI-Powered Interview Assistant

A Django-based interview assistant that conducts AI-powered technical interviews for candidates and provides a dashboard for interviewers.

## Features

- **Resume Upload & Parsing**: Automatically extract candidate information from PDF/DOCX resumes
- **Real-time Interview**: Timed AI-generated questions with automatic progression
- **Two-Tab Interface**: 
  - Interviewee chat interface
  - Interviewer dashboard with candidate scores and summaries
- **Data Persistence**: Local storage with session recovery
- **WebSocket Integration**: Real-time updates between tabs

## Setup Instructions

1. **Install Dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m nltk.downloader stopwords punkt averaged_perceptron_tagger universal_tagset wordnet brown maxent_ne_chunker words
```

2. **Environment Variables**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
GEMINI_API_KEY=AIzaSyDdmA7awAzmhrU8Ob0BSnpOM7I2-xONxUo
ALLOWED_HOSTS=localhost,127.0.0.1
```

3. **Database Setup**
```bash
python manage.py makemigrations
python manage.py migrate
```

4. **Run Redis Server**
```bash
redis-server
```

5. **Run Django Application**
```bash
python manage.py runserver
```

## Project Structure

```
interview_assistant/
├── manage.py
├── requirements.txt
├── .env
├── interview_assistant/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── routing.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── consumers.py
│   ├── utils.py
│   ├── admin.py
│   └── apps.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── templates/
│   ├── base.html
│   ├── interview.html
│   └── dashboard.html
└── media/
    └── resumes/
```

## Usage

1. Navigate to the application URL
2. **Interviewee Tab**: Upload resume, complete missing information, take the interview
3. **Interviewer Tab**: View candidates, scores, and detailed interview summaries
4. Data persists across browser sessions with automatic recovery

## AI Integration

Uses Google Gemini API for:
- Dynamic question generation based on full-stack development roles
- Answer evaluation and scoring
- Final candidate assessment and summary generation

## Question Structure

- **2 Easy Questions** (20 seconds each)
- **2 Medium Questions** (60 seconds each) 
- **2 Hard Questions** (120 seconds each)

## Technologies Used

- **Backend**: Django, Django Channels, WebSockets
- **AI**: Google Gemini API
- **Storage**: Redis for sessions, SQLite for data
- **Resume Parsing**: PyPDF2, python-docx, pyresparser
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Real-time**: WebSockets for tab synchronization