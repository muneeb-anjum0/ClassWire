# Performance and Optimization

ClassWire is optimized for the limits that dominate its workload: Render cold starts, Gmail round trips, repeated Firestore operations, large timetable payloads, browser startup, and broad-result rendering.

## Measured baselines

| Measurement | Current baseline |
| --- | ---: |
| Backend application import | Approximately **0.19 seconds** |
| Initial frontend JavaScript | **202.0 kB**, **64.4 kB gzip** |
| Previous initial JavaScript | **300.9 kB**, **96.7 kB gzip** |
| Initial schedule render window | **60 rows** |
| Semantic search planning | **1.17 ms mean**, **2.73 ms p95** across 2,000 warm local fixture queries |
| Backend test coverage | **64.2% branch-aware** |
| Frontend line coverage | **73.8%** |

These figures were measured locally. The semantic-search measurement used four representative query families against a 40-row synthetic acceptance fixture after warm-up. They are useful regression baselines, not claims about public-network speed, Google API latency, Firestore latency, or hosting-platform wake time.

## Backend startup

Heavy integrations are lazy. Importing the Flask application does not immediately construct Firebase, Firestore, Gmail, or parser services. The first endpoint that needs a service initializes it behind a thread-safe boundary.

The health endpoint is deliberately Flask-only. It does not contact Gmail or Firestore, so Render can detect an open and ready web process as soon as the application is serving requests.

Gunicorn binds to Render's assigned `PORT` through both the process command and the automatically discovered configuration. Startup and crash logs are streamed, lightweight requests can use threads, and worker temporary files use shared memory.

## Browser startup

- The production API origin is known immediately, avoiding a blocking discovery health check.
- DNS prefetch and preconnect start connection setup while the static shell loads.
- An early non-blocking request begins waking the free Render instance.
- One authenticated bootstrap replaces separate session, configuration, and timetable calls.
- Logged-out bootstrap returns an explicit guest state instead of a noisy authorization failure.
- Production API traffic is reverse-proxied through the Vercel origin so signed cookies remain first-party in private browsing.
- Bootstrap returns identity and the latest timetable without reading obsolete filtering configuration.
- Login, legal pages, and the authenticated dashboard load as separate route chunks.
- Native Fetch replaced a general-purpose HTTP dependency while retaining cookies, timeout behavior, and typed errors.

Render free-tier suspension can still add provider-controlled delay. Application work has been minimized, but a sleeping machine cannot be made equivalent to an always-on paid instance.

## Search path

```text
React state
  -> repeated-query process cache
  -> normalized source memory cache
  -> compressed Firestore source
  -> Gmail refresh only when required
```

Normal searches operate on already-normalized rows and do not call Gmail. Repeating the same query against the same source uses a parser-versioned result cache. User and source identity are part of the cache boundary.

### Optional semantic inference

The optional query-understanding model is designed around the free backend's memory and CPU limits:

- four compact TinyBERT layers and one shared encoder for intent and entity prediction;
- dynamic INT8 ONNX weights instead of a PyTorch production runtime;
- lazy artifact loading, so startup and deterministic searches do not pay model initialization cost;
- one ONNX intra-operation thread and one inter-operation thread;
- a maximum 96-token query window;
- an artifact gate of 30 MB and a warm CPU p95 gate of 50 ms.

Those limits are pipeline acceptance targets, not measured production claims. The Kaggle notebook writes the actual size, load time, memory watermark, mean latency, p50, p95, p99, intent accuracy, exact-span entity F1, and joint exact match to machine-readable reports. The standard backend dependency set remains unchanged until an exported artifact passes those gates.

## Gmail efficiency

- Latest message metadata is batched across weekdays.
- Weekday message IDs allow unchanged parsed rows to be reused.
- Only changed weekday bodies are downloaded.
- Failed batch parts are retried without repeating successful parts.
- An older latest weekday remains valid when other weekdays have newer messages.
- Concurrent refresh requests for one user collapse behind one lock.

## Firestore efficiency

| Optimization | Effect |
| --- | --- |
| Direct per-user document IDs | No composite index requirement on interactive paths |
| Bounded TTL caches | Warm token, settings, timetable, source, identity, and health reads avoid Firestore |
| Stable content hashes | Unchanged timetable and source documents are not rewritten |
| Gzip-compressed JSON | Repeated keys and labels occupy less document and transfer space |
| Compressed-size guard | Oversized data fails before an unsafe Firestore write |
| Source/result separation | Durable source stays server-side while ordinary search answers avoid database writes |
| Stale-source cache ordering | Fallback reuses the already decoded document rather than reading it twice |

## Browser persistence

Large authenticated results are stored in IndexedDB rather than synchronous `localStorage`. The connection is reused, existing local entries migrate forward, and an unavailable IndexedDB implementation falls back without breaking the application.

React state keeps the current answer visible while a tab remains open. Failed background refreshes do not replace it with an empty state. Request ordering prevents a late older response from overwriting a newer search.

## Rendering

- Broad results render an initial 60-row window and expand in 60-row increments.
- Desktop and mobile layouts share the same normalized data and deterministic sorting.
- Day rows use content visibility hints for off-screen work.
- Result restoration avoids reparsing or refetching merely to repaint the last answer.
- Semester color assignment uses generated hues rather than a fixed palette.
- Static legal and login code does not inflate the authenticated dashboard entry chunk.

## Payload handling

Large JSON responses are gzip-compressed only when the browser supports compression and the result becomes smaller. Small payloads avoid compression overhead. Authenticated API responses use no-store HTTP semantics because restoration belongs to the controlled per-user browser cache, not a shared cache.

## Optimization ledger

| Constraint | Implemented response |
| --- | --- |
| Eager backend dependency initialization | Lazy request-time service construction |
| Health checks waking cloud dependencies | Constant-time application health route |
| Multiple dashboard startup requests | Consolidated bootstrap endpoint |
| Production API discovery round trip | Immediate known-origin selection and early wake |
| Incognito blocking cross-site session cookies | Same-origin API proxy plus single-use OAuth handoff |
| Synchronous large-result storage | IndexedDB with connection reuse |
| Every refresh reparsing every day | Per-weekday message IDs and incremental fetch |
| Gmail throttling and transient failure | Timeouts, bounded backoff, jitter, and partial retry |
| Search reaching Gmail repeatedly | Durable normalized source separated from displayed result |
| Identical search recomputation | Bounded parser-versioned result cache |
| Search-time Firestore writes | Browser result persistence and server-side source persistence |
| Repeated document reads | Service-specific memory TTL caches |
| Identical document writes | Stable hashes excluding volatile timestamps |
| Large Firestore payloads | Compact JSON plus gzip bytes |
| Hundreds of immediate DOM rows | Progressive render windows |
| One large frontend bundle | Route-level lazy loading and dependency removal |
| Race-prone asynchronous updates | Sequence guards, in-flight guards, and refresh locks |

## Remaining boundary

The current render window materially limits work for normal schedules. True viewport virtualization could reduce DOM work further for thousands of visible rows, but it would add complexity that the current SZABIST timetable volume does not justify.

[Back to documentation index](../README.md)
