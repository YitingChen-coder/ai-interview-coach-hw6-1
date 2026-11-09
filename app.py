"""Streamlit interface for AI Interview Coach."""
import streamlit as st

from graph import run_interview

st.set_page_config(page_title='AI Interview Coach', page_icon='🎯', layout='centered')
st.title('AI Interview Coach')
st.write('Practice technical questions with a suggested answer and two follow-up questions.')
st.caption('HW 6-1 · Generative AI · University of Chicago')

with st.sidebar:
    st.header('Topics')
    st.write('Algorithms · Backend · System Design · AI/LLM')
    st.divider()
    st.markdown('**How it works**\n\n1. Classify your question\n2. Generate a technical answer\n3. Create two follow-up questions')
    st.caption('LangGraph · Streamlit · OpenAI')
    st.caption('History lasts for this browser session. Each question is analyzed independently.')

if 'history' not in st.session_state:
    st.session_state.history = []

with st.form('interview_form'):
    question = st.text_area(
        'Technical interview question',
        placeholder='For example: How does a hash table work, and what is its time complexity?',
        height=120,
        max_chars=6000,
    )
    submitted = st.form_submit_button('Generate answer', type='primary')

if submitted:
    try:
        with st.spinner('Generating answer and follow-up questions...'):
            result = run_interview(question)
        st.session_state.history.append(result)
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
    except Exception:
        st.error('An unexpected error occurred. Please check your configuration and try again.')

if not st.session_state.history:
    st.info('Enter a technical question to get a model answer and two interviewer follow-ups.')
else:
    st.subheader('Practice history')
    for index, entry in reversed(list(enumerate(st.session_state.history, start=1))):
        with st.container(border=True):
            st.caption(f"QUESTION {index} · {entry['category']}")
            st.markdown('**Your question**')
            st.write(entry['question'])
            st.markdown('**Suggested answer**')
            st.markdown(entry['answer'])
            st.markdown('**Interviewer follow-ups**')
            for number, follow_up in enumerate(entry['follow_ups'], start=1):
                st.write(f'{number}. {follow_up}')
