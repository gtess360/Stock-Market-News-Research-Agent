# UI Design — Approved Decorative Direction

## Visual design
Professional financial dashboard: navy sidebar, blue/purple gradient header, light content panels, teal accents, rounded cards, restrained shadows, readable typography, icons, consistent spacing. Accessible contrast, keyboard navigation, responsive layout. All displayed mock data must be labeled as illustrative.

## Global layout
Sidebar: Dashboard, Research History, Saved Reports, Settings; Admin Console visible only to admins.
Header: product name, last updated timestamp, account and entitlement badge.
Shared filter bar: searchable multi-stock selection with removable chips; Today / 7D / 30D / 90D / Custom historical range; timezone and applied date range shown explicitly.
Two tabs: Stock News and Sentiment Research. Switching tabs preserves global filters, but results remain separate and keyed by filter state. Filters do not silently launch paid API calls.

## Stock News tab
Summary cards: selected stocks, article count, research window. Stock selector/list; dated article timeline; publisher, headline, source link, concise grounded summary, duplicate indicator; price and volume chart; compare stocks; generate/export report.

## Sentiment Research tab
Additional independent horizon selector: next 1, 7, 30, 90 days. Per-stock sentiment label (bullish/bearish/neutral/mixed), evidence strength, supporting and opposing evidence, catalysts, risks, scenario cards, side-by-side comparison, caveats. Distinguish news sentiment from forecast and label forecast timestamp.

## Entitlement states
Free badge: 3/2/1/0 remaining. After 0 show access modal with Enter Token and Request Token; active token badge: Unlimited Access. Expired/revoked token returns to entitlement check. Do not expose token in URL or logs.

## Loading and errors
Show per-stock progress and partial results, retryable provider failures, missing-data explanations, stale timestamps, and research cancellation where supported.
