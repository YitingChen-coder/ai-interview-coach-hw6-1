"""Streamlit app for interview practice."""
import streamlit as st

from graph import CATEGORY_LABELS, COMPLEXITY_LABELS, run_interview

st.set_page_config(page_title='技术面试教练', page_icon='🎯', layout='centered')
st.title('技术面试教练')
st.write('输入一道技术面试题，获取对应方向的参考回答和两条深入追问。')
st.caption('HW 7-2 · 模型路由与 OpenRouter')

with st.sidebar:
    st.header('练习方向')
    st.write('算法 · 后端 · 系统设计 · 人工智能与大模型')
    st.divider()
    st.markdown('**处理流程**\n\n1. 判断题目方向和复杂度\n2. 选择模型和专家回答分支\n3. 根据回答生成两条追问')
    st.caption('LangGraph · Streamlit · OpenRouter')
    st.caption('练习记录仅保存在当前浏览器会话中。每道题独立处理。')

if 'history' not in st.session_state:
    st.session_state.history = []

with st.form('interview_form'):
    question = st.text_area(
        '技术面试问题',
        placeholder='例如：数据库索引如何加快查询？它会带来哪些代价？',
        height=120, max_chars=6000,
    )
    submitted = st.form_submit_button('生成回答', type='primary')

if submitted:
    try:
        with st.spinner('正在选择回答方向并生成内容……'):
            result = run_interview(question)
        st.session_state.history.append(result)
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
    except Exception:
        st.error('发生了未预期的错误，请检查配置后重试。')

if not st.session_state.history:
    st.info('输入问题后，页面会显示参考回答、追问和本次执行路径。')
else:
    st.subheader('练习记录')
    for index, entry in reversed(list(enumerate(st.session_state.history, start=1))):
        with st.container(border=True):
            st.caption(f"第 {index} 题 · {CATEGORY_LABELS[entry['category']]}")
            st.markdown('**问题**')
            st.write(entry['question'])
            st.markdown('**参考回答**')
            st.markdown(entry['answer'])
            st.markdown('**面试官追问**')
            for number, follow_up in enumerate(entry['follow_ups'], start=1):
                st.write(f'{number}. {follow_up}')
            with st.expander('查看决策与执行信息'):
                st.markdown(f"**题目复杂度：** {COMPLEXITY_LABELS[entry['complexity']]}")
                st.markdown(f"**决策依据：** {entry['decision_reason']}")
                st.markdown(f"**执行路径：** `{' → '.join(entry['execution_path'])}`")
                st.markdown(f"**服务：** {entry['provider']}")
                st.markdown(f"**决策模型：** `{entry['decision_model']}`")
                st.markdown(f"**回答与追问模型：** `{entry['answer_model']}`")
