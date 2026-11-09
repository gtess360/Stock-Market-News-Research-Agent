# External APIs and Data Contracts

## Provider evaluation (Phase 3 prerequisite)
Select licensed financial news and price providers after comparing: historical news access, ticker coverage, publication timestamps, attribution/redistribution terms, rate limits, reliability, price, and developer keys. Candidate providers may include Finnhub, Polygon/Massive, Alpha Vantage, or other appropriate services; verify current terms before selection.

## Canonical news item
article_id; ticker_symbols; headline; publisher; source_url; published_at_utc; retrieved_at_utc; summary_if_licensed; content_availability; language; syndication_group; evidence_flags.

## Canonical price bar
symbol; timestamp_utc; exchange_timezone; open; high; low; close; volume; adjusted_flag; provider; delayed_flag; retrieved_at_utc.

## API behavior
Use server-held credentials, HTTPS, request timeout, retry with exponential backoff for transient failures, circuit breaker, cache keyed by ticker/date/provider, and per-user/per-provider throttles. Preserve license-required attribution. Do not assume free tiers support 90-day historical news. If unavailable, clearly state coverage limitations rather than fabricate results.

## Historical integrity
Use original publication time, not scrape/retrieval time, for historical windows. Price series aligned to market calendar and trading sessions; weekends and holidays treated explicitly. For backtesting, exclude any information published after the evaluated as-of timestamp.
