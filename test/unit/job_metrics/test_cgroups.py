from galaxy.job_metrics.instrumenters.cgroup import CgroupPlugin

CGROUP_PRODUCTION_EXAMPLE_2201 = """__cpu.cfs_period_us__
100000
__cpu.cfs_quota_us__
-1
__cpu.rt_period_us__
1000000
__cpu.rt_runtime_us__
0
__cpu.shares__
1024
__cpu.stat__
nr_periods 0
nr_throttled 0
throttled_time 0
__cpuacct.stat__
user 616
system 98
__cpuacct.usage__
7265342042
__cpuacct.usage_percpu__
0 7269963877 0 0 0 0 0 0 0 0
__memory.failcnt__
0
__memory.force_empty__
__memory.kmem.failcnt__
0
__memory.kmem.limit_in_bytes__
9223372036854771712
__memory.kmem.max_usage_in_bytes__
0
__memory.kmem.slabinfo__
__memory.kmem.tcp.failcnt__
0
__memory.kmem.tcp.limit_in_bytes__
9223372036854771712
__memory.kmem.tcp.max_usage_in_bytes__
0
__memory.kmem.tcp.usage_in_bytes__
0
__memory.kmem.usage_in_bytes__
0
__memory.limit_in_bytes__
9223372036854771712
__memory.max_usage_in_bytes__
264409088
__memory.memsw.failcnt__
0
__memory.memsw.limit_in_bytes__
9223372036854771712
__memory.memsw.max_usage_in_bytes__
264409088
__memory.memsw.usage_in_bytes__
103460864
__memory.move_charge_at_immigrate__
0
__memory.numa_stat__
total=25226 N0=25226
file=25071 N0=25071
anon=155 N0=155
unevictable=0 N0=0
__memory.oom_control__
oom_kill_disable 0
under_oom 0
__memory.pressure_level__
__memory.soft_limit_in_bytes__
9223372036854771712
__memory.stat__
cache 102690816
rss 655360
rss_huge 0
mapped_file 0
swap 0
pgpgin 136493
pgpgout 111262
pgfault 170611
pgmajfault 961
inactive_anon 0
active_anon 634880
inactive_file 101662720
active_file 1028096
unevictable 0
hierarchical_memory_limit 7853834240
hierarchical_memsw_limit 7853834240
total_cache 102690816
total_rss 655360
total_rss_huge 0
total_mapped_file 0
total_swap 0
total_pgpgin 136493
total_pgpgout 111262
total_pgfault 170611
total_pgmajfault 961
total_inactive_anon 0
total_active_anon 634880
total_inactive_file 101662720
total_active_file 1028096
total_unevictable 0
__memory.swappiness__
30
__memory.usage_in_bytes__
103391232
__memory.use_hierarchy__
1
"""


def test_cgroup_collection(tmpdir):
    plugin = CgroupPlugin()
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cgroup__metrics").write(CGROUP_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert "cpuacct.usage" in properties
    assert properties["cpuacct.usage"] == 7265342042
    assert "memory.limit_in_bytes" in properties
    assert properties["memory.limit_in_bytes"] == 9223372036854771712


def test_instrumentation(tmpdir):
    # don't actually run the instrumentation but at least exercise the code the and make
    # sure templating includes cgroup_mount override.
    mock_cgroup_mount = "/proc/sys/made/up/cgroup/mount"
    plugin = CgroupPlugin(
        cgroup_mount=mock_cgroup_mount,
    )
    assert plugin.pre_execute_instrument(tmpdir) is None
    collection_commands = plugin.post_execute_instrument(tmpdir)
    assert len(collection_commands) == 2
    cpu_command = collection_commands[0]
    assert mock_cgroup_mount in cpu_command
    memory_command = collection_commands[1]
    assert mock_cgroup_mount in memory_command
