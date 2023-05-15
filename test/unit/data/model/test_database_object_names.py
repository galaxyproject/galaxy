import galaxy.model.database_object_names as names


def test_foreign_key_single_column():
    assert names.foreign_key("foo", "bar_id") == "foo_bar_id_fkey"


def test_foreign_key_composite():
    assert names.foreign_key("foo", ["bar_id", "buz_id"]) == "foo_bar_id_buz_id_fkey"
    assert names.foreign_key("foo", ["bar_id", "buz_id", "bam_id"]) == "foo_bar_id_buz_id_bam_id_fkey"


def test_unique_constraint_single_column():
    assert names.unique_constraint("foo", "bar") == "foo_bar_key"


def test_unique_constraint_composite():
    assert names.unique_constraint("foo", ["bar", "buz"]) == "foo_bar_buz_key"
    assert names.unique_constraint("foo", ["bar", "buz", "bam"]) == "foo_bar_buz_bam_key"


def test_check_constraint():
    assert names.check_constraint("foo", "bar") == "foo_bar_check"


def test_index_single_column():
    assert names.index("foo", "bar") == "ix_foo_bar"


def test_index_composite():
    assert names.index("foo", ["bar", "buz"]) == "ix_foo_bar_buz"
    assert names.index("foo", ["bar", "buz", "bam"]) == "ix_foo_bar_buz_bam"
