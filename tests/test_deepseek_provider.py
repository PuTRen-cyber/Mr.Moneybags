from dataclasses import asdict
from io import BytesIO, StringIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from mr_moneybags.cli import main
from mr_moneybags.providers.deepseek import DeepSeekSemanticClient
from mr_moneybags.providers.openai import OpenAISemanticClient
from mr_moneybags.runtime import configured_interpreter
from mr_moneybags.semantic.context import build_semantic_context
from mr_moneybags.semantic.failures import ConfigurationFailure, ModelOutputFailure, TransportFailure
from mr_moneybags.semantic.model import SemanticModelRequest
from mr_moneybags.semantic.schema import RESULT_SCHEMA
from test_semantic import conversation


def envelope(content='{}', finish='stop'):
    return {'choices': [{'finish_reason': finish, 'message': {'role': 'assistant', 'content': content}}]}


class DeepSeekTest(unittest.TestCase):
    def setUp(self):
        self.env = {'MR_MONEYBAGS_SEMANTIC_MODE': 'model', 'MR_MONEYBAGS_SEMANTIC_PROVIDER': 'deepseek',
                    'MR_MONEYBAGS_SEMANTIC_MODEL': 'configured-model', 'DEEPSEEK_API_KEY': 'test-only'}
        self.request = SemanticModelRequest(build_semantic_context(tuple(conversation('Add search.').turns)))

    def test_deepseek_selection_does_not_require_openai_key(self):
        self.assertIsInstance(configured_interpreter(self.env).client, DeepSeekSemanticClient)

    def test_missing_provider_is_not_inferred_from_keys_or_model(self):
        values = dict(self.env, OPENAI_API_KEY='test-only')
        del values['MR_MONEYBAGS_SEMANTIC_PROVIDER']
        with self.assertRaisesRegex(ConfigurationFailure, 'missing_MR_MONEYBAGS_SEMANTIC_PROVIDER'):
            configured_interpreter(values)

    def test_unknown_provider_fails_before_network(self):
        with patch('mr_moneybags.providers.deepseek.urlopen') as deepseek, patch('mr_moneybags.providers.openai.urlopen') as openai:
            with self.assertRaisesRegex(ConfigurationFailure, 'invalid_semantic_provider'):
                configured_interpreter(dict(self.env, MR_MONEYBAGS_SEMANTIC_PROVIDER='unknown'))
            deepseek.assert_not_called()
            openai.assert_not_called()

    def test_each_provider_requires_only_its_own_key(self):
        for provider, key, other in (('deepseek', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY'),
                                     ('openai', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY')):
            values = {'MR_MONEYBAGS_SEMANTIC_MODE': 'model', 'MR_MONEYBAGS_SEMANTIC_PROVIDER': provider,
                      'MR_MONEYBAGS_SEMANTIC_MODEL': 'configured-model', other: 'test-only'}
            with self.assertRaisesRegex(ConfigurationFailure, 'missing_' + key):
                configured_interpreter(values)
            values[key] = 'test-only'
            self.assertIsInstance(configured_interpreter(values).client,
                                  DeepSeekSemanticClient if provider == 'deepseek' else OpenAISemanticClient)

    def test_request_uses_configured_model_json_context_and_schema(self):
        client = configured_interpreter(self.env).client
        with patch('mr_moneybags.providers.deepseek.urlopen', return_value=BytesIO(json.dumps(envelope()).encode())) as network:
            self.assertEqual(client.interpret(self.request).json_text, '{}')
        request = network.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.deepseek.com/chat/completions')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-only')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'configured-model')
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['thinking'], {'type': 'disabled'})
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['max_tokens'], 6000)
        self.assertEqual(network.call_args.kwargs['timeout'], 60)
        self.assertIn(json.dumps(RESULT_SCHEMA), payload['messages'][0]['content'])
        self.assertEqual(json.loads(payload['messages'][1]['content']), json.loads(json.dumps(asdict(self.request.context))))
        self.assertNotIn('tools', payload)
        self.assertNotIn('test-only', repr(client))

    def test_http_401_timeout_and_connection_errors_are_transport_failures(self):
        for error, code in ((HTTPError('https://api.deepseek.com', 401, 'private detail', {}, None), 'http_401'),
                            (TimeoutError('private detail'), 'request_timeout'), (URLError('private detail'), 'connection_failed')):
            with patch('mr_moneybags.providers.deepseek.urlopen', side_effect=error):
                with self.assertRaisesRegex(TransportFailure, code):
                    configured_interpreter(self.env).client.interpret(self.request)

    def test_malformed_empty_truncated_and_tool_responses_are_rejected(self):
        values = [None, {}, {'choices': []}, {'choices': [None]}, envelope(None), envelope(' '),
                  envelope('{}', 'length'), envelope('{}', 'tool_calls'), envelope('{}', 'content_filter')]
        tools = envelope()
        tools['choices'][0]['message']['tool_calls'] = [{'id': 'unexpected'}]
        values.append(tools)
        for raw in [json.dumps(value).encode() for value in values] + [b'{', b'\xff', b'x' * 1048577]:
            with patch('mr_moneybags.providers.deepseek.urlopen', return_value=BytesIO(raw)):
                with self.assertRaises(ModelOutputFailure):
                    configured_interpreter(self.env).client.interpret(self.request)

    def run_cli(self, transport):
        output, error = StringIO(), StringIO()
        with patch.dict('os.environ', self.env, clear=True), patch('builtins.input', return_value='Add search.'), \
                patch('sys.stdout', output), patch('sys.stderr', error), \
                patch('mr_moneybags.providers.deepseek.urlopen', side_effect=transport) as called, \
                patch.object(OpenAISemanticClient, 'interpret', side_effect=AssertionError('provider fallback')) as other, \
                patch('mr_moneybags.semantic.default.DeterministicInterpreter.interpret', side_effect=AssertionError('deterministic fallback')) as fallback:
            status = main(debug=True)
        called.assert_called_once()
        other.assert_not_called()
        fallback.assert_not_called()
        return status, output.getvalue(), error.getvalue()

    def test_runtime_success_reaches_existing_planning(self):
        def transport(request, **kwargs):
            turn = json.loads(json.loads(request.data)['messages'][1]['content'])['current_turn']
            result = {'source_turn_id': turn['id'], 'claims': [{'id': 'goal', 'concept_id': 'search', 'kind': 'goal',
                'value': 'Add search.', 'protected_target': None, 'implementation_delegation': None,
                'evidence': [{'turn_id': turn['id'], 'exact_quote': turn['raw_text']}]}], 'ambiguities': []}
            return BytesIO(json.dumps(envelope(json.dumps(result))).encode())
        status, output, error = self.run_cli(transport)
        self.assertEqual(status, 0, error)
        self.assertTrue(json.loads(output.split('Planning:\n')[1])['success'])

    def test_runtime_errors_preserve_evidence_without_any_fallback(self):
        invalid = {'source_turn_id': 'invented', 'claims': [], 'ambiguities': []}
        for transport, category in (
            (HTTPError('https://api.deepseek.com', 401, 'private detail', {}, None), 'TransportFailure'),
            (lambda *a, **k: BytesIO(b'{'), 'ModelOutputFailure'),
            (lambda *a, **k: BytesIO(json.dumps(envelope('{')).encode()), 'ModelOutputFailure'),
            (lambda *a, **k: BytesIO(json.dumps(envelope(json.dumps(invalid))).encode()), 'EvidenceValidationFailure'),
        ):
            status, output, error = self.run_cli(transport)
            self.assertEqual(status, 1)
            failure = json.loads(output.split('Interpretation Failure:\n')[1])
            self.assertEqual(failure['category'], category)
            self.assertEqual(failure['conversation']['turns'][0]['raw_text'], 'Add search.')
            self.assertNotIn('Planning:', output)
            self.assertNotIn('private detail', output + error)

    def test_punctuation_boundary_derives_quote_from_selected_span(self):
        def transport(request, **kwargs):
            turn = json.loads(json.loads(request.data)['messages'][1]['content'])['current_turn']
            result = {'source_turn_id': turn['id'], 'claims': [{'id': 'goal', 'concept_id': 'search', 'kind': 'goal',
                'value': 'Add search.', 'protected_target': None, 'implementation_delegation': None,
                'evidence': [{'turn_id': turn['id'], 'exact_quote': 'Add search'}]}], 'ambiguities': []}
            return BytesIO(json.dumps(envelope(json.dumps(result))).encode())
        status, output, error = self.run_cli(transport)
        self.assertEqual(status, 0, error)
        alignment = json.loads(output.split('Conversation / Intent Alignment:\n')[1]
                               .split('Intent Specification / Readiness:\n')[0])['alignment']
        self.assertEqual(alignment['statements'][0]['evidence'][0]['quote'], 'Add search')

    def test_empty_content_fails_closed_without_retry_or_fallback(self):
        for content in ('', ' ', None):
            with self.subTest(content=content):
                status, output, error = self.run_cli(
                    lambda *a, **k: BytesIO(json.dumps(envelope(content)).encode()))
                self.assertEqual(status, 1)
                failure = json.loads(output.split('Interpretation Failure:\n')[1])
                self.assertEqual(failure['category'], 'ModelOutputFailure')
                self.assertEqual(failure['code'], 'missing_model_output')
                self.assertNotIn('Intent Specification / Readiness:', output)

    def test_timeout_fails_closed_without_retry_or_fallback(self):
        for timeout in (TimeoutError('private detail'), URLError(TimeoutError('private detail'))):
            with self.subTest(timeout_type=type(timeout).__name__):
                status, output, error = self.run_cli(timeout)
                self.assertEqual(status, 1)
                failure = json.loads(output.split('Interpretation Failure:\n')[1])
                self.assertEqual(failure['category'], 'TransportFailure')
                self.assertEqual(failure['code'], 'request_timeout')
                self.assertNotIn('Intent Specification / Readiness:', output)
                self.assertNotIn('private detail', output + error)
