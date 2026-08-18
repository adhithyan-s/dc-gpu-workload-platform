# ingestion/

- `downloader/` - one-time fetch of the Alibaba GPU trace source files.
- `replay_producer/` - reads the trace in timestamp order and and writes it as timestamped micro-batches straight to S3 at a controlled pace, simulating a live telemetry feed instead of a one-shot batch load. See docs/architecture.md for why this doesn't use Kinesis.