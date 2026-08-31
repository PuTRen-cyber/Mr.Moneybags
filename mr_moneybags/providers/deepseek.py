from dataclasses import asdict
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from mr_moneybags.semantic.failures import ModelOutputFailure, TransportFailure
from mr_moneybags.semantic.model import SemanticModelRequest, SemanticModelResponse
from mr_moneybags.semantic.prompt import INSTRUCTIONS
from mr_moneybags.semantic.schema import RESULT_SCHEMA


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(_NoRedirect()).open


class DeepSeekSemanticClient:
    def __init__(self, *, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def interpret(self, request: SemanticModelRequest) -> SemanticModelResponse:
        payload = {
            'model': self._model,
            'messages': [
                {'role': 'system', 'content': INSTRUCTIONS + '\nReturn a JSON object matching this JSON Schema:\n'
                 + json.dumps(RESULT_SCHEMA)},
                {'role': 'user', 'content': json.dumps(asdict(request.context), ensure_ascii=False)},
            ],
            'response_format': {'type': 'json_object'}, 'stream': False, 'max_tokens': 6000,
        }
        wire_request = Request('https://api.deepseek.com/chat/completions',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self._api_key, 'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(wire_request, timeout=30) as response:
                raw = response.read(1048577)
        except HTTPError as error:
            error.close()
            raise TransportFailure(f'http_{error.code}') from None
        except TimeoutError:
            raise TransportFailure('request_timeout') from None
        except URLError as error:
            code = 'request_timeout' if isinstance(error.reason, TimeoutError) else 'connection_failed'
            raise TransportFailure(code) from None
        except (OSError, ValueError):
            raise TransportFailure('connection_failed') from None
        if len(raw) > 1048576:
            raise ModelOutputFailure('provider_response_too_large')
        try:
            data = json.loads(raw)
            choices = data['choices']
            if not isinstance(choices, list) or len(choices) != 1:
                raise ModelOutputFailure('missing_or_multiple_model_outputs')
            choice = choices[0]
            if choice['finish_reason'] != 'stop':
                raise ModelOutputFailure('provider_response_incomplete')
            message = choice['message']
            if message['role'] != 'assistant' or message.get('tool_calls') or message.get('function_call') or message.get('refusal'):
                raise ModelOutputFailure('unexpected_provider_content')
            content = message['content']
            if not isinstance(content, str) or not content.strip():
                raise ModelOutputFailure('missing_model_output')
        except ModelOutputFailure:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            raise ModelOutputFailure('malformed_provider_response') from None
        return SemanticModelResponse(content)
