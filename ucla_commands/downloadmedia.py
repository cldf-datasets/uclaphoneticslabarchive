"""
Download media files from the UCLA phonetics lab archive website.
"""
import urllib.request

from clldutils.jsonlib import load
from csvw.datatypes import anyURI

from cldfbench_uclaphoneticslabarchive import Dataset


def register(parser):
    parser.add_argument('--suffix', choices='mp3 jpg wav tif'.split())
    parser.add_argument(
        '--recording',
        help="ID of a recording for which to retrieve media files")


def run(args):
    ds = Dataset()
    download(ds, args.recording, args.suffix)


def download(ds, recording=None, suffix=None):
    media = ds.raw_dir / 'media'
    if not media.exists():
        media.mkdir()
    selection = None
    target = None
    if recording:
        for rec in ds.cldf_reader().objects('ContributionTable'):
            if rec.id == recording:
                selection = [
                    anyURI.to_string(f.cldf.downloadUrl) for f in rec.all_related('mediaReference')]
    for d, (url, _, _) in load(ds.etc_dir / 'urls.json').items():
        if selection and url not in selection:
            continue
        if url and (not suffix or (d.split('.')[-1] == suffix)):
            target = media.joinpath(d)
            if not target.exists():
                print(url)
                try:
                    urllib.request.urlretrieve(url, target)
                except:
                    if target.exists():
                        target.unlink()
                    raise
    return target
