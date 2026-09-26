from galaxy.job_metrics.instrumenters.cpuinfo import CpuInfoPlugin

CPUINFO_PRODUCTION_EXAMPLE_2201 = """processor   : 0
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 0
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 0
initial apicid  : 0
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 1
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 1
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 1
initial apicid  : 1
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 2
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 2
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 2
initial apicid  : 2
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 3
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 3
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 3
initial apicid  : 3
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 4
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 4
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 4
initial apicid  : 4
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 5
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 5
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 5
initial apicid  : 5
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 6
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 6
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 6
initial apicid  : 6
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 7
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 7
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 7
initial apicid  : 7
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 8
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 8
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 8
initial apicid  : 8
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
processor   : 9
vendor_id   : GenuineIntel
cpu family  : 6
model       : 63
model name  : Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz
stepping    : 2
microcode   : 0x1
cpu MHz     : 2494.222
cache size  : 16384 KB
physical id : 9
siblings    : 1
core id     : 0
cpu cores   : 1
apicid      : 9
initial apicid  : 9
fpu     : yes
fpu_exception   : yes
cpuid level : 13
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology eagerfpu pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear spec_ctrl intel_stibp
bogomips    : 4988.44
clflush size    : 64
cache_alignment : 64
address sizes   : 46 bits physical, 48 bits virtual
power management:
"""


def test_cpuinfo_collection(tmpdir):
    plugin = CpuInfoPlugin()
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert properties["processor_count"] == 10


# Two processors with differing "model name" values, for the unique-dedup
# fallback case. Trimmed to just the fields the tests care about.
CPUINFO_HETEROGENEOUS_EXAMPLE = """processor   : 0
model name  : Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz
bugs        : spectre_v1 spectre_v2
processor   : 1
model name  : Intel(R) Xeon(R) Gold 6242R CPU @ 3.10GHz
bugs        : spectre_v1 spectre_v2
"""


def test_cpuinfo_verbose_collection(tmpdir):
    """Verbose mode must actually store per-processor properties."""
    plugin = CpuInfoPlugin(verbose=True)
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert properties["processor_count"] == 10
    assert properties["processor_0_model name"] == "intel(r) xeon(r) cpu e5-2680 v3 @ 2.50ghz"
    assert properties["processor_9_model name"] == "intel(r) xeon(r) cpu e5-2680 v3 @ 2.50ghz"
    assert properties["processor_0_vendor_id"] == "genuineintel"


def test_cpuinfo_verbose_fields_filter(tmpdir):
    """`fields` restricts verbose output to the named /proc/cpuinfo fields only."""
    plugin = CpuInfoPlugin(verbose=True, fields="model name,cpu MHz")
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert properties["processor_0_model name"] == "intel(r) xeon(r) cpu e5-2680 v3 @ 2.50ghz"
    assert properties["processor_0_cpu mhz"] == "2494.222"
    assert "processor_0_vendor_id" not in properties
    assert "processor_0_bogomips" not in properties


def test_cpuinfo_verbose_unique_collapses_identical_values(tmpdir):
    """`unique` collapses a field to one key when every processor agrees."""
    plugin = CpuInfoPlugin(verbose=True, fields="model name", unique=True)
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_PRODUCTION_EXAMPLE_2201)
    properties = plugin.job_properties(1, job_dir)
    assert properties["model name"] == "intel(r) xeon(r) cpu e5-2680 v3 @ 2.50ghz"
    assert properties["processor_count"] == 10
    assert "processor_0_model name" not in properties
    assert "processor_9_model name" not in properties


def test_cpuinfo_verbose_unique_keeps_heterogeneous_values_per_processor(tmpdir):
    """`unique` falls back to per-processor keys for a field where processors disagree."""
    plugin = CpuInfoPlugin(verbose=True, fields="model name,bugs", unique=True)
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_HETEROGENEOUS_EXAMPLE)
    properties = plugin.job_properties(1, job_dir)
    assert "model name" not in properties
    assert properties["processor_0_model name"] == "intel(r) xeon(r) gold 6248r cpu @ 3.00ghz"
    assert properties["processor_1_model name"] == "intel(r) xeon(r) gold 6242r cpu @ 3.10ghz"
    assert properties["bugs"] == "spectre_v1 spectre_v2"


# Two processors where processor 1 does not report "bugs" at all (as opposed
# to reporting a different value). unique must not collapse a field that
# not every processor actually reported.
CPUINFO_MISSING_FIELD_EXAMPLE = """processor   : 0
model name  : Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz
bugs        : spectre_v1 spectre_v2
processor   : 1
model name  : Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz
"""


def test_cpuinfo_verbose_unique_keeps_per_processor_key_when_field_missing_on_some_processors(tmpdir):
    """`unique` must not collapse a field that only some processors reported at all."""
    plugin = CpuInfoPlugin(verbose=True, fields="model name,bugs", unique=True)
    job_dir = tmpdir.mkdir("job")
    job_dir.join("__instrument_cpuinfo_cpuinfo").write(CPUINFO_MISSING_FIELD_EXAMPLE)
    properties = plugin.job_properties(1, job_dir)
    assert properties["model name"] == "intel(r) xeon(r) gold 6248r cpu @ 3.00ghz"
    assert "bugs" not in properties
    assert properties["processor_0_bugs"] == "spectre_v1 spectre_v2"
    assert "processor_1_bugs" not in properties
