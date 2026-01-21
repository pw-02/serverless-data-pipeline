import json
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

REGION = "us-west-2"
FUNCTION_NAMES = [f"my-cache-test-{i:03d}" for i in range(200)]

N_MINUTES = 1
INTERVAL_SECONDS = N_MINUTES * 60

# Safety stop (set high, or None if you really want infinite)
MAX_ROUNDS = None  # e.g., 24 hours at 1-min interval

# Threads for parallel invokes
MAX_WORKERS = 64

lambda_client = boto3.client("lambda", region_name=REGION)

def setup_logger():
    logger = logging.getLogger("lambda_reclaim")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File
    logfile = f"lambda_reclaim_{int(time.time())}.log"
    fh = logging.FileHandler(logfile, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.info(f"Logging to file: {logfile}")
    return logger

def invoke_one(fname: str):
    resp = lambda_client.invoke(
        FunctionName=fname,
        InvocationType="RequestResponse",
        Payload=b"{}",
    )
    payload = json.loads(resp["Payload"].read().decode("utf-8"))
    return fname, payload

def main():
    logger = setup_logger()

    # Track first and current IDs per function
    first_id = {}     # fname -> first seen instance_id
    current_id = {}   # fname -> most recent instance_id
    reclaimed = set() # functions that have seen an instance_id change at least once

    total = len(FUNCTION_NAMES)

    round_num = 0
    while True:
        round_num += 1
        round_ts = datetime.utcnow().isoformat() + "Z"
        t0 = time.time()

        logger.info(f"=== Round {round_num} @ {round_ts} | reclaimed {len(reclaimed)}/{total} ===")

        errors = 0
        changed_this_round = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [ex.submit(invoke_one, fn) for fn in FUNCTION_NAMES]
            for fut in as_completed(futures):
                try:
                    fname, payload = fut.result()
                except Exception as e:
                    errors += 1
                    logger.warning(f"{fname if 'fname' in locals() else '?'} invoke failed: {e}")
                    continue

                iid = payload.get("instance_id")
                if not iid:
                    errors += 1
                    logger.warning(f"{fname} missing instance_id. payload={payload}")
                    continue

                if fname not in first_id:
                    first_id[fname] = iid
                    current_id[fname] = iid
                    logger.info(f"{fname}: FIRST instance_id={iid}")
                    continue

                prev = current_id.get(fname)
                if prev != iid:
                    # This indicates a different execution environment than last time.
                    current_id[fname] = iid
                    reclaimed.add(fname)
                    changed_this_round += 1
                    logger.info(f"{fname}: CHANGED prev={prev} new={iid}  (reclaimed {len(reclaimed)}/{total})")
                else:
                    logger.info(f"{fname}: same instance_id={iid}")

        # Stop condition: all have changed at least once
        if len(reclaimed) == total:
            logger.info(f"DONE: all {total} functions observed at least one reclaim (instance_id change).")
            break

        # Safety stop
        if MAX_ROUNDS is not None and round_num >= MAX_ROUNDS:
            logger.info(f"STOP: reached MAX_ROUNDS={MAX_ROUNDS}. reclaimed {len(reclaimed)}/{total}.")
            break

        # Sleep until next interval
        elapsed = time.time() - t0
        sleep_s = max(0, INTERVAL_SECONDS - elapsed)
        logger.info(f"Round summary: changed_this_round={changed_this_round} errors={errors} sleep={sleep_s:.1f}s")
        time.sleep(sleep_s)

if __name__ == "__main__":
    main()
