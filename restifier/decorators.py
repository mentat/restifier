import json
import mimeparse
import xmltodict

from functools import wraps

JSON = 'application/json'
XML = 'text/xml'
HTML = 'text/html'
FORM = 'application/x-www-form-urlencoded'

__all__ = ['api', 'ErrorMessage']

from messages import Message

class ErrorMessage(Message):
    pass
    
def api(input=None, output=None, auth_required=False, description=None, permissions=None):
    def decorator(func):

        func._auth_required = auth_required
        func._input = input
        func._output = output
        func._description = description
        func._permissions = permissions
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            
            client_accept = self.request.headers.get('Accept', JSON)
            content_type = self.request.headers.get('Content-Type', FORM)
            
            if '_force_json' in self.request.params:
                client_accept = JSON
            
            input_format = mimeparse.best_match([FORM, JSON, XML], content_type)
            output_format = mimeparse.best_match([JSON, XML], client_accept)
            
            msg, msg_ok = input and input() or None, True
            
            if msg:
                if input_format == JSON:
                    try:
                        msg_ok = msg.check(json.loads(self.request.body))
                    except ValueError, e:
                        msg_ok = False
                        msg._errors['_major_'] = str(e)
                    
                elif input_format == XML:
                    msg_ok = msg.check(xmltodict.parse(self.request.body))
                elif input_format == FORM:
                    msg_ok = msg.check(self.request.params)
                else:
                    msg_ok = False
                    msg._errors['_major_'] = "Invalid content type."
                
            if not msg_ok:
                resp = msg
                self.response.set_status(400)
            else:   
                # Let the request continue, response is a dictionary
                resp = func(self, msg and msg.valid_data or None, *args, **kwargs)
            
            self.response.headers['Content-Type'] = output_format
            
            if output_format == JSON:
                self.response.out.write(resp.to_json())
            elif output_format == XML:
                self.response.out.write(resp.to_xml())

        return wrapper
    return decorator