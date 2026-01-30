# Test Run Commands

Use these commands from the repo root. The server **must already be running** at `http://127.0.0.1:5321`.

## R1: Latency Sensitivity
Sweep (fixed intervals):
```
python3 -m app.testing.entries.r1_latency --atc 5 --pilots 20 --duration 60 --interval 1 --sweep
```

Single run:
```
python3 -m app.testing.entries.r1_latency --atc 5 --pilots 20 --duration 60 --interval 1
```

## R2: Correctness / State Consistency
```
python3 -m app.testing.entries.r2_correctness --atc 5 --pilots 20 --duration 60 --interval 1 --min-cycles 3
```

## R3: Capacity Envelope
```
python3 -m app.testing.entries.r3_capacity --atc 1 --pilots 10 --duration 60 --interval 1
```

## R4: Overload Behavior
```
python3 -m app.testing.entries.r4_overload --atc 2 --pilots 40 --duration 60 --interval 1
```
