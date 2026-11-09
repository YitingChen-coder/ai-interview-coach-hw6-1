"""Offline checks: real graph and Streamlit, mocked OpenAI network boundary."""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class CoachTests(unittest.TestCase):
    def test_three_stages_propagate_state(self):
        self.assertIsNotNone(importlib.util.find_spec('graph'), 'graph.py must exist')
        from graph import build_graph
        from openai import OpenAI
        replies = iter(['Backend', 'An index speeds up reads but adds write overhead.',
                        json.dumps({'questions': ['When would you avoid an index?', 'How do composite indexes work?']})])
        prompts = []

        def complete(**kwargs):
            prompts.append(kwargs['messages'])
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(replies)))])

        with patch.dict(os.environ, {name: '' for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')}), OpenAI(api_key='offline-test-key') as client:
            with patch.object(client.chat.completions, 'create', side_effect=complete):
                result = build_graph(client, 'gpt-4.1-mini').invoke({'question': 'Explain database indexes.'})
        self.assertEqual(result['category'], 'Backend')
        self.assertIn('write overhead', result['answer'])
        self.assertEqual(len(result['follow_ups']), 2)
        self.assertIn('Backend', prompts[1][1]['content'])
        self.assertIn(result['answer'], prompts[2][1]['content'])

    def test_missing_key_and_blank_question(self):
        self.assertIsNotNone(importlib.util.find_spec('graph'), 'graph.py must exist')
        from graph import run_interview
        with self.assertRaisesRegex(ValueError, 'question'):
            run_interview('  ')
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            with self.assertRaisesRegex(ValueError, 'OPENAI_API_KEY'):
                run_interview('Explain a hash table.')

    def test_ui_history_and_failure(self):
        self.assertIsNotNone(importlib.util.find_spec('graph'), 'graph.py must exist')
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertFalse(app.exception)
        result = {'question': 'Explain indexes.', 'category': 'Backend',
                  'answer': 'Indexes speed up reads.', 'follow_ups': ['What is the write cost?', 'What is a covering index?']}
        with patch('graph.run_interview', return_value=result):
            app.text_area[0].input('Explain indexes.')
            app.button[0].click().run()
        self.assertEqual(len(app.session_state['history']), 1)
        app.run()
        self.assertTrue(any('Indexes speed up reads.' in m.value for m in app.markdown))
        with patch('graph.run_interview', side_effect=RuntimeError('OpenAI connection failed.')):
            app.text_area[0].input('Explain caching.')
            app.button[0].click().run()
        self.assertEqual(len(app.session_state['history']), 1)
        self.assertIn('connection failed', app.error[0].value)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
