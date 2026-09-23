"""Thin wrapper so the subprocess helper uses the real main() with the fake htcondor2.

The subprocess spawned by _HTCondorSubprocessClient runs ``python -m htcondor_helper``.
Because LIVE_FAKE_MODULE_PATH is prepended to PYTHONPATH the real main() resolves
``import htcondor2`` to the fake stub — no code duplication needed.
"""

from galaxy.jobs.runners.htcondor_helper import main

if __name__ == "__main__":
    raise SystemExit(main())
