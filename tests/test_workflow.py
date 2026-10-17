import hashlib
import json
import pytest
from omnioperator.workflow import analyze, DatasetWorkspace, FIELDS

def csv_bytes(value='1,5'):
    return ('Date;Time;'+';'.join(FIELDS)+'\n01/01/2020;12.00.00;'+';'.join([value]*len(FIELDS))+'\n').encode()

def test_decimal_comma_and_missing_sentinel():
    assert analyze(csv_bytes())['columns']['T']['mean']==1.5
    assert analyze(csv_bytes('-200'))['columns']['T']['mean'] is None

@pytest.mark.parametrize('raw',[b'',b'a;b\n1;2',csv_bytes('NaN'),csv_bytes('inf'),csv_bytes('bad')])
def test_invalid_input_is_not_silently_coerced(raw):
    with pytest.raises((ValueError,KeyError)): analyze(raw)

def test_hash_tampering_fails_closed(tmp_path):
    source=tmp_path/'input';source.write_bytes(csv_bytes())
    env=DatasetWorkspace(source,tmp_path/'out.json','0'*64)
    env.type_text('inspect')
    with pytest.raises(ValueError,match='checksum'): env.hotkey('ctrl+enter')
    assert not env.output.exists()

def test_export_before_inspection_is_rejected(tmp_path):
    env=DatasetWorkspace(tmp_path/'missing',tmp_path/'out','x')
    env.type_text('export')
    with pytest.raises(ValueError):env.hotkey('ctrl+enter')

@pytest.mark.parametrize('command',['rm -rf /','../secret','inspect;export','__import__("os")'])
def test_only_fixed_capabilities_are_accepted(tmp_path,command):
    env=DatasetWorkspace('unused',tmp_path/'out','x')
    with pytest.raises(ValueError):env.type_text(command)
