import os
from collections.abc import Mapping

from mr_moneybags.semantic.default import DeterministicInterpreter
from mr_moneybags.semantic.failures import ConfigurationFailure
from mr_moneybags.semantic.interpreter import SemanticInterpreter


def configured_interpreter(environ: Mapping[str, str] | None = None) -> SemanticInterpreter:
    values = os.environ if environ is None else environ
    mode = values.get('MR_MONEYBAGS_SEMANTIC_MODE', 'deterministic')
    if mode == 'deterministic':
        return DeterministicInterpreter()
    if mode != 'model':
        raise ConfigurationFailure('invalid_semantic_mode')
    provider = values.get('MR_MONEYBAGS_SEMANTIC_PROVIDER', '')
    if not provider.strip():
        raise ConfigurationFailure('missing_MR_MONEYBAGS_SEMANTIC_PROVIDER')
    if provider not in ('openai', 'deepseek'):
        raise ConfigurationFailure('invalid_semantic_provider')
    key_name = 'OPENAI_API_KEY' if provider == 'openai' else 'DEEPSEEK_API_KEY'
    for name in (key_name, 'MR_MONEYBAGS_SEMANTIC_MODEL'):
        if not values.get(name, '').strip():
            raise ConfigurationFailure('missing_' + name)
    from mr_moneybags.semantic.model import ModelBackedSemanticInterpreter
    if provider == 'openai':
        from mr_moneybags.providers.openai import OpenAISemanticClient
        client = OpenAISemanticClient(api_key=values[key_name], model=values['MR_MONEYBAGS_SEMANTIC_MODEL'])
    else:
        from mr_moneybags.providers.deepseek import DeepSeekSemanticClient
        client = DeepSeekSemanticClient(api_key=values[key_name], model=values['MR_MONEYBAGS_SEMANTIC_MODEL'])
    return ModelBackedSemanticInterpreter(client)
