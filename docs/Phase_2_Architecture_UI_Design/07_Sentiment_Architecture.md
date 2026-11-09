# Sentiment Research Architecture

## Inputs
Selected tickers, historical evidence window, forward horizon (1/7/30/90 days), verified news articles, dated market prices, optionally scheduled corporate events.

## Outputs
Per-stock current news sentiment (positive/negative/neutral/mixed), forward-looking scenario outlook (bullish/bearish/neutral/mixed), evidence strength (strong/moderate/weak/insufficient), top catalysts, risks, opposing evidence, as-of timestamp, links, limitations.

## Method
1. Summarize article-level claims with evidence links.
2. Classify each article's sentiment with reason and source; label editorial vs factual reporting.
3. Deduplicate syndicated coverage so repeated articles do not count as independent corroboration.
4. Aggregate transparently by recency, relevance, and source diversity, not arbitrary numeric confidence.
5. Generate alternative future scenarios and identify what could change the outlook.
6. Verify citations and disclose missing/contradictory data.
7. Optionally evaluate historical outlooks using strict point-in-time datasets; report sample sizes and limitations.

## Guardrails
Do not state a guaranteed return or buy/sell instruction. Do not conflate positive news with future stock gains. No fabricated probabilities. Provide neutral/insufficient when evidence is weak.
