"""

"""
import pathlib

from cldfbench_uclaphoneticslabarchive import Dataset
from pydub import AudioSegment
from mutagen.mp3 import MP3
from pympi import Eaf


def mp3_to_wav(d, rec, f):
    parts = f.id.split('_')
    fname = '{}.{}'.format('_'.join(parts[:-1]), parts[-1])
    p = d / fname
    assert p.exists()
    sound = AudioSegment.from_mp3(str(p))
    sound.export("{}.wav".format(rec.id), format="wav")
    audio = MP3(str(p))
    return pathlib.Path("{}.wav".format(rec.id)), audio.info.length


def make_eaf(rec, wav, duration, forms):
    eaf = Eaf()
    eaf.add_linked_file(str(wav))
    eaf.add_tier('words')
    tiers = set()

    dpw = duration * 1000 // len(forms)
    for i, form in enumerate(forms):
        eaf.add_annotation('words', int(i * dpw), int((i + 1) * dpw), form.id)
        for k, v in form.data['original_data'].items():
            if k not in tiers:
                eaf.add_tier(k, parent='words')
                tiers.add(k)
            eaf.add_annotation(k, int(i * dpw), int((i + 1) * dpw), v)
    eaf.to_file('{}.eaf'.format(rec.id))


def register(parser):
    parser.add_argument('recording')


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    for rec in cldf.objects('ContributionTable'):
        if rec.id == args.recording:
            print(rec.cldf.name)
            for f in rec.all_related('mediaReference'):
                if f.cldf.mediaType == 'audio/mpeg':
                    wav, dur = mp3_to_wav(ds.raw_dir / 'site' / rec.related('languageReference').id, rec, f)
                    break
            forms = rec.all_related('formReference')
            make_eaf(rec, wav, dur, forms)
            break
