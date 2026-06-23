import json
import sys
import threading
from typing import Any


def _locate_schedd(
    htcondor,
    schedd_cache: dict,
    schedd_lock: threading.Lock,
    collector: str | None,
    schedd_name: str | None,
):
    cache_key = (collector, schedd_name)
    with schedd_lock:
        cached = schedd_cache.get(cache_key)
    if cached:
        return cached

    # Collector lookup may be slow (network I/O) — do it outside the lock.
    if not collector and not schedd_name:
        schedd = htcondor.Schedd()
    else:
        collector_obj = htcondor.Collector(pool=collector) if collector else htcondor.Collector()
        if schedd_name:
            schedd_ad = collector_obj.locate(htcondor.DaemonType.Schedd, name=schedd_name)
        else:
            schedd_ads = collector_obj.locateAll(htcondor.DaemonType.Schedd)
            schedd_ad = schedd_ads[0] if schedd_ads else None
        if not schedd_ad:
            location = f"collector={collector}" if collector else "local collector"
            raise RuntimeError(f"Unable to locate schedd via {location} (schedd={schedd_name or 'first'})")
        schedd = htcondor.Schedd(schedd_ad)

    # Use setdefault so that if a concurrent caller already inserted this key
    # while we were outside the lock, their entry wins and we discard ours.
    with schedd_lock:
        return schedd_cache.setdefault(cache_key, schedd)


def main() -> int:
    import htcondor2

    schedd_cache: dict[tuple[str | None, str | None], Any] = {}
    schedd_lock = threading.Lock()
    response: dict[str, object]

    for line in sys.stdin:
        try:
            request = json.loads(line)
            command = request["command"]
            if command == "shutdown":
                response = dict(ok=True)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                return 0

            collector = request.get("collector")
            schedd_name = request.get("schedd_name")
            schedd = _locate_schedd(htcondor2, schedd_cache, schedd_lock, collector, schedd_name)
            if command == "submit":
                submit_result = schedd.submit(htcondor2.Submit(request["submit_description"]))
                response = dict(ok=True, cluster=str(submit_result.cluster()))
            elif command == "remove":
                schedd.act(
                    htcondor2.JobAction.Remove,
                    request["job_spec"],
                    reason="Galaxy job stop request",
                )
                response = dict(ok=True)
            else:
                raise RuntimeError(f"Unknown HTCondor helper command: {command}")
        except Exception as exc:
            response = dict(ok=False, error=str(exc))

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
