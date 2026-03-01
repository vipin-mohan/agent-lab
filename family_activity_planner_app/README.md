# Family Activity Planner

An AI-powered app that helps busy parents plan age-appropriate, location-aware family activities — built with Python, Streamlit, and Claude (Anthropic).

**[Live Demo →](https://family-activity-planner.streamlit.app/)**

---

## Why I Built This

I have two kids (ages 8 and 3.5) and a full-time job. The hardest part of weekends isn't finding *something* to do — it's finding something that works for both kids, fits the time and energy available, and doesn't require a 45-minute Google spiral to plan.

This app solves that. Enter your zip code, your kids' ages, and a few quick preferences — and get 5 specific, realistic activity suggestions tailored to your family and your neighborhood.

---

## What It Does

**Weekend mode** — fuller activity suggestions with no time constraint, optimized for family days out or low-key time at home.

**Weekday Evening mode** — every suggestion is strictly under 60 minutes. No exceptions. Built for school nights when time is short and energy is unpredictable.

Each suggestion includes:
- 🎯 Activity name
- ⏱ Time needed
- 📍 Location tip specific to your area
- 🛒 What you need
- ⭐ Why kids will love it
- 💡 A parent tip

**Inputs you can customize:**
- Zip code (for location-aware suggestions)
- Number of kids (1–6) with individual age inputs — supports decimals like 3.5
- Plan for all kids together or a specific child
- Energy level, location preference (home / outdoors / either), budget, and screen-free toggle

---

## Tech Stack

- **Frontend:** Streamlit
- **AI:** Anthropic Claude (claude-sonnet-4-6), with automatic fallback to OpenAI (gpt-4.1-mini) and Google Gemini (gemini-2.0-flash)
- **Language:** Python 3.11+
- **Hosting:** Streamlit Community Cloud

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/family-activity-planner.git
cd family-activity-planner
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your API key

Create a `.env` file in the root directory. The app checks for API keys in this priority order — whichever is available first is used:

```env
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-openai-...
# GEMINI_API_KEY=your-gemini-key
```

### 4. Run locally

```bash
streamlit run family_activity_planner_app.py
```

Then open `http://localhost:8501` in your browser.

---

## Deploying to Streamlit Cloud

1. Push the repo to GitHub (make sure `.env` is in your `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repo
3. In app settings, add your API key under **Secrets**:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

4. Deploy — you'll get a shareable public URL instantly

---

## About the Author

I'm a product leader at AWS focused on agentic AI, and a parent of two. I built this because I needed it — and because the best products come from real problems.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [GitHub](https://github.com/vipin-mohan)