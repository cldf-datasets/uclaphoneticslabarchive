"""
Seed an ELAN file with the wordlist data for a particular recording.
"""
import pathlib

from cldfbench_uclaphoneticslabarchive import Dataset
from pydub import AudioSegment
from soundfile import SoundFile
from pympi import Eaf

from .downloadmedia import download


def mp3_to_wav(p, out):
    sound = AudioSegment.from_mp3(str(p))
    sound.export(str(out), format="wav")
    return out


def make_eaf(rec, audio, forms):
    if audio.suffix == '.mp3':
        audio = mp3_to_wav(audio, pathlib.Path('{}.wav'.format(rec.id)))
    f = SoundFile(str(audio))
    duration = f.frames / f.samplerate
    eaf = Eaf()
    eaf.add_linked_file(str(audio))
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
    res = pathlib.Path('{}.eaf'.format(rec.id))
    eaf.to_file(str(res))
    return res, audio


def register(parser):
    parser.add_argument('recording')
    parser.add_argument(
        '--mp3',
        action='store_true',
        default=False,
        help='By default, the wav file of a recording is linked to the ELAN file. For quicker '
             'downloads the mp3 file might be preferable. In that case, add this option.'
    )


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    for rec in cldf.objects('ContributionTable'):
        if rec.id == args.recording:
            audio = download(ds, recording=args.recording, suffix='mp3' if args.mp3 else 'wav')
            eaf, wav = make_eaf(rec, audio, rec.all_related('formReference'))
            break
    args.log.info('Created ELAN file {} with linked audio {}'.format(eaf, wav))
