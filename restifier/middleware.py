import re
import json
from webob import Request, Response

PATH_RE = re.compile(r'<([a-zA-z]+):([^>]+)>')

class DocumentedMiddleware(object):   
    def __init__(self, app, api_base='/api/', api_overview=None):
        self.app = app
        self._api_base = api_base
        self._api_overview = api_overview
        
    def __call__(self, environ, start_response):
        # IF the API base is being requested, render documentation...
        if environ.get('PATH_INFO') == '/api':
            resp = Response(
                body=json.dumps(self._generate_base(), indent=1), 
                status=200, headers=[('Content-Type', 'application/json')])
        elif environ.get('PATH_INFO') == '/api/v1':
            resp = Response(
                body=json.dumps(self._generate_docs(environ), indent=1), 
                status=200, headers=[('Content-Type', 'application/json')])
            
        else:
            req = Request(environ)
            resp = req.get_response(self.app)
            
        return resp(environ, start_response)
        
    def _generate_base(self):
        return {
          "apiVersion": "1.0.0",
          "swaggerVersion": "1.2",
          "apis": [
            {
              "path": "/v1",
              "description": "API Version 1"
            }
          ],
          'authorizations':{
              "apiKey": {
                  "type":"apiKey",
                  "passAs":"header",
                  "keyname":"Authorization"
              },
              "userSession": {
                  "type":"apiKey",
                  "passAs":"header",
                  "keyname":"X-Boomerang-User"
              }
          },
          "info": {
            "title": self._api_overview
          }
        }
        
    def _generate_docs(self, environ):
        
        scheme = (environ.get('HTTPS', 'off') == 'on') and 'https://' or 'http://'
        
        docs = {
            'resourcePath':'/v1',
            'apis':[],
            'apiVersion':"1.0",
            'swaggerVersion': "1.2",
            'basePath': scheme + environ.get('HTTP_HOST') + self._api_base,
            'overview':self._api_overview,
            'info':self._api_overview or "",
            'models':{},
            'authorizations':{
                "apiKey": {
                    "type":"apiKey",
                    "passAs":"header",
                    "keyname":"Authorization"
                },
                "userSession": {
                    "type":"apiKey",
                    "passAs":"header",
                    "keyname":"X-Boomerang-User"
                }
            }
        }
        for route in self.app.router.match_routes:
            
            handlerDoc = {
                'path': PATH_RE.sub(r'{\1}', route.template[len(self._api_base):]) ,
                'operations': []
            }
            if route.handler.__doc__:
                handlerDoc['description'] = route.handler.__doc__
                
            for method in ['post','get','put','head','options','delete']:
                if hasattr(route.handler, method):
                    
                    func = getattr(route.handler, method)
                    input = getattr(func, '_input', None)
                    input_docs = input and input().to_docs() or None
                    output = getattr(func, '_output', None)
                    output_docs = output and output().to_docs() or None
                    
                    parameters = []
                    
                    for param in PATH_RE.finditer(route.template):
                        parameters.append({
                            'name':param.group(1), 
                            'description':"Parameter must match %s." % param.group(2), 
                            'required':True,
                            'type':"string", 
                            'paramType':'path'
                        })
                    
                    if method == 'get':
                        parameters += input_docs and [
                            dict(
                                name=x, 
                                description=y.get('description', ''), 
                                required=x in input_docs['required'],
                                type=y.get('type') or y.get('$ref'), 
                                paramType='query'
                                ) for x,y in input_docs['properties'].iteritems()

    
                        ] or []
                    else:
                        parameters += input_docs and [{
                            "name": "body",
                            "description": input_docs['description'],
                            "required": True,
                            "type": input().__class__.__name__,
                            "paramType": "body"
                        }] or []
                    op = {
                        'parameters': parameters,
                        'summary': getattr(func, '_description', None),
                        'notes': func.__doc__ and func.__doc__.strip() or "",
                        'produces':['application/json', 'text/xml'],
                        'httpMethod':method.upper(),
                        'errorResponses':[
                            {
                                'reason':'Invalid input data.',
                                'code':400
                            },
                            {
                                'reason':'Authoriztion required.',
                                'code':401
                            },
                            {
                                'reason':'Insufficient permissions.',
                                'code':403
                            }
                        ],
                        'nickname': '%s%s' % (route.handler.__name__, method.upper()),
                        'responseClass':getattr(func, '_output', None) and \
                            func._output().__class__.__name__ or None
                    }
                    handlerDoc['operations'].append(op)
                    
                    if input:
                        docs['models'][input().__class__.__name__] = input_docs
                        
                    if output:
                        docs['models'][output().__class__.__name__] = output_docs
                    
            docs['apis'].append(handlerDoc)
          
        return docs