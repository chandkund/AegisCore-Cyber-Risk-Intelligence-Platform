from data_pipeline.loaders.validate_seed_csvs import validate_all


def test_seed_csvs_validate_clean():
    assert validate_all() == []
