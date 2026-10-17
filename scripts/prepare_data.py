"""Explicit public research-data download; never runs at import/startup."""
import hashlib, io, json, urllib.request, zipfile
from pathlib import Path

def main():
    manifest=json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    with urllib.request.urlopen(manifest['source_url'],timeout=60) as response:
        raw=response.read(3_000_001)
    if len(raw)>3_000_000 or hashlib.sha256(raw).hexdigest()!=manifest['archive_sha256']:
        raise ValueError('archive checksum/size mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        data=archive.read('AirQualityUCI.csv')
    if hashlib.sha256(data).hexdigest()!=manifest['sha256']:
        raise ValueError('CSV checksum mismatch')
    Path('data/AirQualityUCI.csv').write_bytes(data)
    print('Verified dataset downloaded. See data/NOTICE.md for attribution and usage notes.')

if __name__=='__main__': main()
