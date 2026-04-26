# Test Run Commands

Use these commands from the repo root. The server must already be running at `http://127.0.0.1:5321`.

## Test Overview

The test suite covers four different questions:

- `R1` measures latency under a fixed, nominal load while varying the message interval.
- `R2` checks correctness and state consistency during a controlled multi-client run.
- `R3` explores capacity by increasing requested load and recording the latency of the traffic that was actually processed.
- `R4` stresses the system beyond expected capacity and compares requested client counts with observed admitted counts.

## R1: Latency Sensitivity

Purpose:
- Measure end-to-end latency and server-side processing latency under a small fixed load.
- Study how latency changes as message frequency increases.

What changes:
- The sweep varies `interval`.
- The default sweep uses `5` ATC clients, `20` pilot clients, and `60 s` duration.

What to read in the output:
- `end_to_end_ms.p50`: median end-to-end latency.
- `end_to_end_ms.p95`: 95th percentile end-to-end latency.
- `server_processing_ms.p50`: median server processing latency.
- `server_processing_ms.p95`: 95th percentile server processing latency.

Run a sweep:
```bash
python3 -m app.testing.entries.r1_latency --atc 5 --pilots 20 --duration 60 --interval 1 --sweep
```

Run a single point:
```bash
python3 -m app.testing.entries.r1_latency --atc 5 --pilots 20 --duration 60 --interval 1
```

## R2: Correctness / State Consistency

Purpose:
- Verify that the system reaches the requested client population.
- Verify that pilots can make progress through repeated request-response-action cycles.
- Verify that one pilot's activity does not leak into another pilot's state.
- Verify that server-side history/state growth remains bounded during the run.

Important terminology:
- `steady state`: a snapshot where observed counts match the requested counts for both pilots and ATC.
- `cycle`: one complete pilot interaction round with the system.
- `completed cycle`: one full pilot interaction that reaches `request -> ATC response -> action acknowledged`.
- `unexpected event`: a client-side event received in the wrong phase, such as an acknowledgement or response arriving when that pilot was not expecting it.
- `history length`: the amount of per-pilot/request history retained by the server, as exposed by `/testing/state`.

R2 pass checks:

- `Population integrity: PASS`
  Means the test reached steady state at least once.
  In code, at least one recorded snapshot must satisfy:
  `pilot_count == requested pilots` and `atc_count == requested ATC`.

- `Per-pilot isolation: PASS`
  Means no pilot client reported unexpected cross-talk or out-of-order events.
  In code, every pilot's `unexpected_events` list must be empty.

- `Progress guarantee: PASS`
  Means every pilot completed at least the configured minimum number of full cycles.
  In code, each pilot's `completed_cycles` must be greater than or equal to `--min-cycles`.

- `Bounded state growth: PASS`
  Means the observed history size behaves consistently and does not grow beyond the expected bound implied by completed work.
  In code, two conditions must hold:
  `1.` the recorded maximum history length is monotonic over the checked snapshots.
  `2.` the maximum history length does not exceed `max_completed_cycles * 3 + 1`.

- `validation_issues_empty: PASS`
  Means the server-reported `validation_issues` list was empty in the final merged state summary.

- `polled_issues_empty: PASS`
  Means the runner did not record polling/bootstrap/connect issues while collecting observations.

Interpretation:
- A passing `R2` run is evidence that the requested population was reached, pilots made progress, no per-pilot isolation anomalies were detected, and observed state growth stayed within the validator's bound.
- A failing `R2` run should be read by the specific failed checks, not only by the overall `PASS` or `FAIL`.

Run:
```bash
python3 -m app.testing.entries.r2_correctness --atc 5 --pilots 20 --duration 60 --interval 1 --min-cycles 3
```

## R3: Capacity Envelope

Purpose:
- Increase requested load and observe how latency behaves as scale rises.
- Identify how much load the environment can request before admission or activity starts to fall short.

Important interpretation note:
- `R3` records real latency for the messages that were actually processed.
- `R3` does not, by itself, guarantee that all requested clients were simultaneously connected and active for the full run.
- For strong claims about sustained population, compare requested counts with the observed counts in `state_summary`.

What to read in the output:
- Requested counts come from `params.atc` and `params.pilots`.
- Observed counts come from `result.state_summary.atc_count` and `result.state_summary.pilot_count`.
- Latency comes from the same `p50` and `p95` metrics used in `R1`.

Run:
```bash
python3 -m app.testing.entries.r3_capacity --atc 1 --pilots 10 --duration 60 --interval 1
```

## R4: Overload Behavior

Purpose:
- Push the system beyond normal capacity.
- Measure how many clients were requested versus how many were actually admitted or observed.
- Check whether overload causes errors, validation issues, or message corruption symptoms.

What to read in the output:
- `expected_counts`: requested pilots and ATC.
- `observed_counts`: highest observed pilots and ATC reported by the run summary.
- `total_errors` and `error_rate`: error volume during overload.
- `validation_issues` and `polled_issues`: anomalies seen by the server state or the runner.

Interpretation:
- `R4` is the right test for statements about overload admission shortfall.
- If requested counts are far above observed counts, the result shows overload rejection or connection shortfall, not sustained support for the requested population.

Run:
```bash
python3 -m app.testing.entries.r4_overload --atc 2 --pilots 40 --duration 60 --interval 1
```
