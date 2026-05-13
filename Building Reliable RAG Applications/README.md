# Building Reliable RAG Applications — Production RAG Notes

Concise reference notes from the O'Reilly workshop by **Sarang Sanjay Kulkarni** focused on moving RAG systems from simple demos to reliable production systems.

---

# What This Course Is Really About

Most RAG tutorials stop at:

```text
User Query
   ↓
Vector Search
   ↓
LLM Answer
```

That works for demos.

But production systems fail because of:

- Hallucinations
- Irrelevant retrieval
- Poor chunking
- Weak parsing
- Context overload
- No evaluation
- No observability

This course focuses on fixing those problems.

---

# Core Idea

> Production RAG is mostly a retrieval engineering problem — not just an LLM problem.

Better retrieval usually improves systems more than:
- Bigger models
- Better prompts
- More tokens

---

# Production RAG Pipeline

```text
Raw Documents
    ↓
Parsing
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Database
    ↓
Hybrid Retrieval
    ↓
Reranking
    ↓
Context Engineering
    ↓
LLM Generation
    ↓
Evaluation + Observability
```

---

# 1. Parsing (Most Underrated Step)

## Goal
Convert PDFs/docs into clean structured text.

## Tools
- Unstructured
- PDFMiner
- LlamaParse

## Why It Matters

Bad parsing causes:
- broken tables
- missing headers
- lost metadata
- corrupted retrieval

### Important Insight

```text
Bad parser → bad chunks → bad retrieval → hallucinated answers
```

Garbage in = garbage out.

---

# 2. Chunking

# Naive Chunking

```text
Fixed-size text splits
```

Problems:
- breaks meaning
- weak retrieval quality
- context fragmentation

---

# Better Approach → Semantic Chunking

Split based on:
- topic
- meaning
- structure

Benefits:
- stronger embeddings
- better retrieval precision
- cleaner context

---

# Small-to-Big Retrieval

One of the most useful concepts.

## Strategy

Store:
```text
small chunks
```

Retrieve:
```text
small precise matches
```

Send to LLM:
```text
larger parent context
```

This improves:
- retrieval precision
- answer quality
- grounding

---

# 3. Retrieval (Most Important Layer)

# Problem with Naive Retrieval

Simple cosine similarity often retrieves:
- noisy context
- semantically similar but wrong docs
- incomplete information

---

# Hybrid Search (Recommended)

Combine:

## Semantic Search
Good for:
- meaning
- intent
- paraphrasing

AND

## BM25 Keyword Search
Good for:
- exact terms
- IDs
- medical terminology
- error codes

---

# Why Hybrid Search Wins

Semantic search alone struggles with:
- numbers
- exact phrases
- technical keywords

Keyword search alone struggles with:
- intent
- reworded queries

Hybrid combines both strengths.

---

# Query Expansion

Instead of using one query:

```text
"How does insulin resistance affect liver metabolism?"
```

Generate multiple related queries:

```text
hepatic metabolism in diabetes
fatty liver insulin pathway
glucose regulation liver dysfunction
```

Benefits:
- broader retrieval coverage
- higher recall
- fewer missed documents

---

# Metadata Filtering

Attach metadata to chunks:

```json
{
  "department": "cardiology",
  "year": 2025,
  "document_type": "clinical_note"
}
```

Enables:
- scoped retrieval
- better precision
- faster searches

Critical for enterprise RAG.

---

# 4. Reranking (Huge Improvement)

# Retrieval Alone Is Not Enough

Retriever may return:
```text
Top 20 "possibly relevant" chunks
```

But only:
```text
Top 3–5 are actually useful
```

---

# Cross-Encoder Rerankers

Pipeline:

```text
Retriever → Top 50
Reranker → Best 5
LLM → Final Answer
```

Benefits:
- removes noisy chunks
- improves faithfulness
- reduces hallucinations

One of the highest ROI improvements in RAG.

---

# 5. Context Engineering

# Bigger Context != Better Answers

Too much context creates:
- distraction
- dilution
- hallucinations

Goal:
```text
Maximum signal density
```

---

# Lost in the Middle Problem

LLMs remember:
- beginning
- ending

Worst attention:
- middle sections

So:
- place critical info early
- compress redundant context
- prioritize high-value chunks

---

# 6. Agentic RAG

Traditional RAG:

```text
Retrieve → Generate
```

Agentic RAG:

```text
Reason → Retrieve → Evaluate → Retry → Generate
```

The system becomes iterative.

---

# ReAct Pattern

Core loop:

```text
Thought → Action → Observation
```

Example:

```text
Thought:
Need more evidence

Action:
Search vector DB

Observation:
Found relevant guideline

Thought:
Enough context available
```

---

# Self-RAG

The model evaluates:
```text
"Did I retrieve enough information?"
```

If not:
- rewrite query
- search again
- validate context

This creates self-correcting retrieval loops.

---

# Planning Agents

Break complex tasks into steps.

Example:

```text
Compare diabetes treatment guidelines
```

Agent plan:

```text
1. Retrieve ADA guidelines
2. Retrieve WHO guidelines
3. Extract treatments
4. Compare differences
5. Generate synthesis
```

Useful for:
- research systems
- enterprise workflows
- multi-hop reasoning

---

# 7. Evaluation (Critical)

# The RAG Triad

Production systems need measurable evaluation.

---

## 1. Context Precision

Question:
```text
Was retrieved context actually relevant?
```

Measures retrieval quality.

---

## 2. Faithfulness

Question:
```text
Did the answer come strictly from the context?
```

Measures hallucination risk.

Most important production metric.

---

## 3. Answer Relevancy

Question:
```text
Did the response answer the user's question directly?
```

Measures usefulness.

---

# RAGAS

Framework used for:
- automated evaluation
- benchmarking
- regression testing

Evaluates:
- faithfulness
- relevance
- retrieval quality

---

# 8. Observability

# Why It Matters

Without tracing:
- failures are invisible
- hallucination source unknown
- retrieval issues hard to debug

---

# Arize Phoenix

Used for:
- tracing agents
- inspecting prompts
- debugging retrieval
- monitoring pipelines

Track:
- retrieved chunks
- token usage
- query rewrites
- tool calls
- agent decisions

---

# Most Valuable Production Lessons

# 1. Retrieval Quality > Model Size

A smaller model with:
- better retrieval
- reranking
- clean context

often beats:
- larger models with weak retrieval

---

# 2. Better Parsing Improves Everything

Most RAG failures start at ingestion.

---

# 3. Reranking Is Extremely Valuable

One of the easiest high-impact improvements.

---

# 4. More Context Often Hurts

Prioritize:
```text
precision > quantity
```

---

# 5. Evaluation Is Mandatory

If you cannot measure:
- faithfulness
- retrieval quality
- relevance

then your RAG system is not production-ready.

---

# Recommended Stack

| Layer | Recommended Tools |
|---|---|
| Parsing | Unstructured, LlamaParse |
| Embeddings | OpenAI, BGE |
| Vector DB | Qdrant, Pinecone |
| Orchestration | LangChain, LangGraph |
| Agents | LangGraph |
| Evaluation | RAGAS |
| Observability | Arize Phoenix |

---

# Recommended Production Architecture

```text
Documents
   ↓
Parser
   ↓
Semantic Chunking
   ↓
Embeddings
   ↓
Vector DB
   ↓
Hybrid Retrieval
   ↓
Reranker
   ↓
Context Compression
   ↓
LLM
   ↓
Evaluation + Observability
```

---

# Workshop Resources

## Workshop Repository
https://github.com/Sarangk90/building-rag-app-workshop

## Advanced RAG Examples
https://github.com/Sarangk90/building-rag-app-workshop/tree/main/advanced-rag

## Course Slides
https://on24static.akamaized.net/event/52/24/85/0/rt/1/documents/resourceList1773343826400/buildingreliableragapplications1770221682484.pdf

---

# Setup

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone Repository

```bash
git clone https://github.com/Sarangk90/building-rag-app-workshop.git

cd building-rag-app-workshop
```

## Install Dependencies

```bash
uv sync
```

## Launch Jupyter

```bash
uv run jupyter lab
```

---

# Final Mental Model

Think of production RAG as:

```text
Search Engine
+
Reasoning Engine
+
Evaluation System
+
Observability Platform
```

NOT just:
```text
LLM + Vector Database
```
