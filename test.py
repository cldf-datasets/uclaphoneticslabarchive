
def test_valid(cldf_dataset, cldf_logger, cldf_sqlite_database):
    assert cldf_dataset.validate(log=cldf_logger)
    assert cldf_sqlite_database.query(
        "select sum(size) from mediatable where cldf_mediaType = 'audio/mpeg'")[0][0] == 6554419709
