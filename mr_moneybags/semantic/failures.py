from mr_moneybags.semantic.interpreter import SemanticValidationError


class TransportFailure(SemanticValidationError):
    category = 'TransportFailure'


class ModelOutputFailure(SemanticValidationError):
    category = 'ModelOutputFailure'


class EvidenceValidationFailure(SemanticValidationError):
    category = 'EvidenceValidationFailure'


class ContextFailure(SemanticValidationError):
    category = 'ContextFailure'


class ConfigurationFailure(SemanticValidationError):
    category = 'ConfigurationFailure'
