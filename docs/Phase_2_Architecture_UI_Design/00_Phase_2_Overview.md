# Phase 2 — Architecture & UI Design
Status: Proposed for user approval. Version 1.0. Date: 2026-11-07.

## Goal
Translate approved Phase 1 requirements into an implementable, testable design. Antigravity generates code only after Phase 2 approval.

## Design decisions
- Python, Streamlit, LangGraph, OpenAI API, SQLite for initial deployment; Plotly for charts.
- Single research orchestrator with explicit tools and deterministic validation steps; not a needless collection of autonomous agents.
- Two tabs: Stock News and Sentiment Research; shared stock selection and historical research window.
- Forward outlook horizon (1, 7, 30, 90 days) belongs only to Sentiment Research.
- Three successful free research jobs per authenticated user; valid admin-issued token enables unlimited jobs while active, subject to abuse/rate controls.
- Data provider choice remains conditional on cost, historical availability, licensing, and reliability.

## Documents
See numbered files in this folder. Review the open decisions in 11_Phase_2_Approval.md before Phase 3.
