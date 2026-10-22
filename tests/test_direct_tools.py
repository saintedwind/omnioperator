import hashlib,json
import pytest
from omnioperator.direct_tools import DatasetTools,parse_call,run
from omnioperator.workflow import FIELDS

def setup_tools(tmp_path,allow=True):
    source=tmp_path/'source.csv'
    raw=('Date;Time;'+';'.join(FIELDS)+'\n01/01/2020;00.00.00;'+';'.join(['1']*13)+'\n').encode()
    source.write_bytes(raw)
    return DatasetTools(source,tmp_path/'out.json',hashlib.sha256(raw).hexdigest(),allow)

@pytest.mark.parametrize('payload',['{}','[]','{"tool":[]}','{"tool":"bash"}','{"tool":"inspect_dataset","path":"/secret"}'])
def test_model_cannot_expand_tool_contract(payload):
    with pytest.raises(ValueError):parse_call(payload)

def test_real_file_roundtrip(tmp_path):
    tools=setup_tools(tmp_path)
    assert tools.execute('inspect_dataset')['rows']==1
    assert tools.execute('export_report')['saved']
    assert tools.verify('export')

def test_inspection_scope_cannot_write(tmp_path):
    tools=setup_tools(tmp_path,False)
    tools.execute('inspect_dataset')
    with pytest.raises(ValueError,match='capability'):tools.execute('export_report')
    assert tools.verify('inspect')

def test_changed_source_is_not_exported(tmp_path):
    tools=setup_tools(tmp_path);tools.execute('inspect_dataset')
    tools.source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):tools.execute('export_report')
    assert not tools.output.exists()

def test_existing_destination_is_preserved(tmp_path):
    tools=setup_tools(tmp_path);tools.execute('inspect_dataset');tools.output.write_text('keep')
    with pytest.raises(FileExistsError):tools.execute('export_report')
    assert tools.output.read_text()=='keep'

def test_export_requires_inspection(tmp_path):
    tools=setup_tools(tmp_path)
    with pytest.raises(ValueError,match='first'):tools.execute('export_report')
    assert not tools.verify('export')

class ScriptedProbe:
    def __init__(self,tools):self.plan=iter(tools);self.responses=[]
    def token_count(self):return 0
    def choose(self,*args):
        result=next(self.plan);self.responses.append(result);return result

def test_premature_finish_can_recover_without_false_success(tmp_path):
    tools=setup_tools(tmp_path)
    result=run(ScriptedProbe(['finish','inspect_dataset','export_report','finish']),tools,'export','export')
    assert result['success']
    assert any('error' in item for item in result['history'])

def test_repeated_false_completion_has_bounded_retries(tmp_path):
    tools=setup_tools(tmp_path)
    result=run(ScriptedProbe(['finish']*7),tools,'export','export')
    assert not result['success']
    assert result['calls']==3
    assert result['stop_reason']=='recovery_budget'

def test_repeated_completed_operation_is_rejected_and_bounded(tmp_path):
    tools=setup_tools(tmp_path)
    result=run(ScriptedProbe(['inspect_dataset']*7),tools,'export','export')
    assert not result['success']
    assert result['stop_reason']=='recovery_budget'
    assert result['calls']==4


def test_lifecycle_options_track_actual_state(tmp_path):
    tools=setup_tools(tmp_path)
    assert tools.available_tools()==['inspect_dataset','finish','refuse']
    tools.execute('inspect_dataset')
    assert tools.available_tools()==['export_report','finish','refuse']
    tools.execute('export_report')
    assert tools.available_tools()==['finish','refuse']


def test_verify_inspection_detects_source_change(tmp_path):
    tools=setup_tools(tmp_path);tools.execute('inspect_dataset')
    tools.source.write_bytes(b'changed')
    assert not tools.verify('inspect')


def test_verify_export_detects_missing_or_corrupt_file(tmp_path):
    tools=setup_tools(tmp_path);tools.execute('inspect_dataset');tools.execute('export_report')
    tools.output.write_text('{invalid')
    assert not tools.verify('export')
    tools.output.unlink()
    assert not tools.verify('export')


def test_verify_detects_in_memory_report_tampering(tmp_path):
    tools=setup_tools(tmp_path);tools.execute('inspect_dataset')
    tools.report['rows']=999
    assert not tools.verify('inspect')


def test_model_response_counts_are_per_episode(tmp_path):
    adapter=ScriptedProbe(['inspect_dataset','finish','inspect_dataset','finish'])
    first=run(adapter,setup_tools(tmp_path,False),'inspect','inspect')
    second=run(adapter,setup_tools(tmp_path,False),'inspect','inspect')
    assert first['success'] and second['success']
    assert first['calls']==second['calls']==2
    assert len(second['model_responses'])==2


def test_failed_tool_can_recover(tmp_path):
    tools=setup_tools(tmp_path)
    result=run(ScriptedProbe(['export_report','inspect_dataset','export_report','finish']),tools,'export','export')
    assert result['success']
    assert result['history'][0]['ok'] is False
