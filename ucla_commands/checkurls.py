"""

"""
import mimetypes

import requests
from tqdm import tqdm
from clldutils.jsonlib import load

from cldfbench_uclaphoneticslabarchive import Dataset


def run(args):
    ds = Dataset()
    for fname, (url, size) in tqdm(load(ds.etc_dir / 'urls.json').items()):
        if url:
            mimetype = mimetypes.guess_type(fname)[0]
            if mimetype.split('/')[0] in ['audio', 'image']:
                res = requests.head(url)
                assert res.status_code == 200, 'HTTP {}: {}'.format(res.status_code, url)
                assert int(res.headers['Content-Length']) == size, '{}: {}'.format(
                    url, res.headers)
