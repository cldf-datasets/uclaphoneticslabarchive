# Releasing the dataset


```shell
cldfbench makecldf cldfbench_uclaphoneticslabarchive.py --glottolog-version v4.8 --with-cldfreadme --with-zenodo
```

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
