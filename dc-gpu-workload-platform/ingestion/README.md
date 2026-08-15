# ingestion/

- `downloader/` — one-time fetch of the Alibaba GPU trace source files.
- `replay_producer/` — reads the trace in timestamp order and emits it at a
  controlled pace into Kinesis / a scheduled Lambda, simulating a live
  telemetry feed instead of a one-shot batch load.
