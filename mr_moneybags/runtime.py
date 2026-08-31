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
    for name in ('OPENAI_API_KEY', 'MR_MONEYBAGS_SEMANTIC_MODEL'):
        if not values.get(name, '').strip():
            raise ConfigurationFailure('missing_' + name)
    from mr_moneybags.providers.openai import OpenAISemanticClient
    from mr_moneybags.semantic.model import ModelBackedSemanticInterpreter
    return ModelBackedSemanticInterpreter(OpenAISemanticClient(
        api_key=values['OPENAI_API_KEY'], model=values['MR_MONEYBAGS_SEMANTIC_MODEL']))
