"""Test the graph and UI without making API calls."""
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from graph import build_graph, run_interview


def response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def decision(category='Backend', reason='问题涉及数据库实现。', complexity='simple'):
    return json.dumps({'category': category, 'reason': reason, 'complexity': complexity}, ensure_ascii=False)


FOLLOW_UPS = json.dumps({'questions': ['什么时候不适合建立索引？', '复合索引有什么限制？']}, ensure_ascii=False)


class GraphTests(unittest.TestCase):
    def test_categories_and_model_routing(self):
        branches = {'Algorithms': 'algorithms_answer', 'Backend': 'backend_answer',
                    'System Design': 'system_design_answer', 'AI/LLM': 'ai_answer'}
        focus = {'Algorithms': '时间与空间复杂度', 'Backend': '数据一致性',
                 'System Design': '规模假设', 'AI/LLM': '评估方法'}
        models = {'simple': 'test/light', 'complex': 'test/strong'}
        for category, branch in branches.items():
            for complexity, expected_model in models.items():
                with self.subTest(category=category, complexity=complexity):
                    client = MagicMock()
                    client.chat.completions.create.side_effect = [
                        response(decision(category, complexity=complexity)),
                        response('索引提升读取效率，但增加写入开销。'),
                        response(FOLLOW_UPS),
                    ]
                    workflow = build_graph(client, 'test/light', 'test/decision',
                                           complex_model='test/strong')
                    events = list(workflow.stream({'question': '解释数据库索引。'},
                                                  stream_mode='updates'))
                    path = ['decision_model', 'model_router', branch, 'follow_up_generator']
                    self.assertEqual([next(iter(event)) for event in events], path)
                    result = {}
                    for event in events:
                        result.update(next(iter(event.values())))
                    self.assertEqual(result['category'], category)
                    self.assertEqual(result['complexity'], complexity)
                    self.assertEqual(result['route'], branch)
                    self.assertEqual(result['decision_reason'], '问题涉及数据库实现。')
                    self.assertEqual(result['execution_path'], path)
                    self.assertEqual(result['answer_model'], expected_model)
                    self.assertEqual(len(result['follow_ups']), 2)
                    calls = client.chat.completions.create.call_args_list
                    self.assertEqual([call.kwargs['model'] for call in calls],
                                     ['test/decision', expected_model, expected_model])
                    self.assertIn('中文', calls[1].kwargs['messages'][0]['content'])
                    self.assertIn(focus[category], calls[1].kwargs['messages'][0]['content'])
                    self.assertIn(category, calls[1].kwargs['messages'][1]['content'])
                    self.assertIn(result['answer'], calls[2].kwargs['messages'][1]['content'])

    def test_invalid_decisions_stop_before_answer(self):
        invalid = [
            'not json', '[]', decision('Unknown'), decision(reason=' '), decision(reason=3),
            decision(complexity='medium'), decision(complexity=None), decision(complexity=[]),
            '{"category":"Backend","reason":"x"}', '{"reason":"x"}',
        ]
        for raw in invalid:
            with self.subTest(raw=raw):
                client = MagicMock()
                client.chat.completions.create.return_value = response(raw)
                with self.assertRaisesRegex(ValueError, '决策'):
                    build_graph(client, 'answer', 'decision').invoke({'question': '解释索引'})
                self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_empty_responses(self):
        for content in [None, '', '   ']:
            client = MagicMock()
            client.chat.completions.create.return_value = response(content)
            with self.assertRaisesRegex(ValueError, '空'):
                build_graph(client, 'answer', 'decision').invoke({'question': '解释索引'})
        client.chat.completions.create.return_value = SimpleNamespace(choices=[])
        with self.assertRaisesRegex(ValueError, '空'):
            build_graph(client, 'answer', 'decision').invoke({'question': '解释索引'})

    def test_invalid_follow_ups(self):
        for raw in ['no json', '[]', '{}', '{"questions":["a"]}', '{"questions":["a"," a "]}', '{"questions":["a",3]}', '{"questions":["a"," "]}']:
            client = MagicMock()
            client.chat.completions.create.side_effect = [response(decision()), response('回答'), response(raw)]
            with self.assertRaisesRegex(ValueError, '追问'):
                build_graph(client, 'answer', 'decision').invoke({'question': '解释索引'})

    def test_validation(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': ''}):
            with self.assertRaisesRegex(ValueError, '问题'):
                run_interview('  ')
            with self.assertRaisesRegex(ValueError, 'OPENROUTER_API_KEY'):
                run_interview('解释索引')

    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'offline-key', 'DECISION_MODEL': 'test/decision', 'ANSWER_MODEL': 'test/answer', 'COMPLEX_ANSWER_MODEL': 'test/complex'})
    def test_openrouter_configuration(self):
        with patch('graph.OpenAI') as factory:
            client = factory.return_value.__enter__.return_value
            client.chat.completions.create.side_effect = [response(decision(complexity='complex')), response('回答'), response(FOLLOW_UPS)]
            result = run_interview('  解释索引  ')
        self.assertEqual(factory.call_args.kwargs['base_url'], 'https://openrouter.ai/api/v1')
        self.assertEqual(factory.call_args.kwargs['api_key'], 'offline-key')
        self.assertEqual(result['question'], '解释索引')
        self.assertEqual(result['decision_model'], 'test/decision')
        self.assertEqual(result['answer_model'], 'test/complex')
        self.assertEqual(result['provider'], 'OpenRouter')

    def test_real_sdk_serializes_openrouter_requests(self):
        requests = []
        replies = iter([decision(complexity='complex'), '索引提升读取效率。', FOLLOW_UPS])

        def serve(request):
            requests.append(request)
            return httpx.Response(200, json={
                'id': 'offline', 'object': 'chat.completion', 'created': 0,
                'model': 'test/model', 'choices': [{'index': 0,
                    'message': {'role': 'assistant', 'content': next(replies)},
                    'finish_reason': 'stop'}],
            })

        with httpx.Client(transport=httpx.MockTransport(serve)) as http_client:
            with OpenAI(api_key='offline-key', base_url='https://openrouter.ai/api/v1',
                        http_client=http_client) as client:
                result = build_graph(client, 'test/answer', 'test/decision',
                                     complex_model='test/strong').invoke({'question': '解释索引'})
        self.assertEqual(result['category'], 'Backend')
        self.assertEqual(len(requests), 3)
        for request in requests:
            self.assertEqual(str(request.url), 'https://openrouter.ai/api/v1/chat/completions')
            self.assertEqual(request.headers['authorization'], 'Bearer offline-key')
        bodies = [json.loads(request.content) for request in requests]
        self.assertEqual([b['model'] for b in bodies], ['test/decision', 'test/strong', 'test/strong'])
        self.assertEqual(bodies[0]['response_format'], {'type': 'json_object'})
        self.assertNotIn('response_format', bodies[1])
        self.assertEqual(bodies[2]['response_format'], {'type': 'json_object'})

    def test_api_errors_are_readable(self):
        request = httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions')
        errors = [
            (AuthenticationError('bad', response=httpx.Response(401, request=request), body=None), '认证'),
            (RateLimitError('quota', response=httpx.Response(429, request=request), body=None), '额度'),
            (APITimeoutError(request=request), '超时'),
            (APIConnectionError(request=request), '连接'),
            (APIStatusError('bad', response=httpx.Response(503, request=request), body=None), '503'),
        ]
        for error, message in errors:
            with self.subTest(error=type(error).__name__), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'offline-key'}), patch('graph.OpenAI', side_effect=error):
                with self.assertRaisesRegex(RuntimeError, message):
                    run_interview('解释索引')


class InterfaceTests(unittest.TestCase):
    def test_chinese_history_and_error_display(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, '技术面试教练')
        result = {'question': '解释索引', 'category': 'Backend', 'answer': '索引加快读取。',
                  'follow_ups': ['写入代价是什么？', '什么是覆盖索引？'], 'decision_reason': '涉及数据库。',
                  'route': 'backend_answer', 'execution_path': ['decision_model', 'model_router', 'backend_answer', 'follow_up_generator'],
                  'decision_model': 'test/decision', 'answer_model': 'test/answer', 'complexity': 'simple', 'provider': 'OpenRouter'}
        with patch('graph.run_interview', return_value=result):
            app.text_area[0].input('解释索引')
            app.button[0].click().run()
        self.assertEqual(len(app.session_state['history']), 1)
        app.run()
        content = '\n'.join(m.value for m in app.markdown)
        self.assertIn('涉及数据库。', content)
        self.assertIn('backend_answer', content)
        self.assertIn('test/decision', content)
        self.assertIn('基础题', content)
        with patch('graph.run_interview', side_effect=RuntimeError('OpenRouter 连接失败。')):
            app.text_area[0].input('解释缓存')
            app.button[0].click().run()
        self.assertEqual(len(app.session_state['history']), 1)
        self.assertIn('连接失败', app.error[0].value)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
