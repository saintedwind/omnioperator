import os
from pathlib import Path
import subprocess
import sys


def test_existing_evidence_is_never_overwritten(tmp_path):
    output=tmp_path/'evidence.json'
    output.write_text('keep original evidence',encoding='utf-8')
    root=Path(__file__).resolve().parents[1]
    env=os.environ.copy();env['PYTHONPATH']=str(root)
    result=subprocess.run([sys.executable,'-m','scripts.direct_live','--output',str(output)],
                          cwd=root,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode != 0
    assert 'Result already exists' in result.stderr
    assert output.read_text(encoding='utf-8')=='keep original evidence'
