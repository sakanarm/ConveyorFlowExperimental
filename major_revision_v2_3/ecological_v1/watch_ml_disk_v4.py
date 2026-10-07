"""No-provider disk guard for continuation 4; pauses before C: falls below 4 GiB."""
import argparse
import json

import continue_ml_calibration_v4 as continuation
import watch_ml_disk_v3 as guard


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-free-gib', type=float, default=4)
    parser.add_argument('--interval-seconds', type=int, default=60)
    parser.add_argument('--max-hours', type=float, default=36)
    args = parser.parse_args()
    continuation._route_v3_loop()
    print(json.dumps(guard.watch(args.min_free_gib, args.interval_seconds,
                                 args.max_hours)), flush=True)
