import json
import calendar
from datetime import date, datetime

from webob.multidict import MultiDict

try:
    from webob.multidict import UnicodeMultiDict
except ImportError:
    UnicodeMultiDict = MultiDict
    
from variabledecode import variable_decode
from xmltodict import parse, unparse

from validators import *

__all__ = [
    'Message',
    'IntegerProperty',
    'FloatProperty',
    'BooleanProperty',
    'StringProperty',
    'DateProperty',
    'DateTimeProperty',
    'StructuredProperty'
]

class Property(object):
    INTERNAL_TYPE = None
    
    def __init__(self, repeated=False, validators=None, description=None, example=None):
        self._repeated = repeated
        self._validators = validators
        self._description = description
        self._example = example
        
    def is_required(self):
        """
        Helper method for internal use mostly.
        """
        if not self._validators:
            return False
            
        for v in self._validators:
            if isinstance(v, RequiredValidator):
                return True
        return False
        
    def _cast(self, value):
        return self.INTERNAL_TYPE(value)
        
    def check(self, value):
        """
        Validate the given input.
        """
        if self._repeated and not isinstance(value, (list, set)):
            raise InvalidValueError("This value is repeated.")
        
        import logging
        
        # Try to cast type
        try:
            if self._repeated:
                value = [self._cast(x) for x in value]
            else:
                value = self._cast(value)
        except ValueError:
            raise InvalidValueError("This value is not of the right type.")
            
        if self._validators:
            for v in self._validators:
                v.check(value)
                
        return value

class Message(object):
    
    TYPE_MAP = {
        unicode: ('string', None), 
        long: ('integer', 'int64'), 
        float: ('number', 'double'), 
        dict: ('$ref', None), 
        bool: ('boolean', None),
        date: ('string', 'date'),
        datetime: ('integer', 'date-time')
    }
    
    def __init__(self, description=None, **kwargs):
        self._data = {}
        self._errors = {}
        self._description = description
        
        if kwargs and not self.check(kwargs):
            raise RuntimeError(u"Initial data is invalid: %s" % u' '.join(
                [u'%s: %s' % (k,u' '.join(v)) for k,v in self._errors.iteritems()]
            ))
    
    def check(self, input):
        """
        Validate the given input. Input can be a string, MultiDict or dict
        """
        input_data = None
        
        if isinstance(input, str):
            input_data = json.loads(str)
        elif isinstance(input, (MultiDict, UnicodeMultiDict)):
            input_data = variable_decode(input)
        elif isinstance(input, dict):
            input_data = input
        else:
            raise RuntimeError("Invalid input given to restifier check.")
        
        properties = self.to_dict()
        
        self._errors = {}
        self._data = {}
        
        # Run validation checks....
        for k,v in input_data.iteritems():
            if k in properties:
                try:
                    self._data[k] = properties[k].check(v)
                except ValidationError, e:
                    if k in self._errors:
                        self._errors[k].append(unicode(e))
                    else:
                        self._errors[k] = [unicode(e)]
                
                try:
                    # Call "_check" functions if defined...
                    if hasattr(self, '%s_check' % k):
                        self._data[k] = getattr(self, '%s_check' % k)(v)
                        
                except ValidationError, e:
                    if k in self._errors:
                        self._errors[k].append(unicode(e))
                    else:
                        self._errors[k] = [unicode(e)]
                        
        # Check for missing elements
        for k,v in properties.iteritems():
            if v.is_required() and not (k in self._data or k in self._errors):
                if k in self._errors:
                    self._errors[k].append('This value is required.')
                else:
                    self._errors[k] = ['This value is required.']
                        
        if self._errors:
            return False
        else:
            return True
            
        
    def to_dict(self):
        """
        Create a dictionary mapping property names to property objects.
        """ 
        output = {}
        for k in dir(self):
            prop = getattr(self, k)
            if not isinstance(prop, Property):
                continue
            else:
                output[k] = prop
        return output

    def to_docs(self):
        # Generate a structure that can be used to document this message.
        doc_data = {
            'id':self.__class__.__name__,
            'description': self._description or '', 
            'required':[],
            'properties': {}
        }
        
        for k,v in self.to_dict().iteritems():
            
            
            if isinstance(v, StructuredProperty):
                doc = {
                    '$ref':v._message().__class__.__name__
                }
                #doc['properties'] = v._message().to_docs()['properties']
            else:
                
                t, f = self.TYPE_MAP[v.INTERNAL_TYPE]
                doc = {
                    'type':t,
                    'description':v._description or '',
                    'example':v._example or '',
                    #'is_repeated':v._repeated
                }
                if f:
                    doc['format'] = f
            
            if v._validators:
                for validate in v._validators:
                    doc.update(validate.to_docs())
                    
            if 'required' in doc:
                doc_data['required'].append(k)
                    
            #if isinstance(v, StructuredProperty):
            #    doc['properties'] = v._message().to_docs()['properties']
                
            if v._repeated:
                doc = {
                    'type':'array',
                    'items':doc
                }
            
            doc_data['properties'][k] = doc
            
        return doc_data
        
    def populate_obj(self, obj):
        """
        Populate an object with valid inbound data.
        """
        def populate(data, my_obj):
            for k,v in self.data:
                if hasattr(my_obj, k):
                    if isinstance(v, dict):
                        populate(v, my_obj.k)
                    else:
                        setattr(my_obj, k, v)
        populate(self.valid_data, obj)
        
    @property
    def errors(self):
        """
        Return a dictionary of errors.
        """
        return self._errors
    
    @property    
    def valid_data(self):
        """
        Return a dictionary of valid data.
        """
        return self._data
        
    def to_xml(self):
        return unparse({
            self.__class__.__name__:self._errors and self._errors or self._data
        }) 
        
    def to_json(self):
        return self._custom_json_dumps(self._errors and self._errors or self._data)
        
    def _custom_json_dumps(self, message):
        def json_default(obj):
            # Serialize datetime objects as ISO8601 string
            if isinstance(obj, datetime):
                return calendar.timegm(obj.timetuple())
            elif isinstance(obj, date):
                return obj.isoformat()
            else:
                return obj
        return json.dumps(message, default=json_default)
    
class IntegerProperty(Property):
    INTERNAL_TYPE = long


class DateProperty(Property):
    INTERNAL_TYPE = date
    
    def _cast(self, value):
        if isinstance(value, date):
            return value
        elif isinstance(value, datetime):
            return value.date()
        else:
            return datetime.strptime(value, "%Y-%m-%d")


class DateTimeProperty(Property):
    INTERNAL_TYPE = datetime
    
    def _cast(self, value):
        if isinstance(value, datetime):
            return value
        else:
            return datetime.fromtimestamp(value)


class FloatProperty(Property):
    INTERNAL_TYPE = float


class StringProperty(Property):
    INTERNAL_TYPE = unicode


class BooleanProperty(Property):
    INTERNAL_TYPE = bool 


class StructuredProperty(Property):
    INTERNAL_TYPE = dict
    
    def __init__(self, message_type, **kwargs):
        super(StructuredProperty, self).__init__(**kwargs)

        assert issubclass(message_type, Message)
        
        self._message = message_type
    
    def check(self, value):
        if self._repeated and not isinstance(value, (list, set)):
            raise InvalidValueError("This value is repeated.")
        elif not self._repeated and isinstance(value, (list, set)):
            raise InvalidValueError("This value is must be a single item.")
        
        if not self._repeated:
            value = [value]
        
        all_data = []
        
        for val in value:   
            if not isinstance(val, dict):
                raise InvalidValueError("Data much be structured.")
            
            if self._validators:
                for v in self._validators:
                    v.check(val)
        
            # Gather properties of this structured property    
            properties = self._message().to_dict()
          
            data = {}  
            # Run validation checks...allow exceptions here.
            for k,v in val.iteritems():
                if k in properties:
                    data[k] = properties[k].check(v)
                
                    if hasattr(self, '%s_check' % k):
                        data[k] = getattr(self, '%s_check' % k)(v)
                        
            # Check for missing elements
            for k,v in properties.iteritems():
                if v.is_required() and not k in data:
                    raise ValueRequiredError('This value is required.')
                    
            all_data.append(data)
            
        if not self._repeated:
            return all_data[0]
        else:
            return all_data

