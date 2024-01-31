"""

"""
import urllib.request

from clldutils.jsonlib import load

from cldfbench_uclaphoneticslabarchive import Dataset


def register(parser):
    parser.add_argument('--suffix', choices='mp3 jpg wav tif'.split())


def run(args):
    ds = Dataset()
    media = ds.raw_dir / 'media'
    if not media.exists():
        media.mkdir()
    for d, (url, _, _) in load(ds.etc_dir / 'urls.json').items():
        suffix = d.split('.')[-1]
        if url and (not args.suffix or (args.suffix == suffix)):
            target = media.joinpath(d)
            if not target.exists():
                print(url)
                try:
                    urllib.request.urlretrieve(url, target)
                except:
                    if target.exists():
                        target.unlink()
                    raise
