import json

from mr_moneybags.conversation.models import (
    DecisionOwner, EvidenceReference, ImplementationDelegation, IntentKind, Materiality,
)
from mr_moneybags.semantic.failures import ModelOutputFailure
from mr_moneybags.semantic.models import SemanticAmbiguity, SemanticClaim, SemanticResult


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def _array(items, maximum):
    return {'type': 'array', 'items': items, 'maxItems': maximum}


TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
IDENTIFIER = {'type': 'string', 'minLength': 1, 'maxLength': 128}
EVIDENCE = _array(_object({
    'turn_id': IDENTIFIER, 'start': {'type': 'integer'}, 'end': {'type': 'integer'},
}), 8)
RESULT_SCHEMA = _object({
    'source_turn_id': IDENTIFIER,
    'claims': _array(_object({
        'id': IDENTIFIER, 'concept_id': IDENTIFIER,
        'kind': {'type': 'string', 'enum': [kind.value for kind in IntentKind]},
        'value': TEXT, 'evidence': EVIDENCE,
        'protected_target': {'type': ['string', 'null'], 'minLength': 1, 'maxLength': 512},
        'implementation_delegation': {'type': ['string', 'null'],
                                    'enum': [None, ImplementationDelegation.ORDINARY_IMPLEMENTATION.value]},
    }), 64),
    'ambiguities': _array(_object({
        'topic': TEXT, 'description': TEXT, 'evidence': EVIDENCE,
        'decision_owner': {'type': 'string', 'enum': [owner.value for owner in DecisionOwner]},
        'materiality': {'type': 'string', 'enum': [level.value for level in Materiality]},
        'candidate_interpretations': _array(TEXT, 8),
    }), 32),
})


def _check(value, schema):
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'null': type(None)}
    kinds = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
    if type(value) not in [types[kind] for kind in kinds]:
        raise ModelOutputFailure('invalid_output_type')
    if 'enum' in schema and value not in schema['enum']:
        raise ModelOutputFailure('invalid_output_enum')
    if isinstance(value, dict):
        if value.keys() != schema['properties'].keys():
            raise ModelOutputFailure('unsupported_or_missing_output_fields')
        for name, child in schema['properties'].items():
            _check(value[name], child)
    elif isinstance(value, list):
        if len(value) > schema['maxItems']:
            raise ModelOutputFailure('output_collection_too_large')
        for item in value:
            _check(item, schema['items'])
    elif isinstance(value, str):
        if not value.strip() or len(value) > schema.get('maxLength', 4096):
            raise ModelOutputFailure('invalid_output_text')


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ModelOutputFailure('duplicate_json_key')
        value[key] = item
    return value


def decode_result(text: str, turns) -> SemanticResult:
    if not isinstance(text, str) or len(text) > 262144:
        raise ModelOutputFailure('invalid_output_size')
    try:
        data = json.loads(text, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        raise ModelOutputFailure('malformed_json') from None
    _check(data, RESULT_SCHEMA)
    by_id = {turn.id: turn for turn in turns}
    def evidence(items):
        references = []
        for item in items:
            turn = by_id.get(item['turn_id'])
            start, end = item['start'], item['end']
            quote = turn.raw_text[start:end] if turn is not None else ''
            references.append(EvidenceReference(item['turn_id'], start, end, quote))
        return tuple(references)
    claims = tuple(SemanticClaim(
        item['id'], item['concept_id'], IntentKind(item['kind']), item['value'], evidence(item['evidence']),
        item['protected_target'], ImplementationDelegation(item['implementation_delegation'])
        if item['implementation_delegation'] is not None else None,
    ) for item in data['claims'])
    ambiguities = tuple(SemanticAmbiguity(
        item['topic'], item['description'], evidence(item['evidence']),
        DecisionOwner(item['decision_owner']), Materiality(item['materiality']), tuple(item['candidate_interpretations']),
    ) for item in data['ambiguities'])
    return SemanticResult(data['source_turn_id'], claims, ambiguities)
