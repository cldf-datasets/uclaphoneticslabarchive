"""
This module implements the conversion of the HTML pages of the UCLA phonetics lab archive to CLDF.

Sprinkled throughout are comments indicating fixes of the inconsistencies encountered in the
web site's files.
"""
import argparse
import re
import pathlib
import mimetypes
import collections
import urllib.parse
import urllib.request

import lxml.html
from csvw.metadata import URITemplate
from clldutils.jsonlib import dump, load
from clldutils.misc import slug
from clldutils.markup import add_markdown_text
from cldfbench import Dataset as BaseDataset, CLDFSpec

GLOTTOCODES = {
    'ALE_EASTERN': 'east2533',
    'ALE_WESTERN': 'west2616',
    'Gikuyu': 'kiku1240',
    'KOR_CHEJU': 'jeju1234',
    'EST': 'esto1258',
    'PRV': 'occi1239',
    'BNH': 'jama1261',
    'blu': 'hmon1264',
}


def iter_tables(doc):
    def norm(d):
        for k in ['Zulu', 'Hindi', 'Armenian', 'Haiǀǀom', 'Language:']:
            if k in d:
                assert 'Language' not in d
                d['Language'] = d.pop(k)
        for k in ['Tiff Image', 'Tiff Image 2']:
            if k in d:
                d[k.replace('Tiff', 'TIFF')] = d.pop(k)
        return d

    def extract(key, value):
        key = ''.join(key.itertext()).strip()
        if key == 'Rights of Access':
            value = value.xpath('a')[0].attrib['href']
        else:
            value = ''.join(value.itertext()).strip()
        return key, value

    for i, table in enumerate(doc.xpath('.//table'), start=1):
        md = dict(extract(*tr.xpath('td')) for tr in table.xpath('tr'))
        assert int(md['Recording']) == i
        yield i, norm(md)


def iter_trs(doc, fname):
    def extract(td, sep='\n'):
        links = td.xpath('a')
        if links and 'href' in links[0].attrib:
            assert len(links) == 1
            return links[0].attrib['href'], links[0].text
        if td.xpath('div'):
            return td.xpath('div')[0].text.strip()
        return sep.join(td.itertext()).strip()

    tables = list(doc.xpath('.//table'))
    header = None
    for i, tr in enumerate(tables[-1].xpath('.//tr')):
        if not i:
            header = [
                ' '.join((extract(e, sep='') or str(i + 1)).split())
                for i, e in enumerate(tr.xpath('th'))]
        else:
            row = [extract(td) for td in tr.xpath('td')]
            if fname in ['hye_word-list_1973_01.html', 'hye_word-list_1983_01.html']:
                # four columns are stuffed into two
                assert len(row) == 2
                row = [r.strip() for r in (row[0].split('\xa0') + row[1].split('\xa0'))[:4]]
            if len(row) < len(header):
                row += ['' for _ in range(len(header) - len(row))]
            yield i, dict(zip(header, row))


def doc(p):
    # There are corrupted HTML files:
    return lxml.html.fromstring(p.read_text(encoding='utf8').replace('<t/d>', '</td>'))


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "uclaphoneticslabarchive"

    def get_page(self, path=None, fname=None):
        url = 'http://archive.phonetics.ucla.edu/Language%20Indices/index_available.htm'
        target = self.raw_dir / 'site' / 'index.html'

        if path:
            path = path.replace('maj.html', 'MAJ.html')
            assert 'Language/' in path
            lid, fname_ = path.split('Language/')[1].split('/', maxsplit=1)
            fname = fname or fname_
            url = urllib.parse.urljoin(url, path)
            if not self.raw_dir.joinpath('site', lid).exists():
                self.raw_dir.joinpath('site', lid).mkdir()
            target = self.raw_dir / 'site' / lid / fname

        if url.endswith('mpz_word-list_1976_01.mp3'):
            url += '.LCK'

        # Wrong wordlist linked from MNR index:
        url = url.replace('/MNR/bul_word-list_1971_01', '/MNR/mnr_word-list')
        # Non-existing page linked instead of wordist:
        url = url.replace('amh_conversation_1967', 'amh_word-list_1967')

        if not target.exists():
            #print(url)
            #try:
            #    urllib.request.urlretrieve(url, target)
            #except:
            #    parts = url.split('.')
            #    url = '.'.join(parts[:-1]) + '.' + parts[-1].upper()
            #    try:
            #        urllib.request.urlretrieve(url, target)
            #    except:
            #        raise
            pass
        return url, target

    def cldf_specs(self):
        return CLDFSpec(dir=self.cldf_dir, module="Wordlist")

    def cmd_readme(self, args: argparse.Namespace) -> str:
        # link map and ERD
        return add_markdown_text(
            super().cmd_readme(args), """
{}

### Coverage

The CLDF dataset contains all textual data and metadata from http://archive.phonetics.ucla.edu/ and
provides URLs of all media files associated with recordings on http://archive.phonetics.ucla.edu/

The dataset covers all languages represented in the archive.

![](map.svg)
*Languages represented in the archive color-coded by language family.*


### Dataset schema

The following entity-relationship diagram shows how the tables of the dataset are related. For
detailed descriptions of the individual columns, see [the CLDF README](cldf/README.md).

![](erd.svg)
""".format(self.dir.joinpath('NOTES.md').read_text(encoding='utf8')), section='Description')

    def cmd_download(self, args):
        mdfields = collections.Counter()
        wlfields = {}

        # Read the language index:
        index = doc(self.get_page()[1])
        for link in index.xpath('.//a'):
            if '/Language/' in link.attrib['href']:
                self.get_page('../Language' + link.attrib['href'].split('/Language')[1], fname='index.html')

        fname_to_url = {}
        data = {}

        # Read the index pages of individual languages:
        for d in self.raw_dir.joinpath('site').iterdir():
            if d.is_dir():
                index = doc(d.joinpath('index.html'))
                lname = index.xpath('.//title')[0].text

                mds = list(d.glob('*_record_details.html'))
                assert len(mds) == 1 or d.name == 'MZQ', d
                if mds:
                    md = dict(iter_tables(lxml.html.fromstring(mds[0].read_text(encoding='utf8'))))
                    for d_ in md.values():
                        mdfields.update([k for k, v in d_.items() if v])
                else:
                    md = {}

                wlfields[d.name] = {}
                i = -1

                recordings = []
                words = {}
                for i, rec in iter_trs(index, None):
                    rec['details'] = md.get(i, {})
                    if d.name == 'MNR' and i == 1:
                        rec['Word List Entries'] = ('mnr_word-list.html#1', rec['Word List Entries'][1])
                    recordings.append(rec)

                    if rec.get('Word List Entries'):
                        fname = rec.get('Word List Entries')[0].split('#')[0]
                        if fname not in words:
                            words[fname] = dict(
                                scans=[rec[k][0] for
                                       k in ['Scanned Word List (JPG)', 'JPG 2', 'Scanned Word List (TIF)', 'TIF 2']
                                       if rec.get(k)],
                                words=[w for _, w in iter_trs(doc(d.joinpath(fname)), fname)])
                        if words[fname]:
                            wlfields[d.name][fname] = {w: '' for w in words[fname]['words'][0] if w != 'Entry'}

                assert i >= 0

                data['{}|{}'.format(lname, d.name)] = dict(recordings=recordings, words=words)

                for link in index.xpath('.//a'):
                    if not (link.attrib['href'].startswith('..') or link.attrib['href'].startswith('http:')):
                        if '.wav' in link.attrib['href'] or '.tif' in link.attrib['href']:
                            continue
                        url, fname = self.get_page('../Language/{}/{}'.format(d.name, link.attrib['href'].split('#')[0]))
                        fname_to_url['{}/{}'.format(d.name, fname.name)] = url

        #dump(wlfields, self.etc_dir / 'wordlist_fields.json', indent=2)
        dump(data, self.raw_dir / 'recordings.json', indent=2)
        #dump(sorted(fname_to_url.items()), self.raw_dir / 'fname2url.json', indent=2)

    def cmd_makecldf(self, args):
        self.schema(args.writer.cldf)

        wordlist_fields = load(self.etc_dir / 'wordlist_fields.json')
        fnames = {tuple(k.split('/')): v for k, v in load(self.etc_dir / 'urls.json').items()}
        mids = {}

        fields = collections.Counter()
        glangs = {}
        for l in args.glottolog.api.languoids():
            glangs[l.id] = l
            if l.iso:
                glangs[l.iso] = l

        concepts = collections.defaultdict(set)
        for k, data in load(self.raw_dir / 'recordings.json').items():
            lname, dname = k.split('|')
            glang = glangs[GLOTTOCODES[dname]] if dname in GLOTTOCODES else glangs[dname.lower()]

            geolang = glang
            if geolang.latitude is None:
                geolang = glangs[glang.lineage[-1][1]]
                assert geolang.latitude is not None

            args.writer.objects['LanguageTable'].append(dict(
                ID=dname,
                Name=lname,
                Glottocode=glang.id,
                Latitude=geolang.latitude,
                Longitude=geolang.longitude,
                Macroarea=glang.macroareas[0].name,
                ISO639P3code=glang.iso,
                Family_Name=glangs[glang.lineage[0][1]].name if glang.lineage else 'Isolate',
            ))

            wordlist2ids = collections.defaultdict(list)
            text2ids = collections.defaultdict(list)
            for fname, words in data['words'].items():
                for form, gloss, entry, eid in iter_words(
                        fname, words['words'], wordlist_fields[dname][fname]):
                    if not any(cue in fname for cue in ['word-list', 'ear-training', 'sounds']):
                        text2ids[fname].append((eid, int(entry['Entry'])))
                        args.writer.objects['ExampleTable'].append(dict(
                            ID=eid,
                            Language_ID=dname,
                            Primary_Text=form,
                            Translated_Text=gloss,
                            Speaker=entry.get('Speaker'),
                            original_data=entry,
                        ))
                    else:
                        pid = slug(gloss) or 'NA'
                        concepts[pid].add(gloss)
                        wordlist2ids[fname].append((eid, int(entry['Entry'])))
                        args.writer.objects['FormTable'].append(dict(
                            ID=eid,
                            Form=norm_form(form),
                            Language_ID=dname,
                            Parameter_ID=pid,
                            original_data=entry,
                            Scan_IDs=[fname.replace('.', '_') for fname in words['scans']],
                        ))

            for rid, r in enumerate(data['recordings'], start=1):
                fields.update([k for k, v in r.items() if v])

                wids, tids = [], []
                wordlist_entries = r['Word List Entries']
                if wordlist_entries:
                    fname, items = wordlist_entries
                    fname = fname.split('#')[0]
                    if fname in wordlist2ids:
                        wids = linked_words(fname, items, wordlist2ids[fname])
                    else:
                        tids = linked_words(fname, items, text2ids[fname])

                ncontents = norm_contents(r['details'].get('Recording Contents', ''))
                date, year = norm_date(r['details'].get('Recording Date'))
                args.writer.objects['ContributionTable'].append(dict(
                    ID='{}-{}'.format(dname, rid),
                    Name='{} recording {}'.format(lname, rid),
                    Description='Recording of {}'.format(' and '.join(ncontents)),
                    Position=rid,
                    Language_ID=dname,
                    Contributor=norm_fieldworker(r['details'].get('Fieldworkers')),
                    contents=ncontents,
                    location=norm_location(r['details'].get('Recording Location')),
                    date=date,
                    year=year,
                    rights_of_access=r['details'].get('Rights of Access'),
                    Media_IDs=[],
                    Form_IDs=wids,
                    Text_IDs=tids,
                    dialect=norm_dialect(r['details'].get('Dialect')),
                    speakers=norm_speakers(r['details'].get('Speakers')),
                    speaker_name=norm_speaker_name(r['details'].get('Speaker Name')),
                    speaker_origin=norm_speaker_origin(r['details'].get('Speaker Origin')),
                    wordlist_entries=r['details'].get('Unicode Word List Entries'),
                    original_recording_medium=norm_orm(r['details'].get('Original Recording Medium')),
                ))
                rec = args.writer.objects['ContributionTable'][-1]
                for suffix in [
                    'WAV',
                    'MP3',
                    ('Scanned Word List (JPG)', 'JPG'),
                    ('Scanned Word List (TIF)', 'TIF'),
                    ('JPG 2', 'JPG'),
                    ('TIF 2', 'TIF'),
                ]:
                    if isinstance(suffix, tuple):
                        attr, suffix = suffix
                    else:
                        attr = suffix
                    quality = {
                        'WAV': ['WAV Digitization Quality'],
                        'MP3': ['MP3 Bit Rate'],
                        'JPG': ['JPG Quality', 'JPG Image Quality'],
                        'TIF': ['TIFF Image Quality'],
                    }
                    desc = None
                    for prop in quality[suffix]:
                        if prop in r['details']:
                            desc = r['details'][prop]
                            break
                    fname = r[attr][0] if isinstance(r.get(attr), list) else r.get(attr)
                    if fname and fnames[dname, fname][0]:
                        # There are a handful of linked files which do not exist on the server.
                        rec['Media_IDs'].append(fname.replace('.', '_'))
                        if fname not in mids:
                            args.writer.objects['MediaTable'].append(dict(
                                ID=fname.replace('.', '_'),
                                Name=fname,
                                Description=desc,
                                Media_Type=mimetypes.guess_type('a.' + suffix),
                                Download_URL=fnames[dname, fname][0],
                                size=fnames[dname, fname][1],
                            ))
                            mids[fname] = fname.replace('.', '_')

        for pid, glosses in sorted(concepts.items()):
            args.writer.objects['ParameterTable'].append(dict(
                ID=pid,
                Name=' | '.join(sorted(glosses))
            ))

    def schema(self, cldf):
        cldf.properties['dc:description'] = \
            ("This CLDF dataset provides the data of the UCLA Phonetics Lab Archive. It is modeled "
             "as a CLDF `Wordlist` because most of the recordings contain elicitations of "
             "wordlists, but the main data of interest may be the audio recordings themselves, "
             "which are modeled as items in a `MediaTable`, related to recording sessions, modeled "
             "as items in a `ContributionTable`.")
        cldf.add_component(
            'LanguageTable',
            'Family_Name',
        )
        cldf['LanguageTable', 'ID'].common_props['dc:description'] = \
            ('We use subdirectory names under http://archive.phonetics.ucla.edu/Language/ as '
             'identifiers for languages. While these are typically the uppercase "SIL codes" of '
             'the corresponding languages, there are some exceptions.')
        cldf['LanguageTable', 'ID'].valueUrl = URITemplate(
            'http://archive.phonetics.ucla.edu/Language/{ID}/')
        t = cldf.add_component(
            'ContributionTable',
            {
                'name': 'Language_ID',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#languageReference',
            },
            {
                'name': 'Position',
                'datatype': 'integer',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#position',
            },
            {
                'name': 'contents',
                'separator': '; ',
                'dc:description': "List of genre types of the recorded content"
            },
            {
                'name': 'rights_of_access',
                'propertyUrl': 'dc:license',
            },
            {
                'name': 'location',
                'propertyUrl': 'dc:spatial',
            },
            {
                'name': 'date',
                'propertyUrl': 'dc:temporal',
            },
            {
                'name': 'year',
                'datatype': 'integer',
            },
            'dialect',
            'speakers',
            'speaker_name',
            'speaker_origin',
            {
                'name': 'wordlist_entries',
                'dc:description': 'A specification of entries in the corresponding (written) '
                                  'wordlist that are recorded in the audio files.'
            },
            {
                'name': 'original_recording_medium',
                'separator': '|'
            },
            {
                'name': 'Media_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#mediaReference',
                'dc:description':
                    'Audio recordings are available in WAV and MP3 formats. Transcripts of the '
                    'recordings are available as scanned image files of original fieldwork word '
                    'lists. The scanned images often contain additional information not easily '
                    'presented in `FormTable`. They are available both in compressed JPG and '
                    'uncompressed TIF format.'
            },
            {
                'name': 'Form_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference',
            },
            {
                'name': 'Text_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#exampleReference',
            },
        )
        t.common_props['dc:description'] = \
            ('The recordings of the archive are modeled as contributions because provenance '
             'metadata is attached to these entities.')
        cldf['ContributionTable', 'Contributor'].common_props['dc:description'] = \
            "The fieldworkers responsible for the recording"
        cldf.add_component(
            'MediaTable',
            {
                'name': 'size',
                'datatype': 'integer',
                'dc:description': 'File size in bytes'
            }
        )
        cldf.add_component('ParameterTable')
        cldf.add_columns(
            'FormTable',
            {
                'name': 'original_data',
                'datatype': 'json',
                'dc:description': "JSON object holding all data of a row as read from a word list "
                                  "table from the archive web site."
            },
            {
                'name': 'Scan_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#mediaReference',
            },
        )
        cldf['FormTable'].common_props['dc:description'] = \
            ("Words from elicited wordlists. Note that often no transcriptions are provided. In "
             "these cases, the string `NA` is given as `Form` rather than omitting the word, "
             "because we want to record all metadata as well as the fact that some word appears "
             "in a certain position in the recordings or scans.")
        t = cldf.add_component(
            'ExampleTable',
            {
                'name': 'Position',
                'datatype': 'integer',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#position',
            },
            'Speaker',
            {
                'name': 'original_data',
                'datatype': 'json',
                'dc:description':
                    "JSON object holding all data of a row as read from a word list "
                    "table from the archive web site."
            }
        )
        t.common_props['dc:description'] = \
            ("Phrases or other text chunks from conversations or stories. Note that sometimes no "
             "transcriptions or not translations are provided. In these cases, the string `NA` is "
             "given as `Primary_Text` or `Translated_Text` rather than omitting the phrase, "
             "because we want to record all metadata as well as the fact that some phrase appears "
             "in a certain position in the recordings or scans.")


def norm_form(c):
    if c in [
        "(no transcription)",
        "----",
        "No transcription given",
        "no phonemic transcription given",
        "Transcription illegible",
        "No IPA given",
        "(not on wordlist)",
    ]:
        return 'NA'
    return c


def norm_dialect(c):
    if c in """dialect not specified
Dialect not specified
dialects not specified
dialect unknown
dialect unkown
dialect unspecified
Dialect unspecified
N/A
not specified
Speaker dialect not specified
unknown""".split('\n'):
        return None
    return c


def norm_speakers(c):
    if not c:
        return None
    if c in 'unknown n/a N/A':
        return None
    return c


def norm_speaker_name(c):
    if not c:
        return None
    if c in 'Speaker not identified Speaker name unspecified N/A unknown Unknown':
        return None
    return c


def norm_speaker_origin(c):
    if not c:
        return None
    if c in """Speaker origin not specified
Speakers' origins not specified
Speaker origin not specified
Speaker origins not specified
Speaker origins unknown
speaker origin unknown
Speaker origin unknown
Speaker Origin Unknown
Speaker origin unspecified
not specified
unknown""".split('\n'):
        return None
    return c


def norm_fieldworker(c):
    if c in [
        'Fieldworker not specified',
        'fieldworker(s) not specified',
        'Fieldworker(s) unspecified',
        'N/A',
        'not specified',
        'unknown',
        'Unknown',
        'Unspecified',
    ]:
        return None
    return c


def norm_orm(c):
    return {
        '32K DAT': ["DAT tape, 32 kHz"],
        "48K DAT": ["DAT tape, 48 kHz"],
        "casette tape": ["cassette tape"],
        "Casette tape": ["cassette tape"],
        "Casette Tape": ["cassette tape"],
        "cassette": ["cassette tape"],
        "Cassette tape": ["cassette tape"],
        "Cassette Tape": ["cassette tape"],
        "reel tape": [""],
        "Reel tape": ["reel tape"],
        "Reel Tape": ["reel tape"],
        "Reel Tape, Cassette Tape": ["reel tape", "cassette tape"],
        "unknown": None,
        "Unknown": None,
    }.get(c, [c])


def norm_date(c):
    if not c:
        return None, None
    if c in [
        'N/A',
        'not specified',
        'Recording date(s) not given',
        'Date unspecified',
    ]:
        return None, None
    if c.lower().endswith('unknown'):
        return None, None
    m = re.search('(?P<year>[0-9]{4})', c)
    assert m
    return c, int(m.group('year')) or None


def norm_location(c):
    return None if c and c.lower() == 'unknown' else c


def norm_contents(c):
    c = re.split(' and |, ', c.lower().replace('Running speech', 'continuous speech'))
    return sorted([w.replace('wordlist', 'word list') for w in c])


def iter_words(fname, words, fieldmap):
    assert all(any(k in v for v in set(fieldmap.values())) for k in ['Gloss', 'Form']), 'missing col: {}'.format(fname)
    revfieldmap = {}
    for k, v in fieldmap.items():
        for vv in v.split():
            revfieldmap[vv] = k

    leid = None
    i = 0
    for w in words:
        if leid is None and not w['Entry']:
            # Sometimes the first row in the table is used for notes and comments.
            continue
        i += 1
        wid = '{}-{}'.format(fname.split('.')[0], i)
        if not w['Entry']:
            w['Entry'] = leid
        if w['Entry'].endswith('.5') or w['Entry'].endswith('.7'):
            # There are some entry number like "2" and "2.5". We subsume these
            # under "2"
            assert leid
            w['Entry'] = leid
        if fname == 'nmn_word-list_0000_01.html' and w['Entry'] == '612':
            # There's a typo in the entry number:
            w['Entry'] = '162'
        try:
            if revfieldmap['Form'] == 'NA':
                form = 'NA'
            else:
                form = w[revfieldmap['Form']].strip() or 'NA'
        except:
            print(fname)
            print(revfieldmap)
            raise
        yield (
            form,
            '' if revfieldmap['Gloss'] == 'NA' else w.get(revfieldmap['Gloss'], ''),
            {k: v for k, v in w.items() if v},
            wid)
        leid = w['Entry']


def linked_words(fname, ranges, items):
    batches = []
    batch = []
    leid = -1
    for id_, eid in items:
        if eid == 1 and batch and leid > 1:
            # There are more sets of entry numbers starting with 1.
            batches.append(batch)
            batch = []
        batch.append((id_, eid))
        leid = eid
    assert batch, '{}: {}\t{}'.format(fname, ranges, len(items))
    batches.append(batch)

    entry_numbers = []
    for r in ranges.split(','):  # multiple ranges
        if r.lower() == 'paragraph':
            entry_numbers.append([1])
        else:
            if '-' in r:
                s, e = [int(d.strip()) for d in r.split('-')]
                entry_numbers.append(list(range(s, e + 1)))
            else:
                entry_numbers.append([int(r.strip())])

    wids = []
    for r in entry_numbers:
        if len(batches) > 1:
            # If a range matches exactly the entry numbers of a batch, we choose the words in this
            # batch:
            for batch in batches:
                if r == [eid for _, eid in batch]:
                    wids.extend([wid for wid, _ in batch])
                    break
            else:
                # Otherwise, we interpret the range as subset of the first batch:
                for wid, eid in batches[0]:
                    if eid in r:
                        wids.append(wid)
        else:
            # Otherwise, we just chose all words with matching entry numbers:
            for wid, eid in batches[0]:
                if eid in r:
                    wids.append(wid)

    return wids
