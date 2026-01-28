import logging
from time import perf_counter

log = logging.getLogger("strategy")

def run_step(label, fn):
    t0 = perf_counter()
    fn()
    dt = perf_counter() - t0

    safe_label = label.encode("ascii", errors="ignore").decode()
    log.debug("%s %.3fs", safe_label, dt)