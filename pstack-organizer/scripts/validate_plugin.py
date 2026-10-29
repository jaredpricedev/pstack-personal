"""Check companion packaging without third-party dependencies."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
repo = root.parent
manifests = [json.loads((root / path).read_text()) for path in ("plugin.json", ".cursor-plugin/plugin.json", ".claude-plugin/plugin.json")]
assert all(m['name'] == 'pstack-organizer' and m['version'] == manifests[0]['version'] for m in manifests)
for marketplace in ('.cursor-plugin/marketplace.json', '.claude-plugin/marketplace.json'):
    data = json.loads((repo / marketplace).read_text())
    assert data['name'] == 'pstack-personal'
    assert any(e['name'] == 'pstack-organizer' and (repo / e['source']).resolve() == root for e in data['plugins'])
for skill in (root / 'skills').glob('*/SKILL.md'):
    content = skill.read_text()
    assert content.startswith('---\n') and '\ndescription:' in content
    assert re.search(r'^name: ' + re.escape(skill.parent.name) + '$', content, re.M)
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if not target.startswith(('http:', 'https:', '#')):
            assert (skill.parent / target.split('#')[0]).exists(), (skill, target)
print('Organizer packaging validated.')
