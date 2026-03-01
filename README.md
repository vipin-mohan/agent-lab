# agent-lab

Hands-on experiments in agentic AI and LLM-powered products — built by a PM who ships this stuff at AWS for a living.

I lead agentic AI product development at Amazon Web Services. This repo is where I build things outside of work: real apps with real use cases, using the same AI APIs and patterns I work with professionally.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [Live demos below](#projects)

---

## Projects

### 🤖 PM Career Coach
> AI-powered career coaching for aspiring product managers

An app that gives structured, personalized PM interview prep, gap analysis, and career positioning — built from patterns I've observed coaching 250+ MBA students at UC Berkeley Haas over 5+ years.

**Why it's different:** The system prompts aren't generic. They encode real coaching patterns from hundreds of actual sessions — what separates strong PM candidates, common storytelling mistakes, and what top tech companies actually look for.

**Tech:** Python · Streamlit · Claude / OpenAI / Gemini (auto-fallback)

[Live Demo](https://agent-lab-career-coach.streamlit.app/) · [Source](./pm_career_coach_app/)

---

### 👨‍👧‍👦 Family Activity Planner
> Location-aware activity suggestions for busy parents

Enter your zip code, your kids' ages, and how much time and energy you have — get 5 specific, realistic activity suggestions tailored to your family and your neighborhood. Weekend mode for fuller days, Weekday Evening mode for suggestions that fit within 60 minutes.

**Why I built it:** I have two young kids and a full-time job. The best products solve real problems. This one solves mine.

**Tech:** Python · Streamlit · Claude / OpenAI / Gemini (auto-fallback)

[Live Demo](https://family-activity-planner.streamlit.app/) · [Source](./family_activity_planner_app/)

---

### ⚙️ Task API
> A clean REST API with a built-in UI for managing tasks

A FastAPI backend with persistent JSON storage and a minimal, dark-mode task management UI served directly from the API. Built as a backend fundamentals exercise — REST design, persistent state, and serving a frontend from a Python API.

**Tech:** Python · FastAPI · Uvicorn

[Source](./task-api/)

---

## Why This Repo Exists

I've spent 8+ years in product management at AWS, Google, and Walmart — and the last two focused entirely on agentic AI. I built agent routing systems before MCP existed, launched AI integrations at AWS re:Invent, and defined what "AI-native" means for developer tools.

This repo is my way of staying close to the code, building intuition for what's hard to build vs. easy to build, and demonstrating that I think about AI products as a practitioner — not just a strategist.

Every project here started as a real problem I wanted to solve.

---

## Tech Stack Across Projects

| | Language | Framework | AI |
|---|---|---|---|
| PM Career Coach | Python | Streamlit | Claude / OpenAI / Gemini |
| Family Activity Planner | Python | Streamlit | Claude / OpenAI / Gemini |
| Task API | Python | FastAPI | — |

All LLM-powered apps support Anthropic Claude, OpenAI, and Google Gemini based on available API keys.

---

## About Me

I'm Vipin Mohan — Head of Product for Agentic AI at AWS, UC Berkeley Haas MBA coach, co-founder of a smart water tech startup, and parent of two. I've spent my career at the intersection of deep technical systems and products that real people use.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [GitHub](https://github.com/vipin-mohan)
