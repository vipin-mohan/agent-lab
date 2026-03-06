# PM Career Coach

An AI-powered career coaching app for aspiring and current product managers — built with Python, Streamlit, and modern LLMs (Anthropic Claude, OpenAI, and Google Gemini).

**[Live Demo →](https://agent-lab-career-coach.streamlit.app/)**

> ⏱ Hosted on Streamlit Community Cloud free tier — may take 30–60 seconds to wake up on first visit.

---

## What It Does

PM Career Coach gives you structured, personalized coaching across four key areas of your PM job search:

- **Interview Prep**: Paste your background and target role, and get tailored PM interview questions, STAR-structured story guidance, and delivery tips specific to your experience.
- **Gap Analysis**: Understand where you stand relative to hiring expectations for your target roles, and get a concrete 30–90 day development plan to close the most important gaps.
- **Career Positioning**: Craft a compelling PM narrative, positioning statement, and reusable lines for your resume, LinkedIn headline, and recruiter conversations.
- **Job Match Score**: Paste your resume and a job description side by side, and get a structured match analysis — an overall score out of 10, your strongest signals, gaps to address, positioning guidance, and specific resume tweaks to improve your fit.

All four flows share a common foundation: an expert PM career coach persona with 10+ years of experience working with MBA students and early-career PMs.

---

## Why I Built This

I've been coaching MBA students at UC Berkeley Haas for nearly 5 years — over 250 one-on-one sessions helping candidates break into PM roles at Amazon, Google, Meta, Apple, OpenAI and others.

In those sessions I saw the same patterns repeatedly: strong candidates struggling to structure their stories, articulate their differentiation, or close skill gaps efficiently.

This app is different from generic PM coaching tools. The AI responses are grounded in a knowledge base built from my actual coaching notes — real patterns, real mistakes, real advice that worked. When you ask for a gap analysis or interview prep, the app retrieves the most relevant coaching insights from those 250+ sessions and uses them to inform the response.

## How It Works

1. You enter your background, target role, and questions
2. The app searches a vector database of 250+ real coaching sessions for the most relevant patterns
3. Those patterns are injected into the AI prompt alongside your inputs
4. Claude synthesizes the coaching wisdom with your specific situation to generate a personalized response

This means responses are grounded in real PM hiring patterns — not just what a general-purpose AI knows about product management.

---

## Tech Stack

- **Frontend:** Streamlit
- **AI:** Anthropic Claude (claude-sonnet-4-6), with automatic fallback to OpenAI (gpt-4.1-mini) and Google Gemini (gemini-2.0-flash)
- **RAG Pipeline:** sentence-transformers (all-MiniLM-L6-v2) for embeddings, Pinecone for cloud vector storage
- **Language:** Python 3.11+
- **Hosting:** Streamlit Community Cloud

---

## Repository Layout

Key pieces of this repo:

- `pm_career_coach_app/pm_career_coach_app.py` — main Streamlit app.
- `requirements.txt` — Python dependencies for the app (also mirrored at `pm_career_coach_app/requirements.txt`).
- `task-api/` — a separate FastAPI-based task API experiment (not required to run PM Career Coach).

---

## Getting Started (Local)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/pm-career-coach.git
cd pm-career-coach
```

### 2. (Recommended) Create and activate a virtual environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell on Windows
# or
source .venv/bin/activate      # macOS / Linux
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Add your API keys

Create a `.env` file in the repo root (this is used for local development only — do **not** commit it):

```bash
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

You only need **one** of these for the app to work; if multiple are set, the app uses them in this order:

1. `ANTHROPIC_API_KEY`
2. `OPENAI_API_KEY`
3. `GEMINI_API_KEY`

### 5. Run locally

From the repo root:

```bash
streamlit run pm_career_coach_app/pm_career_coach_app.py
```

Then open the URL printed in the terminal (typically `http://localhost:8501`).

---

## Deploying to Streamlit Cloud

1. **Push to GitHub**

   - Ensure `.env` is in your `.gitignore` so you never commit secrets.

2. **Create an app on Streamlit Community Cloud**

   - Go to `https://share.streamlit.io` and connect your GitHub repo.
   - When asked for the app entrypoint, use:
     - **Main file**: `pm_career_coach_app/pm_career_coach_app.py`

3. **Configure secrets**

   In the Streamlit app settings, under **Secrets**, add one or more of:

   ```toml
   ANTHROPIC_API_KEY = "your_anthropic_key_here"
   OPENAI_API_KEY    = "your_openai_key_here"
   GEMINI_API_KEY    = "your_gemini_key_here"
   PINECONE_API_KEY  = "your_pinecone_key_here"
   ```

   The app will automatically pick the first available key in the priority order described above.

4. **Deploy**

   - Click **Deploy**. Streamlit will install dependencies from `requirements.txt` and launch the app.
   - You’ll get a public URL like `https://your-username-pm-career-coach.streamlit.app`.

---

## About the Author

I'm a product leader with 8+ years at AWS, where I currently lead agentic AI products for Amazon Q. I've shipped 15+ AI agent integrations using MCP and A2A protocols, and I coach MBA students at UC Berkeley Haas on breaking into product management.

This project sits at the intersection of those two worlds — agentic AI and PM career development.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [GitHub](https://github.com/vipin-mohan)
