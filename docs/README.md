# ClassWire Documentation

The root README is intentionally compact. This directory contains the implementation details, design decisions, measured baselines, operational behavior, and quality guarantees behind the completed ClassWire system.

## Documentation map

| Area | Document | Focus |
| --- | --- | --- |
| System design | [Architecture](architecture/README.md) | Component boundaries, request flow, security, and repository organization |
| Source ingestion | [Data pipeline](data-pipeline/README.md) | Gmail selection, parser strategy, normalization, storage, caching, and deletion |
| Query behavior | [Search engine](search-engine/README.md) | Entity recognition, query plans, filters, custom schedules, availability, and conflicts |
| Optional NLU | [Training pipeline](../ml/query_understanding/README.md) | Labeled data, Kaggle training, evaluation, ONNX export, and rollout gates |
| Speed and cost | [Performance](performance/README.md) | Startup, browser loading, query caching, database operations, rendering, and payload size |
| Product UI | [Interface](interface/README.md) | Search composer, timetable views, feedback, mobile behavior, accessibility, and metadata |
| Production behavior | [Operations](operations/README.md) | Deployment, scheduled jobs, telemetry, failure recovery, and current boundaries |
| Verification | [Quality suite](quality/README.md) | Unit, integration, acceptance, frontend, coverage, and CI policy |

## Documentation principles

- Describe the completed system, not a tutorial for cloning it.
- Record why an engineering decision exists, not only what file contains it.
- Separate measured local baselines from provider-controlled production behavior.
- Keep security-sensitive values, credentials, user queries, and timetable contents out of examples and logs.
- Update metrics and test counts only after rerunning the corresponding verification.

## Project state

ClassWire is complete and in maintenance mode. Further changes are expected to address security, external API compatibility, timetable-format changes, or clearly bounded product refinements rather than unfinished core scope.

ClassWire remains an independent student project and is not an official SZABIST service.
