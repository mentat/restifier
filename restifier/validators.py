import re

REGEX_TYPE = type(re.compile(''))

__all__ = [
    'ValidationError',
    'ValueRequiredError',
    'InvalidValueError',
    'RequiredValidator',
    'BoundsValidator',
    'RegexValidator',
    'ChoiceValidator',
    'ConditionalValidator',
    'required',
    'bounds',
    'regex',
    'cond',
    'choice'
]

class ValidationError(Exception):
    pass

class ValueRequiredError(ValidationError):
    pass
    
class InvalidValueError(ValidationError):
    pass

class Validator(object):
    
    def check(self, value):
        raise NotImplementedError
        
    def to_docs(self):
        return {}
        
class ChoiceValidator(Validator):
    
    def __init__(self, choices):
        super(ChoiceValidator, self).__init__()
        self._choices = choices
        
    def to_docs(self):
        return {
            'choices':self._choices
        }
        
    def check(self, value):
        if not value in self._choices:
            raise InvalidValueError('Value is not a valid choice.')
    
class RequiredValidator(Validator):
    def __init__(self, empty_ok=True, min_count=None, max_count=None):
        super(RequiredValidator, self).__init__()
        self._empty_ok = empty_ok
        self._min_count = min_count
        self._max_count = max_count
        
    def to_docs(self):
        doc = {
            'required': True,
            'empty_ok': self._empty_ok
        }
        
        if self._max_count:
            doc['max_count'] = self._max_count
        if self._min_count:
            doc['min_count'] = self._max_count
        
        return doc
    
    def check(self, value):
        if self._empty_ok:
            if value is None:
                raise ValueRequiredError('This value is required.')
        else:
            if not value:
                raise ValueRequiredError('This value is required.')
                
        if isinstance(value, (list, set)):
            if self._min_count and len(value) < self._min_count:
                raise InvalidValueError('List length is less than the minimum allowed.')
            if self._max_count and len(value) > self._max_count:
                raise InvalidValueError('List length is greater than the maximum allowed.')
    
class BoundsValidator(Validator):
    def __init__(self, min_value=None, max_value=None):
        super(BoundsValidator, self).__init__()
        self._min_value = min_value
        self._max_value = max_value
        
    def to_docs(self):
        doc = {}
        
        if self._max_value:
            doc['max_value'] = self._max_value
            
        if self._min_value:
            doc['min_value'] = self._min_value
        
        return doc
        
    def check(self, value):
        if self._min_value is not None:
            if value < self._min_value:
                raise InvalidValueError('Value is less than the minimum allowed.')
        if self._max_value is not None:
            if value > self._max_value:
                raise InvalidValueError('Value is greater than the maximum allowed.')
        
class RegexValidator(Validator):
    def __init__(self, regex):
        super(RegexValidator, self).__init__()
        assert type(regex) == REGEX_TYPE, "Regex must be a compiled regex."
        self._regex = regex
        
    def to_docs(self):
        return {
            'pattern': self._regex.pattern
        }
        
    def check(self, value):
        if not self._regex.match(value):
            raise InvalidValueError('Value did not match requirements.')
    
class ConditionalValidator(Validator):
    def __init__(self, func):
        super(ConditionalValidator, self).__init__()
        self._func = func
        
    def check(self, value):
        if not self._func(value):
            raise InvalidValueError('Value did not match condition.')
    
    
    
required = RequiredValidator
bounds = BoundsValidator
regex = RegexValidator
cond = ConditionalValidator
choice = ChoiceValidator