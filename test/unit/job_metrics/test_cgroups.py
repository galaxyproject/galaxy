from galaxy.job_metrics.instrumenters.cgroup import CgroupPlugin

CGROUPV1_PRODUCTION_EXAMPLE_2201 = """__cpu.cfs_period_us__
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

CGROUPV2_PRODUCTION_EXAMPLE_232 = """__cpu.idle__
0
__cpu.max__
max 100000
__cpu.max.burst__
0
__cpu.stat__
usage_usec 8992210
user_usec 6139150
system_usec 2853059
core_sched.force_idle_usec 0
nr_periods 0
nr_throttled 0
throttled_usec 0
nr_bursts 0
burst_usec 0
__cpu.weight__
100
__cpu.weight.nice__
0
__memory.current__
139350016
__memory.events__
low 0
high 0
max 0
oom 0
oom_kill 0
oom_group_kill 0
__memory.events.local__
low 0
high 0
max 0
oom 0
oom_kill 0
oom_group_kill 0
__memory.high__
max
__memory.low__
0
__memory.max__
max
__memory.min__
0
__memory.numa_stat__
anon N0=864256
file N0=129146880
kernel_stack N0=32768
pagetables N0=131072
sec_pagetables N0=0
shmem N0=0
file_mapped N0=0
file_dirty N0=0
file_writeback N0=0
swapcached N0=0
anon_thp N0=0
file_thp N0=0
shmem_thp N0=0
inactive_anon N0=819200
active_anon N0=20480
inactive_file N0=51507200
active_file N0=77639680
unevictable N0=0
slab_reclaimable N0=8638552
slab_unreclaimable N0=340136
workingset_refault_anon N0=0
workingset_refault_file N0=77
workingset_activate_anon N0=0
workingset_activate_file N0=0
workingset_restore_anon N0=0
workingset_restore_file N0=0
workingset_nodereclaim N0=0
__memory.oom.group__
0
__memory.peak__
339906560
__memory.reclaim__
__memory.stat__
anon 860160
file 129146880
kernel 9211904
kernel_stack 32768
pagetables 126976
sec_pagetables 0
percpu 0
sock 0
vmalloc 0
shmem 0
zswap 0
zswapped 0
file_mapped 0
file_dirty 0
file_writeback 0
swapcached 0
anon_thp 0
file_thp 0
shmem_thp 0
inactive_anon 815104
active_anon 20480
inactive_file 51507200
active_file 77639680
unevictable 0
slab_reclaimable 8642480
slab_unreclaimable 340904
slab 8983384
workingset_refault_anon 0
workingset_refault_file 77
workingset_activate_anon 0
workingset_activate_file 0
workingset_restore_anon 0
workingset_restore_file 0
workingset_nodereclaim 0
pgscan 0
pgsteal 0
pgscan_kswapd 0
pgscan_direct 0
pgsteal_kswapd 0
pgsteal_direct 0
pgfault 132306
pgmajfault 524
pgrefill 0
pgactivate 18958
pgdeactivate 0
pglazyfree 0
pglazyfreed 0
zswpin 0
zswpout 0
thp_fault_alloc 19
thp_collapse_alloc 0
__memory.swap.current__
0
__memory.swap.events__
high 0
max 0
fail 0
__memory.swap.high__
max
__memory.swap.max__
max
__memory.zswap.current__
0
__memory.zswap.max__
max
"""


def test_cgroupv1_collection(tmpdir):
    plugin = CgroupPlugin()
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cgroup__metrics").write(CGROUPV1_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert "cpuacct.usage" in properties
    assert properties["cpuacct.usage"] == 7265342042
    assert "memory.limit_in_bytes" in properties
    assert properties["memory.limit_in_bytes"] == 9223372036854771712


def test_cgroupv2_collection(tmpdir):
    plugin = CgroupPlugin()
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cgroup__metrics").write(CGROUPV2_PRODUCTION_EXAMPLE_232)
    properties = plugin.job_properties(1, job_dir)
    assert "cpu.stat.usage_usec" in properties
    assert properties["cpu.stat.usage_usec"] == 8992210
    assert "memory.peak" in properties
    assert properties["memory.peak"] == 339906560


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
