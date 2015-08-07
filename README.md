# Restifier

Restifier is a python library for creating and documenting RESTful APIs.  
It includes a middleware component, a set of decorators, and a "forms"
library for validating/documenting requests.  The middle generates a
Swagger compatible JSON specification for the APIs automatically.

## Author

Jesse Lovelace <jesse@hawatian.com>

## License

The MIT License

## Usage

See tests.py for information on usage.  In general, so create a payload 
validator construct a class like this:

```python
class HelloMessage(Message):
    greeting = StringProperty(description="The greating.", 
        validators=[regex(re.compile('^[A-Za-z]+$')), required()])

class HelloResponseMessage(Message):
    salutation = StringProperty(description="The response.")
    tags = StringProperty(repeated=True)
    request = StructuredProperty(HelloMessage)
````

Then decorate your handlers like this:

```python
class HelloHandler(RequestHandler):
    
    @api(input=HelloMessage, output=HelloResponseMessage)
    def post(self, obj):
        return {'salutation':'You are the best.'}
````

Also, to auto-document, use the middleware:

```python
routes = [
    ('/api/v1/hello', HelloHandler)
]

app = DocumentedMiddleware(
    WSGIApplication(routes), 
    api_base="/api/v1",
    api_overview="This is a super important API that does a lot of stuff."
)
```