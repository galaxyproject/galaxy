from galaxy.model.database_object_names import (
    build_check_constraint_name,
    build_foreign_key_name,
    build_index_name,
    build_unique_constraint_name,
)


def test_foreign_key_single_column():
    assert build_foreign_key_name("foo", "bar_id") == "foo_bar_id_fkey"


def test_foreign_key_composite():
    assert build_foreign_key_name("foo", ["bar_id", "buz_id"]) == "foo_bar_id_buz_id_fkey"
    assert build_foreign_key_name("foo", ["bar_id", "buz_id", "bam_id"]) == "foo_bar_id_buz_id_bam_id_fkey"


def test_unique_constraint_single_column():
    assert build_unique_constraint_name("foo", "bar") == "foo_bar_key"


def test_unique_constraint_composite():
    assert build_unique_constraint_name("foo", ["bar", "buz"]) == "foo_bar_buz_key"
    assert build_unique_constraint_name("foo", ["bar", "buz", "bam"]) == "foo_bar_buz_bam_key"


def test_check_constraint():
    assert build_check_constraint_name("foo", "bar") == "foo_bar_check"


def test_index_single_column():
    assert build_index_name("foo", "bar") == "ix_foo_bar"


def test_index_composite():
    assert build_index_name("foo", ["bar", "buz"]) == "ix_foo_bar_buz"
    assert build_index_name("foo", ["bar", "buz", "bam"]) == "ix_foo_bar_buz_bam"
