import re
import random
import unittest

from validators import *
from messages import *

from decorators import *
from middleware import *

class TestValidators(unittest.TestCase):

    def test_required(self):
        r = RequiredValidator()
        
        # Check none raises
        self.assertRaises(ValueRequiredError, r.check, None)
        
        # Check empty string does not
        r.check('')
        
        r2 = RequiredValidator(empty_ok=False)
        # Check none raises
        self.assertRaises(ValueRequiredError, r2.check, None)
        
        # Check empty string does too
        self.assertRaises(ValueRequiredError, r2.check, '')
        
        r3 = RequiredValidator(min_count=1, max_count=2)
        self.assertRaises(InvalidValueError, r3.check, [])
        self.assertRaises(InvalidValueError, r3.check, [1,1,1])
        
        r3.check([1])
        r3.check(['ok','cool'])
        
    def test_bounds(self):
        
        b = BoundsValidator(min_value=1, max_value=100)
        
        self.assertRaises(InvalidValueError, b.check, 0)
        self.assertRaises(InvalidValueError, b.check, -1)
        self.assertRaises(InvalidValueError, b.check, 101)
        self.assertRaises(InvalidValueError, b.check, 1000)
        b.check(1)
        b.check(100)
        b.check(50)
        
        b2 = BoundsValidator(min_value=1)
        self.assertRaises(InvalidValueError, b2.check, 0)
        self.assertRaises(InvalidValueError, b2.check, -1)
        b2.check(1)
        b2.check(50)
        b2.check(100)
        b2.check(101)
        
    def test_regex(self):
        import re
        
        r = RegexValidator(regex=re.compile("^[0-9]+[a-z]{,2}[0-9]$"))
        r.check('00000aa9')
        self.assertRaises(InvalidValueError, r.check, "aaaaa")
        self.assertRaises(InvalidValueError, r.check, "00000aa99")
        
    def test_condition(self):
        
        c = ConditionalValidator(lambda x: x % 3 == 0)
        c.check(0)
        c.check(3)
        self.assertRaises(InvalidValueError, c.check, 1)
        self.assertRaises(InvalidValueError, c.check, 2)
        

class TestMessages(unittest.TestCase):
    
    def test_message(self):
        
        class EducationMessage(Message):
            school = StringProperty(description="The name of the school.")
            degree = StringProperty(validators=[RegexValidator(re.compile(r'(MS|PHD|BS)'))], 
                description="Highest degree achieved.")
        
        class HelloMessage(Message):
            name = StringProperty(validators=[RequiredValidator()], description="The name")
            age = IntegerProperty(validators=[BoundsValidator(min_value=10)], description="The age")
            education = StructuredProperty(EducationMessage, repeated=True, description="Education details.")
            ratio = FloatProperty()
            created_at = DateTimeProperty()
            final_year = DateProperty()
            
        hm = HelloMessage()
        assert(hm.check({
            'name':'Blah',
            'age':123,
            'education':[{'school':'Yale', 'degree':'MS'}, {'school':'NCSU', 'degree':'BS'}],
            'final_year':'2012-12-01',
            'created_at': 1406650720,
            'ratio':1.231232
        })), hm.errors
        
        hm.valid_data
        hm.to_docs()
        print hm.to_json()
        hm.to_xml()
    
class TestDecorators(unittest.TestCase):
    
    def test_app(self):
        from webapp2 import WSGIApplication, RequestHandler, Request
        
        class HelloMessage(Message):
            greeting = StringProperty(description="The greating.", 
                validators=[regex(re.compile('^[A-Za-z]+$')), required()])
        
        class HelloResponseMessage(Message):
            salutation = StringProperty(description="The response.")
        
        
        class HelloHandler(RequestHandler):
            
            @api(input=HelloMessage, output=HelloResponseMessage)
            def post(self, obj):
                return HelloResponseMessage(salutation='You are the best.')
                
        routes = [
            ('/api/v1/hello', HelloHandler)
        ]
        
        app = WSGIApplication(routes)
        
        request = Request.blank('/api/v1/hello', POST='{}', headers={'Content-Type':'application/json'})
        request.method = 'POST'
        response = request.get_response(app)
        assert response.status_int==400
        
        request = Request.blank('/api/v1/hello', POST='{"greeting":"Hi"}', headers={'Content-Type':'application/json'})
        request.method = 'POST'
        response = request.get_response(app)
        assert response.status_int==200
        
        request = Request.blank('/api/v1/hello', POST='{"greeting":"Hi123123"}', headers={'Content-Type':'application/json'})
        request.method = 'POST'
        response = request.get_response(app)
        assert response.status_int==400
        
    def test_document(self):
        from webapp2 import WSGIApplication, RequestHandler, Request
        
        class HelloMessage(Message):
            greeting = StringProperty(description="The greating.", 
                validators=[regex(re.compile('^[A-Za-z]+$')), required()])
        
        class HelloResponseMessage(Message):
            salutation = StringProperty(description="The response.")
            tags = StringProperty(repeated=True)
            request = StructuredProperty(HelloMessage)
        
        class HelloHandler(RequestHandler):
            
            @api(input=HelloMessage, output=HelloResponseMessage)
            def post(self, obj):
                return {'salutation':'You are the best.'}
                
        routes = [
            ('/api/v1/hello', HelloHandler)
        ]
        
        app = DocumentedMiddleware(
            WSGIApplication(routes), 
            api_base="/api/v1",
            api_overview="This is a super important API that does a lot of stuff."
        )
        
        request = Request.blank('/api/v1', headers={'Content-Type':'application/json'})
        response = request.get_response(app)
        #print response.body

if __name__ == '__main__':
    unittest.main()