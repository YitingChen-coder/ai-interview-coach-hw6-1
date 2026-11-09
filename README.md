# AI Interview Coach

Generative AI — HW 6-1, University of Chicago.

A technical interview practice app built with LangGraph, Streamlit, and OpenAI. Enter a question to get its category, a suggested answer, and two follow-up questions.

## Run locally

Use Python 3.11 or newer. From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

If `.env` already contains your key, skip the copy command. Edit `.env` to add your OpenAI API key:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Start the app:

```bash
python -m streamlit run app.py
```

Open http://localhost:8501. If Streamlit asks for an email on first startup, press Enter to skip it. Restart the app after changing `.env`. Existing shell environment variables take precedence over `.env`.

Try a question such as "How do database indexes improve query performance?" and click **Generate answer**. Previous results appear below the form and remain during the current browser session. Each question is handled independently.

## Workflow

```text
START -> Question Classifier -> Answer Generator -> Follow-up Generator -> END
```

The workflow is defined in `graph.py`:

1. **Question Classifier** selects Algorithms, Backend, System Design, or AI/LLM.
2. **Answer Generator** uses the question and category to write a technical answer.
3. **Follow-up Generator** uses the question and answer to produce two follow-up questions.

`InterviewState` holds `question`, `category`, `answer`, and `follow_ups`. The nodes are registered with `StateGraph.add_node()` and connected with `add_edge()`. `build_graph()` compiles the graph, and `run_interview()` runs it with `invoke()`.

`app.py` provides the Streamlit form and displays the results. Completed results are stored in `st.session_state`. Each completed workflow makes three OpenAI requests. If a request fails, the app displays an error and leaves the existing history intact.

## Project files

- `app.py`: Streamlit interface and session history.
- `graph.py`: LangGraph workflow and OpenAI calls.
- `requirements.txt`: Python dependencies.
- `.env.example`: Environment variable template.
- `.gitignore`: Excludes local keys and virtual environments.
- `tests/test_app.py`: Offline tests.

## Checks

```bash
python -m py_compile app.py graph.py
python -c "import streamlit, langgraph, openai, dotenv; import graph"
python -m pip check
python -m unittest discover -s tests -v
```

The tests cover graph state, input validation, session history, and error display using simulated OpenAI responses. Live generation requires a valid API key.

## Configuration and errors

Keep your key in `.env`; do not put it in `.env.example` or submit it with the project. The model can be changed through `OPENAI_MODEL` to a Chat Completions model that supports JSON mode.

If authentication fails, check the key. For rate limits or quota errors, check API billing and retry later. For connection errors, check your internet connection and proxy settings. The app also reports timeouts, HTTP errors, and invalid responses.

## References

- [LangGraph graph API](https://reference.langchain.com/python/langgraph/graph)
- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
- [OpenAI JSON mode](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
