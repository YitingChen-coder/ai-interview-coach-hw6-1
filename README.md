# AI Interview Coach — HW 7-2

## Project Overview

This is my UChicago Generative AI homework project, built on my HW 6-1 interview coach. It uses LangGraph and Streamlit to generate a sample answer and two follow-up questions. Questions are classified as Algorithms, Backend, System Design, or AI/LLM. The app interface and generated answers are in Chinese.

## What I Changed for HW 7-2

I added model routing through OpenRouter. A classifier checks the question's topic and complexity, then the router selects a model:

- Basic questions use `openai/gpt-4.1-mini`.
- Questions involving multi-step reasoning or several design constraints use `openai/gpt-4.1`.

The selected model generates both the answer and the follow-up questions. Each topic has its own answer prompt. The page shows the complexity, routing reason, selected model, and execution path.

```text
Question -> Classifier -> Model Router -> Topic Answer -> Follow-ups
```

This project uses the Model Router option for HW 7-2. The classifier is a regular LLM, not a separate Decision Model such as SemIf.

## How to Run

Use Python 3.11 or newer (I tested with Python 3.12).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

If `.env` already exists, edit it instead of copying over it. Add your OpenRouter key:

```dotenv
OPENROUTER_API_KEY=your_openrouter_api_key_here
DECISION_MODEL=openai/gpt-4.1-mini
ANSWER_MODEL=openai/gpt-4.1-mini
COMPLEX_ANSWER_MODEL=openai/gpt-4.1
```

`ANSWER_MODEL` is for basic questions; `COMPLEX_ANSWER_MODEL` is for complex ones. Use different models for these settings. All configured models need JSON mode support. Keep `.env` out of Git; it is already in `.gitignore`.

```bash
python -m streamlit run app.py
```

Open http://localhost:8501. Restart the app after changing `.env`. Practice history stays in the current browser session.

## Example Questions

- Algorithms: How does binary search work? What is its time complexity?
- Backend: What is a database index?
- System Design: Design a multi-region URL shortener. Discuss capacity, unique IDs, consistency, caching, and failover.
- AI/LLM: When would you use RAG instead of fine-tuning?

Try the database index and multi-region design questions to compare model choices. Complexity is judged by the classifier, so the choice can vary.

## Testing

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py graph.py tests/test_app.py
```

The 9 offline tests cover all four topics with both model choices, answer and follow-up generation, invalid responses, API errors, and UI history. They mock API calls and do not require a key.

I also tested two live interview runs through Streamlit AppTest using OpenRouter on November 17, 2026: a database index question used GPT-4.1 Mini, and a multi-region URL shortener question used GPT-4.1. Both returned an answer and two follow-up questions. These live checks were done before this cleanup; the offline tests were rerun after it.
