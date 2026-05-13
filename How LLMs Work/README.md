# How LLMs Work: Course Overview

This repository contains core materials and key takeaways from the **How LLMs Work** course. The goal is to demystify how word embeddings power generative AI models like ChatGPT, moving beyond the "black box" and into the mathematical foundations of modern AI.

---

## Core Concepts (The Crux)

Large Language Models (LLMs) translate human language into numbers through three critical stages:

| Stage | What Happens? | Result |
| :--- | :--- | :--- |
| **Tokenization** | Splitting text into smaller units (words or parts of words). | Raw text becomes "tokens." |
| **Embedding** | Mapping tokens into a high-dimensional mathematical space. | Tokens become "vectors" (lists of numbers). |
| **Language Modeling** | Using math (matrix multiplication) to predict the next token. | AI generates a coherent response. |

---

## Key Takeaways

* **Word Embeddings:** "You shall know a word by the company it keeps." Meaning is derived from context. Similar words (e.g., "dog" and "cat") are mathematically close.
* **The Power of Math:** Embeddings allow for "semantic math." Example: `King - Man + Woman = Queen`.
* **Temperature Settings:** Controls the "creativity" or randomness of the AI.
    * *Temperature 0:* Deterministic (picks the most likely word).
    * *Temperature 1+:* Creative (picks less likely words).
* **Transformers & Attention:** The "backbone" architecture that allows models to focus on specific parts of a sentence to understand relationships.

---

## Limitations to Remember

* **Hallucinations:** Models predict *probability*, not *truth*, which can lead to confident but false claims.
* **Bias:** Inherited from the vast internet data used for training (e.g., gender or occupational biases).

---

## Applications Beyond Chat

* **R.A.G. (Retrieval Augmented Generation):** Connecting a private database to an LLM to provide factual context.
* **Semantic Search:** Finding documents based on meaning rather than keywords.
* **Multi-modal Systems:** Linking text with images or sound through shared embedding spaces.

---

*Reference: Materials based on the course by Kate Harwood (New York Times R&D).*
