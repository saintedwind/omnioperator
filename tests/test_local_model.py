import pytest
from omnioperator.adapters.local_model import LocalModelAdapter
from omnioperator.adapters.openai_vlm import OpenAIVLMAdapter

@pytest.mark.parametrize('url',['https://example.com','http://localhost:8081/v1/chat/completions','http://127.0.0.1@evil.example/v1','http://127.0.0.1:8081/v1?key=x'])
def test_local_endpoint_must_be_literal_loopback(url):
    with pytest.raises(ValueError):LocalModelAdapter(endpoint=url)

def test_malformed_action_type_is_not_executed():
    assert OpenAIVLMAdapter._parse('{"action":[],"done":false}')['action']=='wait'

def test_local_adapter_does_not_connect_at_construction():
    adapter=LocalModelAdapter()
    assert adapter.token_count()==0
    assert adapter.responses==[]
