from collections import Counter

from galaxy_test.shard import (
    assign_groups_to_shards,
    build_groups,
    select_shard,
    ShardGroup,
)


class FakeModule:
    def __init__(self, name):
        self.__name__ = name


class FakeItem:
    def __init__(self, module_name, class_name, node_id):
        self.module = FakeModule(module_name)
        self.cls = type(class_name, (), {}) if class_name else None
        self.nodeid = node_id

    def __repr__(self):
        return self.nodeid


def make_items(*specs):
    return [FakeItem(module, cls, f"{module}::{cls}::{name}") for module, cls, name in specs]


def test_class_items_stay_in_one_group():
    items = make_items(
        ("test_a", "TestOne", "test_x"),
        ("test_a", "TestOne", "test_y"),
        ("test_a", "TestTwo", "test_z"),
    )
    groups = {group.key: group for group in build_groups(items, {})}
    assert set(groups) == {"test_a::TestOne", "test_a::TestTwo"}
    assert len(groups["test_a::TestOne"].items) == 2


def test_module_level_items_group_by_module():
    items = make_items(("test_a", None, "test_x"), ("test_a", None, "test_y"))
    groups = build_groups(items, {})
    assert len(groups) == 1
    assert groups[0].key == "test_a"


def test_unknown_groups_get_a_default_weight():
    groups = build_groups(make_items(("test_a", "TestOne", "test_x")), {})
    assert groups[0].seconds > 0


def test_recorded_durations_are_used():
    groups = build_groups(make_items(("test_a", "TestOne", "test_x")), {"test_a::TestOne": 123.0})
    assert groups[0].seconds == 123.0


def test_longest_group_lands_on_its_own_shard():
    groups = [
        ShardGroup("slow", [], 100.0),
        ShardGroup("a", [], 10.0),
        ShardGroup("b", [], 10.0),
        ShardGroup("c", [], 10.0),
    ]
    shards = assign_groups_to_shards(groups, 2)
    loads = sorted(sum(group.seconds for group in shard) for shard in shards)
    assert loads == [30.0, 100.0]


def test_assignment_is_deterministic_for_equal_weights():
    groups = [ShardGroup(key, [], 10.0) for key in ("d", "a", "c", "b")]
    first = assign_groups_to_shards(groups, 3)
    second = assign_groups_to_shards(list(reversed(groups)), 3)
    assert [[g.key for g in shard] for shard in first] == [[g.key for g in shard] for shard in second]


def test_shards_partition_the_suite_without_splitting_classes():
    items = make_items(
        *[
            (f"test_mod{module}", f"TestClass{cls}", f"test_{index}")
            for module in range(5)
            for cls in range(3)
            for index in range(4)
        ]
    )
    num_shards = 4
    selected = [select_shard(items, shard_id, num_shards, {}) for shard_id in range(num_shards)]

    node_ids = [item.nodeid for shard in selected for item in shard]
    assert Counter(node_ids) == Counter(item.nodeid for item in items), "shards must partition the suite exactly"

    shards_per_group: Counter[str] = Counter()
    for shard in selected:
        for key in {f"{item.module.__name__}::{item.cls.__name__}" for item in shard}:
            shards_per_group[key] += 1
    assert all(count == 1 for count in shards_per_group.values()), "a test class must not span shards"


def test_single_shard_selects_everything():
    items = make_items(("test_a", "TestOne", "test_x"), ("test_b", "TestTwo", "test_y"))
    assert select_shard(items, 0, 1, {}) == items
