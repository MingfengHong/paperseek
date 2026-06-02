# Source Routing Reference

Use this reference when deciding which PaperSeek data source to use for a user request.

## Source Map

| Source | Use for | Strengths | Limits |
| --- | --- | --- | --- |
| OpenAlex | Default natural-language literature discovery | Broad coverage, abstracts when available, citation counts, reference and citing-work traversal | API key recommended; metadata quality varies by work |
| Crossref | DOI and publisher bibliographic metadata | DOI/title/venue/year verification, publisher metadata, broad registry | Abstracts often absent; not ideal as the only semantic recall source |
| Web of Science Starter | Institution-backed WoS metadata when key and entitlement exist | Curated citation index metadata and citation counts | Key required; UI marks temporarily unavailable; native abstracts should not be assumed |

## Default Choice

Use OpenAlex by default for open-ended literature search:

```bash
paperseek search "open innovation and digital platforms" --source openalex --output json
```

Use Crossref when:

- the task is DOI/title/metadata verification;
- OpenAlex metadata is sparse;
- the user explicitly asks for Crossref;
- you need a registry-oriented secondary check.

Use WoS only when:

- the user has configured `WOS_API_KEY`;
- the task explicitly requires WoS Starter;
- Clarivate API availability has been checked.

## Citation Expansion

Citation expansion is OpenAlex-only. It can add forward and backward citation neighbors from high-scoring seed papers, then rerank the expanded candidate pool.

Use it when:

- user wants related work discovery;
- the first query is likely to miss classic or neighboring papers;
- citation graph exploration is useful.

Avoid or disable it when:

- the user wants a small, fast smoke test;
- rate limits are a concern;
- source is Crossref or WoS.

CLI flag:

```bash
paperseek search "QUERY" --source openalex --no-expand-citations
```

## Query Guidance

- Natural-language questions may be Chinese or English; PaperSeek asks the LLM to generate source-appropriate search queries.
- For Chinese user questions, preserve the original question but expect English scholarly query terms.
- Prefer concise research questions over very long pasted text.
- Use `--field` only when the user has a clear discipline constraint; it can over-narrow results.
- If results are weak, rerun with a shorter question, fewer concepts, or broader terms.

## Result Interpretation

PaperSeek ranks returned candidates with LLM relevance scoring. Treat this as a screening signal, not as evidence that the paper is high quality.

When reporting results, include:

- final query;
- data source;
- number of iterations;
- total returned count;
- top paper titles, authors, venue, year, DOI or URL when available;
- relevance score and reason.

Do not fabricate missing abstracts, DOI, citation counts, or authors.
