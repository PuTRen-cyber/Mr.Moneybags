from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from mr_moneybags.providers.openai import OpenAISemanticClient
from mr_moneybags.runtime import configured_interpreter
from mr_moneybags.semantic.context import build_semantic_context
from mr_moneybags.semantic.failures import ConfigurationFailure, ModelOutputFailure, TransportFailure
from mr_moneybags.semantic.model import ModelBackedSemanticInterpreter, SemanticModelRequest
from mr_moneybags.semantic.default import DeterministicInterpreter
from test_semantic import conversation


def envelope(text='{}', status='completed'):
    return {'status': status, 'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                                        'content': [{'type': 'output_text', 'text': text}]}]}


class ProviderTest(unittest.TestCase):
    def setUp(self):
        self.request = SemanticModelRequest(build_semantic_context(tuple(conversation('Add search.').turns)))
        self.client = OpenAISemanticClient(api_key='test-only', model='test-model')

    def test_real_adapter_builds_strict_bounded_request_without_tools(self):
        with patch('mr_moneybags.providers.openai.urlopen', return_value=BytesIO(json.dumps(envelope()).encode())) as network:
            self.assertEqual(self.client.interpret(self.request).json_text, '{}')
        request = network.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'test-model')
        self.assertFalse(payload['store'])
        self.assertTrue(payload['text']['format']['strict'])
        self.assertFalse(payload['text']['format']['schema']['additionalProperties'])
        self.assertNotIn('tools', payload)
        self.assertNotIn('previous_response_id', payload)
        self.assertEqual(network.call_args.kwargs['timeout'], 30)
        self.assertEqual(json.loads(payload['input'])['current_turn']['raw_text'], 'Add search.')
        self.assertNotIn('test-only', repr(self.client))

    def test_timeout_connection_and_http_errors_are_sanitized(self):
        for error, code in (
            (TimeoutError('private detail'), 'request_timeout'),
            (URLError('private detail'), 'connection_failed'),
            (HTTPError('https://api.openai.com', 503, 'private detail', {}, None), 'http_503'),
            (HTTPError('https://api.openai.com', 401, 'private detail', {}, None), 'http_401'),
        ):
            with self.subTest(code=code), patch('mr_moneybags.providers.openai.urlopen', side_effect=error):
                with self.assertRaisesRegex(TransportFailure, code) as caught:
                    self.client.interpret(self.request)
                self.assertNotIn('private detail', str(caught.exception))

    def test_incomplete_refusal_missing_and_malformed_are_output_failures(self):
        for value in (
            envelope(status='incomplete'), {'status': 'completed', 'output': []},
            {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                                               'content': [{'type': 'refusal', 'refusal': 'private detail'}]}]},
            {'status': 'completed', 'output': [None]}, [],
            {'status': 'completed', 'output': [{'type': 'message', 'role': 'user', 'status': 'completed',
                                               'content': [{'type': 'output_text', 'text': '{}'}]}]},
            {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant', 'status': 'incomplete',
                                               'content': [{'type': 'output_text', 'text': '{}'}]}]},
        ):
            with patch('mr_moneybags.providers.openai.urlopen', return_value=BytesIO(json.dumps(value).encode())):
                with self.assertRaises(ModelOutputFailure):
                    self.client.interpret(self.request)
        for payload in (b'{', b'\xff', b'x' * 1048577):
            with patch('mr_moneybags.providers.openai.urlopen', return_value=BytesIO(payload)):
                with self.assertRaises(ModelOutputFailure):
                    self.client.interpret(self.request)

    def test_provider_response_affects_cli_through_normal_model_mode(self):
        def transport(request, **kwargs):
            context = json.loads(json.loads(request.data)['input'])
            turn = context['current_turn']
            data = {'source_turn_id': turn['id'], 'claims': [{
                'id': 'search', 'concept_id': 'search', 'kind': 'goal', 'value': 'Find local records.',
                'evidence': [{'turn_id': turn['id'], 'start': 0, 'end': len(turn['raw_text'])}],
                'protected_target': None, 'implementation_delegation': None}], 'ambiguities': []}
            return BytesIO(json.dumps(envelope(json.dumps(data))).encode())
        from io import StringIO
        from mr_moneybags.cli import main
        output = StringIO()
        with patch.dict('os.environ', {'MR_MONEYBAGS_SEMANTIC_MODE': 'model',
                                      'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'openai',
                                      'OPENAI_API_KEY': 'test-only', 'MR_MONEYBAGS_SEMANTIC_MODEL': 'test-model'}, clear=True), \
                patch('mr_moneybags.providers.openai.urlopen', side_effect=transport) as called, \
                patch('builtins.input', return_value='Find records.'), patch('sys.stdout', output):
            self.assertEqual(main(debug=True), 0)
        called.assert_called_once()
        plan = json.loads(output.getvalue().split('Planning:\n')[1])
        self.assertEqual(plan['current_work_unit']['objective']['value'], 'Find local records.')

    def test_configuration_is_explicit_and_missing_key_fails_without_network(self):
        self.assertIsInstance(configured_interpreter({}), DeterministicInterpreter)
        self.assertIsInstance(configured_interpreter({'MR_MONEYBAGS_SEMANTIC_MODE': 'model',
            'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test-only', 'MR_MONEYBAGS_SEMANTIC_MODEL': 'test-model'}), ModelBackedSemanticInterpreter)
        for values, code in (
            ({'MR_MONEYBAGS_SEMANTIC_MODE': 'invalid'}, 'invalid_semantic_mode'),
            ({'MR_MONEYBAGS_SEMANTIC_MODE': 'model', 'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'openai'}, 'missing_OPENAI_API_KEY'),
            ({'MR_MONEYBAGS_SEMANTIC_MODE': 'model', 'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'openai',
              'OPENAI_API_KEY': 'test-only'}, 'missing_MR_MONEYBAGS_SEMANTIC_MODEL'),
        ):
            with patch('mr_moneybags.providers.openai.urlopen') as network:
                with self.assertRaisesRegex(ConfigurationFailure, code):
                    configured_interpreter(values)
                network.assert_not_called()

    def test_model_mode_configuration_failure_preserves_cli_evidence(self):
        from io import StringIO
        from mr_moneybags.cli import main
        output, error = StringIO(), StringIO()
        with patch.dict('os.environ', {'MR_MONEYBAGS_SEMANTIC_MODE': 'model', 'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'openai'}, clear=True), \
                patch('builtins.input', return_value='Keep raw request.'), patch('sys.stdout', output), patch('sys.stderr', error):
            self.assertEqual(main(debug=True), 1)
        self.assertIn('missing_OPENAI_API_KEY', error.getvalue())
        self.assertIn('Keep raw request.', output.getvalue())
        self.assertNotIn('Planning:', output.getvalue())
