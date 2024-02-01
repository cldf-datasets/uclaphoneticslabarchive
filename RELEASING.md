# Releasing the dataset

```shell
cldfbench download cldfbench_uclaphoneticslabarchive.py
```

```shell
cldfbench makecldf cldfbench_uclaphoneticslabarchive.py --glottolog-version v4.8 --with-cldfreadme --with-zenodo
```
Note: For a handful of linked files no valid URL could be found, i.e. the corresponding files seem
to be missing on the UCLA server.

```shell
pytest
```

```shell
cldfbench cldfviz.map --format svg --pacific-centered --no-legend  --language-properties Family_Name cldf --with-ocean --padding-bottom 5 --padding-top 5 --width 20
```

```shell
cldferd --format compact.svg cldf > erd.svg
```

```shell
cldfbench readme cldfbench_uclaphoneticslabarchive.py
```
