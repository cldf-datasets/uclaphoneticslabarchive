# Configuration directory

This directory contains "configuration" data, i.e. data which helps with and
guides the conversion of the raw data to CLDF.

- [urls.json](urls.json) maps filenames - as encountered in relative links in the HTML
  pages of the site to working URLs (and the size of the linked file). The URLs needed to
  be manually corrected in several cases, e.g. adapting casing of file extensions (which
  hints at the site having been maintained on a case-insensitive filesystem such as Windows
  at some point).
- [wordist_fields.json](wordlist_fields.json) maps the names of HTML pages which contain
  tables of lexical data to mappings of the column names in the table to meaningful names
  in CLDF tables. In particular, we try to identify the best source column for the word
  form (ideally in broad IPA transcription) and the English gloss. Due to the variety of
  the source data, this mapping cannot reliably be done automatically, but needs to be
  curated by hand.
