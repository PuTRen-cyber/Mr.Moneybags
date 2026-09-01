from mr_moneybags.semantic.interpreter import SemanticValidationError


class TransportFailure(SemanticValidationError):
    category = 'TransportFailure'


class ModelOutputFailure(SemanticValidationError):
    category = 'ModelOutputFailure'


class EvidenceValidationFailure(SemanticValidationError):
    category = 'EvidenceValidationFailure'

    def __init__(self, code, diagnostic=None):
        super().__init__(code)
        self.diagnostic = diagnostic


class ContextFailure(SemanticValidationError):
    category = 'ContextFailure'


class ConfigurationFailure(SemanticValidationError):
    category = 'ConfigurationFailure'
