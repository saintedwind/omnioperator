"""Local OpenAI-compatible inference; no paid provider or credentials."""
import json
import urllib.request
from urllib.parse import urlsplit
from .base import BaseLLMAdapter
from .openai_vlm import OpenAIVLMAdapter

PROMPT = """Choose the next action for a dataset review. Reply only with JSON.
Read current state first. Select ONE action using these workflow rules:
- If inspected=false and selected is empty: type inspect.
- If selected is inspect or export: press ctrl+enter to execute it.
- If inspected=true, exported=false and the user wants a saved report: type export.
- If the requested work is complete: done.
The initial state is unfinished. Selecting an operation alone does not execute it.
Action JSON forms:
Type: {"action":"type","params":{"text":"inspect"},"done":false} (text may also be export)
Execute selection: {"action":"hotkey","params":{"combo":"ctrl+enter"},"done":false}
Finish: {"action":"done","params":{},"done":true}
Use the CURRENT state, not an earlier state. /no_think"""

class LocalModelAdapter(BaseLLMAdapter):
    name = 'local-model'
    def __init__(self, endpoint='http://127.0.0.1:8081/v1/chat/completions', model='local', timeout=45):
        url=urlsplit(endpoint)
        if url.scheme!='http' or url.hostname!='127.0.0.1' or url.username or url.password or url.query or url.fragment:
            raise ValueError('only explicit IPv4 loopback HTTP endpoints are supported')
        self.endpoint, self.model, self.timeout = endpoint,model,timeout
        self._tokens=0
        self.responses=[]
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise ValueError('model endpoint redirects are disabled')
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def propose_action(self, observation, history, goal):
        state=observation.get('raw_framebuffer','')
        request={'model':self.model,'temperature':0,'max_tokens':160,
                 'response_format':{'type':'json_object'},'chat_template_kwargs':{'enable_thinking':False},
                 'messages':[{'role':'system','content':PROMPT},
                 {'role':'user','content':json.dumps({'goal':goal,'state':state,'history':history},ensure_ascii=False)}]}
        req=urllib.request.Request(self.endpoint,json.dumps(request).encode(),{'Content-Type':'application/json'})
        with self.opener.open(req,timeout=self.timeout) as response:
            raw=response.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('oversized model response')
        body=json.loads(raw)
        content=body['choices'][0]['message']['content']
        self._tokens+=int(body.get('usage',{}).get('total_tokens',0))
        self.responses.append({'content':content,'usage':body.get('usage',{})})
        return OpenAIVLMAdapter._parse(content)
    def token_count(self): return self._tokens
