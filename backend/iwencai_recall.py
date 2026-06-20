from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .db import DATA_DIR, configure_sqlite_connection, now_iso
from .providers.iwencai_profile import IWENCAI_PROFILE_DB_PATH, open_iwencai_readonly_db


IWENCAI_RECALL_DB_PATH = DATA_DIR / "iwencai_recall.db"
IWENCAI_QDRANT_LOCAL_PATH = DATA_DIR / "qdrant_iwencai_recall"
IWENCAI_BGE_MODELS_DIR = DATA_DIR / "models"
DEFAULT_BGE_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_QDRANT_COLLECTION_BASE = "iwencai_profile_chunks"
RECALL_SCHEMA_VERSION = "2026-06-20.3"
_QDRANT_CLIENT_CACHE: dict[tuple[str, str, str, float], Any] = {}
_BGE_EMBEDDER_CACHE: dict[str, "BgeEmbedder"] = {}

KEYWORD_WEIGHT = 0.60
EMBEDDING_WEIGHT = 0.35
EVIDENCE_WEIGHT = 0.05
DEFAULT_MIN_RERANK_SCORE = float(os.environ.get("IWENCAI_RECALL_MIN_SCORE", "0.42"))

TITLE_NGRAM_MAX_TERMS = 120
TEXT_NGRAM_MAX_TERMS = 180
QUERY_NGRAM_MAX_TERMS = 120

DOC_TYPE_LABELS = {
    "summary": "简介",
    "highlight": "看点",
    "event": "近期概念事件",
    "concept": "所属概念",
}

DOC_TYPE_EVIDENCE_WEIGHT = {
    "concept": 1.0,
    "event": 0.86,
    "highlight": 0.78,
    "summary": 0.68,
}

TERM_WEIGHTS = {
    "symbol": 2.0,
    "name": 2.0,
    "doc_title": 7.0,
    "concept_name": 10.0,
    "title_ngram": 4.2,
    "text_ngram": 1.15,
    "english_token": 1.8,
}


def get_iwencai_recall_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or IWENCAI_RECALL_DB_PATH).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    configure_sqlite_connection(conn)
    return conn


def init_iwencai_recall_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists iwencai_recall_documents (
          id integer primary key autoincrement,
          doc_id text not null unique,
          point_id integer not null unique,
          symbol text not null,
          name text not null default '',
          market text not null default '',
          doc_type text not null,
          title text not null default '',
          text text not null default '',
          event_date text not null default '',
          source_table text not null,
          source_row_id integer,
          text_hash text not null,
          keyword_text text not null,
          fetched_at text not null default '',
          updated_at text not null
        );

        create table if not exists iwencai_recall_terms (
          id integer primary key autoincrement,
          doc_id text not null,
          term text not null,
          normalized_term text not null,
          weight real not null default 1,
          match_kind text not null default '',
          unique(doc_id, normalized_term, match_kind)
        );

        create table if not exists iwencai_recall_state (
          key text primary key,
          value text not null default '',
          updated_at text not null
        );

        create table if not exists iwencai_recall_runs (
          id integer primary key autoincrement,
          status text not null,
          reason text not null default '',
          started_at text not null,
          finished_at text,
          source_symbols_hash text not null default '',
          source_symbol_count integer not null default 0,
          document_count integer not null default 0,
          qdrant_collection text not null default '',
          embedding_model text not null default '',
          counts_json text not null default '{}',
          error text not null default ''
        );

        create index if not exists idx_iwencai_recall_docs_symbol
        on iwencai_recall_documents(symbol, doc_type);

        create index if not exists idx_iwencai_recall_docs_type
        on iwencai_recall_documents(doc_type, event_date desc);

        create index if not exists idx_iwencai_recall_terms_norm
        on iwencai_recall_terms(normalized_term, weight desc);

        create table if not exists iwencai_recall_embeddings (
          doc_id text not null primary key,
          text_hash text not null,
          embedding_model text not null,
          vector_dim integer not null,
          vector_blob blob not null,
          updated_at text not null
        );

        create index if not exists idx_iwencai_recall_embeddings_model
        on iwencai_recall_embeddings(embedding_model, text_hash);
        """
    )


def iwencai_recall_status(
    *,
    recall_db_path: str | Path | None = None,
    iwencai_db_path: str | Path | None = None,
    include_qdrant: bool = True,
) -> dict[str, Any]:
    with get_iwencai_recall_db(recall_db_path) as conn:
        init_iwencai_recall_db(conn)
        state = recall_state(conn)
        document_count = scalar_count(conn, "iwencai_recall_documents")
        term_count = scalar_count(conn, "iwencai_recall_terms")
        embedding_cache_count = scalar_count(conn, "iwencai_recall_embeddings")
        latest_run = conn.execute(
            """
            select *
            from iwencai_recall_runs
            order by id desc
            limit 1
            """
        ).fetchone()

    source = source_snapshot(iwencai_db_path=iwencai_db_path, documents=None)
    active_collection = state.get("qdrant_collection", "")
    qdrant: dict[str, Any] = {
        "collection": active_collection,
        "status": "not_checked",
    }
    if include_qdrant and active_collection:
        try:
            qdrant["points"] = qdrant_collection_count(active_collection)
            qdrant["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - status endpoint should not fail hard.
            qdrant["status"] = "error"
            qdrant["error"] = str(exc)

    model_name = state.get("embedding_model", bge_model_name())
    model_path = local_bge_model_dir(model_name)
    return {
        "mode": "iwencai-recall-index",
        "schema_version": state.get("schema_version", ""),
        "built_at": state.get("built_at", ""),
        "embedding_model": model_name,
        "embedding_model_path": str(model_path),
        "embedding_model_ready": model_path.exists() and (model_path / "config.json").exists(),
        "embedding_device": bge_device_name(),
        "embedding_cache": embedding_cache_count,
        "source_symbols_hash": state.get("source_symbols_hash", ""),
        "source_symbol_count": int_text(state.get("source_symbol_count")),
        "source_document_count": int_text(state.get("source_document_count")),
        "documents": document_count,
        "terms": term_count,
        "source": source,
        "needs_rebuild": bool(source["symbols_hash"] and state.get("source_symbols_hash") != source["symbols_hash"]),
        "qdrant": qdrant,
        "latest_run": dict(latest_run) if latest_run else None,
        "db_path": str(Path(recall_db_path or IWENCAI_RECALL_DB_PATH).expanduser()),
    }


def sync_iwencai_recall_index(
    *,
    force: bool = False,
    dry_run: bool = False,
    recall_db_path: str | Path | None = None,
    iwencai_db_path: str | Path | None = None,
    batch_size: int = 64,
    cleanup_old_collections: bool = True,
) -> dict[str, Any]:
    documents = build_source_documents(iwencai_db_path=iwencai_db_path)
    source = source_snapshot(iwencai_db_path=iwencai_db_path, documents=documents)
    with get_iwencai_recall_db(recall_db_path) as conn:
        init_iwencai_recall_db(conn)
        state = recall_state(conn)
        previous_hash = state.get("source_symbols_hash", "")
        reason = rebuild_reason(force, previous_hash, source, state.get("schema_version", ""))
        if not reason:
            return {
                "mode": "iwencai-recall-daily-sync",
                "status": "skipped",
                "reason": "no_new_iwencai_profile_symbols",
                "source": source,
                "documents": scalar_count(conn, "iwencai_recall_documents"),
                "qdrant_collection": state.get("qdrant_collection", ""),
                "built_at": state.get("built_at", ""),
            }
        if dry_run:
            return {
                "mode": "iwencai-recall-daily-sync",
                "status": "would_rebuild",
                "reason": reason,
                "source": source,
                "document_count": len(documents),
                "qdrant_collection": planned_qdrant_collection_name(),
                "embedding_model": bge_model_name(),
            }
        run_id = start_recall_run(conn, reason, source)
        conn.commit()

    if not documents:
        with get_iwencai_recall_db(recall_db_path) as conn:
            finish_recall_run(conn, run_id, "no_source_documents", source, "", {}, "问财画像库暂无可索引文档")
            conn.commit()
        return {
            "mode": "iwencai-recall-daily-sync",
            "status": "no_source_documents",
            "reason": reason,
            "source": source,
            "run_id": run_id,
        }

    qdrant_collection = planned_qdrant_collection_name()
    counts: dict[str, Any] = {}
    try:
        embedder = get_bge_embedder()
        vector_size = embedder.vector_size(embedding_text(documents[0]))
        with open_qdrant_client() as client:
            create_qdrant_collection(client, qdrant_collection, vector_size)
            with get_iwencai_recall_db(recall_db_path) as cache_conn:
                init_iwencai_recall_db(cache_conn)
                upload_stats = upload_documents_to_qdrant(
                    client,
                    qdrant_collection,
                    embedder,
                    documents,
                    batch_size=batch_size,
                    conn=cache_conn,
                )

            with get_iwencai_recall_db(recall_db_path) as conn:
                init_iwencai_recall_db(conn)
                counts = replace_keyword_library(conn, documents)
                prune_embedding_cache(conn, {doc["doc_id"] for doc in documents})
                counts["embedding_cache_hits"] = upload_stats.get("cache_hits", 0)
                counts["embedding_encoded"] = upload_stats.get("encoded", 0)
                counts["embedding_cache_total"] = scalar_count(conn, "iwencai_recall_embeddings")
                set_recall_state(conn, "schema_version", RECALL_SCHEMA_VERSION)
                set_recall_state(conn, "built_at", now_iso())
                set_recall_state(conn, "source_symbols_hash", source["symbols_hash"])
                set_recall_state(conn, "source_symbol_count", str(source["symbol_count"]))
                set_recall_state(conn, "source_document_count", str(len(documents)))
                set_recall_state(conn, "embedding_model", embedder.model_name)
                set_recall_state(conn, "qdrant_collection", qdrant_collection)
                finish_recall_run(conn, run_id, "ok", source, qdrant_collection, counts, "")
                conn.commit()

            if cleanup_old_collections:
                cleanup_qdrant_collections(client, keep=qdrant_collection)
        return {
            "mode": "iwencai-recall-daily-sync",
            "status": "rebuilt",
            "reason": reason,
            "run_id": run_id,
            "source": source,
            "counts": counts,
            "qdrant_collection": qdrant_collection,
            "embedding_model": embedder.model_name,
        }
    except Exception as exc:
        try:
            with open_qdrant_client() as client:
                delete_qdrant_collection(client, qdrant_collection)
        except Exception:
            pass
        with get_iwencai_recall_db(recall_db_path) as conn:
            finish_recall_run(conn, run_id, "failed", source, qdrant_collection, counts, str(exc))
            conn.commit()
        raise qdrant_access_error(exc) from exc


def search_iwencai_recall(
    query: str,
    *,
    limit: int = 20,
    recall_db_path: str | Path | None = None,
    use_embedding: bool = True,
    keyword_weight: float = KEYWORD_WEIGHT,
    embedding_weight: float = EMBEDDING_WEIGHT,
    evidence_weight: float = EVIDENCE_WEIGHT,
    min_score: float | None = None,
) -> dict[str, Any]:
    raw_query = str(query or "").strip()
    if not raw_query:
        return {
            "mode": "iwencai-recall-hybrid",
            "query": {"raw": raw_query, "terms": [], "expanded_terms": []},
            "count": 0,
            "results": [],
            "error": "query is empty",
        }

    with get_iwencai_recall_db(recall_db_path) as conn:
        init_iwencai_recall_db(conn)
        state = recall_state(conn)
        parsed = parse_query_terms(raw_query)
        keyword_docs = keyword_recall(conn, parsed, doc_limit=max(80, limit * 10))
        embedding_error = ""
        embedding_docs: list[dict[str, Any]] = []
        if use_embedding:
            collection = state.get("qdrant_collection", "")
            if collection:
                try:
                    embedding_docs = embedding_recall(conn, raw_query, collection, doc_limit=max(80, limit * 10))
                except Exception as exc:  # noqa: BLE001 - keep keyword results available.
                    embedding_error = str(exc)
            else:
                embedding_error = "qdrant collection is not built"
        results = merge_recall_results(
            keyword_docs,
            embedding_docs,
            parsed,
            limit=limit,
            keyword_weight=keyword_weight,
            embedding_weight=embedding_weight if use_embedding else 0.0,
            evidence_weight=evidence_weight,
        )
        threshold = DEFAULT_MIN_RERANK_SCORE if min_score is None else float(min_score)
        results = rerank_and_filter_results(results, parsed, min_score=threshold, limit=limit)

    return {
        "mode": "iwencai-recall-hybrid",
        "query": {
            "raw": raw_query,
            "terms": parsed["terms"],
            "expanded_terms": parsed["expanded_terms"],
            "primary_terms": parsed["primary_terms"],
        },
        "weights": {
            "keyword": keyword_weight,
            "embedding": embedding_weight if use_embedding else 0.0,
            "evidence": evidence_weight,
        },
        "min_score": threshold,
        "count": len(results),
        "results": results,
        "embedding": {
            "enabled": use_embedding,
            "error": embedding_error,
        },
    }


def build_source_documents(*, iwencai_db_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(iwencai_db_path or IWENCAI_PROFILE_DB_PATH).expanduser()
    if not path.exists():
        return []
    conn = open_iwencai_readonly_db(path.resolve())
    try:
        profiles = {
            str(row["symbol"]).upper(): dict(row)
            for row in conn.execute(
                """
                select symbol, name, market, summary, fetched_at, updated_at
                from iwencai_profiles
                where status = 'ok'
                order by symbol
                """
            )
        }
        documents: list[dict[str, Any]] = []
        for profile in profiles.values():
            summary = clean_text(profile.get("summary"))
            if summary:
                documents.append(
                    make_document(
                        symbol=str(profile["symbol"]).upper(),
                        name=str(profile.get("name") or ""),
                        market=str(profile.get("market") or ""),
                        doc_type="summary",
                        title="简介和看点",
                        text=summary,
                        event_date="",
                        source_table="iwencai_profiles",
                        source_row_id=None,
                        fetched_at=str(profile.get("fetched_at") or ""),
                    )
                )

        for row in conn.execute(
            """
            select h.id, h.symbol, p.name, p.market, h.label, h.effect, h.label_type, h.fetched_at
            from iwencai_profile_highlights h
            join iwencai_profiles p on p.symbol = h.symbol
            where p.status = 'ok'
            order by h.symbol, h.id
            """
        ):
            title = clean_text(row["label"] or row["label_type"] or "看点")
            text = clean_text(" ".join([str(row["label"] or ""), str(row["effect"] or ""), str(row["label_type"] or "")]))
            if not text:
                continue
            documents.append(
                make_document(
                    symbol=str(row["symbol"]).upper(),
                    name=str(row["name"] or ""),
                    market=str(row["market"] or ""),
                    doc_type="highlight",
                    title=title,
                    text=text,
                    event_date="",
                    source_table="iwencai_profile_highlights",
                    source_row_id=int(row["id"]),
                    fetched_at=str(row["fetched_at"] or ""),
                )
            )

        for row in conn.execute(
            """
            select e.id, e.symbol, p.name, p.market, e.announcement_date,
                   e.event_name, e.content, e.fetched_at
            from iwencai_important_events e
            join iwencai_profiles p on p.symbol = e.symbol
            where p.status = 'ok'
            order by e.symbol, e.announcement_date desc, e.id desc
            """
        ):
            title = clean_text(row["event_name"] or "近期概念事件")
            text = clean_text(" ".join([str(row["event_name"] or ""), str(row["content"] or "")]))
            if not text:
                continue
            documents.append(
                make_document(
                    symbol=str(row["symbol"]).upper(),
                    name=str(row["name"] or ""),
                    market=str(row["market"] or ""),
                    doc_type="event",
                    title=title,
                    text=text,
                    event_date=clean_text(row["announcement_date"]),
                    source_table="iwencai_important_events",
                    source_row_id=int(row["id"]),
                    fetched_at=str(row["fetched_at"] or ""),
                )
            )

        for row in conn.execute(
            """
            select c.id, c.symbol, p.name, p.market, c.concept_name,
                   c.included_date, c.concept_content, c.generated_date, c.fetched_at
            from iwencai_concepts c
            join iwencai_profiles p on p.symbol = c.symbol
            where p.status = 'ok'
            order by c.symbol, c.included_date desc, c.id desc
            """
        ):
            title = clean_text(row["concept_name"] or "所属概念")
            text = clean_text(" ".join([str(row["concept_name"] or ""), str(row["concept_content"] or "")]))
            if not text:
                continue
            documents.append(
                make_document(
                    symbol=str(row["symbol"]).upper(),
                    name=str(row["name"] or ""),
                    market=str(row["market"] or ""),
                    doc_type="concept",
                    title=title,
                    text=text,
                    event_date=clean_text(row["included_date"] or row["generated_date"]),
                    source_table="iwencai_concepts",
                    source_row_id=int(row["id"]),
                    fetched_at=str(row["fetched_at"] or ""),
                )
            )

        for point_id, doc in enumerate(documents, start=1):
            doc["point_id"] = point_id
        return documents
    finally:
        conn.close()


def make_document(
    *,
    symbol: str,
    name: str,
    market: str,
    doc_type: str,
    title: str,
    text: str,
    event_date: str,
    source_table: str,
    source_row_id: int | None,
    fetched_at: str,
) -> dict[str, Any]:
    title = clean_text(title)
    text = clean_text(text)
    text_hash = stable_hash([symbol, doc_type, title, text])
    doc_id = stable_hash([symbol, source_table, source_row_id or 0, doc_type, text_hash])
    keyword_text = keyword_blob([symbol, name, market, DOC_TYPE_LABELS.get(doc_type, doc_type), title, text])
    return {
        "doc_id": doc_id,
        "point_id": 0,
        "symbol": symbol,
        "name": name,
        "market": market,
        "doc_type": doc_type,
        "title": title,
        "text": text,
        "event_date": event_date,
        "source_table": source_table,
        "source_row_id": source_row_id,
        "text_hash": text_hash,
        "keyword_text": keyword_text,
        "fetched_at": fetched_at,
        "updated_at": now_iso(),
    }


def replace_keyword_library(conn: sqlite3.Connection, documents: list[dict[str, Any]]) -> dict[str, int]:
    conn.execute("delete from iwencai_recall_terms")
    conn.execute("delete from iwencai_recall_documents")
    term_count = 0
    for doc in documents:
        conn.execute(
            """
            insert into iwencai_recall_documents (
              doc_id, point_id, symbol, name, market, doc_type, title, text, event_date,
              source_table, source_row_id, text_hash, keyword_text, fetched_at, updated_at
            )
            values (
              :doc_id, :point_id, :symbol, :name, :market, :doc_type, :title, :text, :event_date,
              :source_table, :source_row_id, :text_hash, :keyword_text, :fetched_at, :updated_at
            )
            """,
            doc,
        )
        for term in document_terms(doc):
            conn.execute(
                """
                insert or ignore into iwencai_recall_terms (
                  doc_id, term, normalized_term, weight, match_kind
                )
                values (?, ?, ?, ?, ?)
                """,
                (
                    doc["doc_id"],
                    term["term"],
                    term["normalized_term"],
                    term["weight"],
                    term["match_kind"],
                ),
            )
            term_count += 1
    return {"documents": len(documents), "terms": term_count, "symbols": len({doc["symbol"] for doc in documents})}


def document_terms(doc: dict[str, Any]) -> list[dict[str, Any]]:
    terms: dict[tuple[str, str], dict[str, Any]] = {}

    def add(term: str, weight: float, kind: str) -> None:
        clean = clean_text(term)
        normalized = normalize_term(clean)
        if not normalized:
            return
        key = (normalized, kind)
        existing = terms.get(key)
        if not existing or weight > float(existing["weight"]):
            terms[key] = {
                "term": clean,
                "normalized_term": normalized,
                "weight": weight,
                "match_kind": kind,
            }

    title = str(doc.get("title") or "")
    text = " ".join([str(doc.get("title") or ""), str(doc.get("text") or "")])
    add(str(doc.get("symbol") or ""), TERM_WEIGHTS["symbol"], "symbol")
    add(str(doc.get("name") or ""), TERM_WEIGHTS["name"], "name")
    add(title, TERM_WEIGHTS["doc_title"], "doc_title")
    if doc.get("doc_type") == "concept":
        add(title, TERM_WEIGHTS["concept_name"], "concept_name")

    for token in auto_ngram_terms(title, max_terms=TITLE_NGRAM_MAX_TERMS):
        add(token, TERM_WEIGHTS["title_ngram"], "title_ngram")

    for token in auto_ngram_terms(text, max_terms=TEXT_NGRAM_MAX_TERMS):
        add(token, TERM_WEIGHTS["text_ngram"], "text_ngram")

    for token in re.findall(r"[A-Za-z][A-Za-z0-9+.\-]{1,24}", text):
        if len(token) >= 2:
            add(token, TERM_WEIGHTS["english_token"], "english_token")
    return list(terms.values())


def parse_query_terms(query: str) -> dict[str, Any]:
    text = unicodedata.normalize("NFKC", str(query or "")).strip()
    split_text = re.sub(r"(或者|以及|并且|和|与|或|and|or)", " ", text, flags=re.I)
    split_text = re.sub(r"[,，、;；|/]+", " ", split_text)
    parts = [item.strip() for item in split_text.split() if item.strip()]
    terms = [text, *parts] if text else parts
    expansion_terms = parts or ([text] if text else [])

    primary_terms = unique_texts(parts or ([text] if text else []))
    expanded: list[str] = [text] if text else []
    for term in expansion_terms:
        expanded.append(term)
        expanded.extend(auto_query_terms(term))

    return {
        "terms": unique_texts(terms),
        "primary_terms": primary_terms,
        "expanded_terms": unique_texts(expanded),
        "normalized_terms": unique_texts([normalize_term(item) for item in expanded if normalize_term(item)]),
        "primary_normalized_terms": unique_texts([normalize_term(item) for item in primary_terms if normalize_term(item)]),
    }


def keyword_recall(conn: sqlite3.Connection, parsed_query: dict[str, Any], *, doc_limit: int) -> list[dict[str, Any]]:
    normalized_terms = list(parsed_query.get("normalized_terms") or [])
    expanded_terms = list(parsed_query.get("expanded_terms") or [])
    if not normalized_terms:
        return []

    scores: dict[str, dict[str, Any]] = {}
    placeholders = ",".join("?" for _ in normalized_terms)
    for row in conn.execute(
        f"""
        select d.*, sum(t.weight) as term_score, group_concat(distinct t.term) as matched_terms
        from iwencai_recall_terms t
        join iwencai_recall_documents d on d.doc_id = t.doc_id
        where t.normalized_term in ({placeholders})
        group by d.doc_id
        order by term_score desc
        limit ?
        """,
        [*normalized_terms, max(doc_limit * 2, 100)],
    ):
        item = dict(row)
        item["keyword_score"] = float(row["term_score"] or 0)
        item["matched_terms"] = split_matched_terms(row["matched_terms"])
        scores[item["doc_id"]] = item

    like_terms = [normalize_text(term) for term in expanded_terms if normalize_text(term)]
    if like_terms:
        clauses = " or ".join(["keyword_text like ?"] * len(like_terms))
        params = [f"%{escape_like(term)}%" for term in like_terms]
        for row in conn.execute(
            f"""
            select *
            from iwencai_recall_documents
            where {clauses}
            limit ?
            """,
            [*params, max(doc_limit * 3, 160)],
        ):
            item = scores.get(row["doc_id"], dict(row))
            item.setdefault("keyword_score", 0.0)
            item.setdefault("matched_terms", [])
            scores[row["doc_id"]] = item

    for item in scores.values():
        score, matched = score_keyword_doc(item, expanded_terms)
        item["keyword_score"] = float(item.get("keyword_score") or 0) + score
        item["matched_terms"] = unique_texts([*item.get("matched_terms", []), *matched])

    return sorted(scores.values(), key=lambda row: float(row.get("keyword_score") or 0), reverse=True)[:doc_limit]


def score_keyword_doc(doc: dict[str, Any], terms: list[str]) -> tuple[float, list[str]]:
    title = normalize_text(str(doc.get("title") or ""))
    text = normalize_text(str(doc.get("text") or ""))
    matched: list[str] = []
    score = 0.0
    for term in terms:
        needle = normalize_text(term)
        if not needle:
            continue
        if needle in title:
            score += 9.0 if doc.get("doc_type") == "concept" else 6.0
            matched.append(term)
        elif needle in text:
            score += 3.0
            matched.append(term)
    diversity = len({normalize_term(term) for term in matched if normalize_term(term)})
    if diversity > 1:
        score += 1.5 * math.log1p(diversity)
    score *= DOC_TYPE_EVIDENCE_WEIGHT.get(str(doc.get("doc_type") or ""), 0.7)
    return score, matched


def embedding_recall(
    conn: sqlite3.Connection,
    query: str,
    collection: str,
    *,
    doc_limit: int,
) -> list[dict[str, Any]]:
    embedder = get_bge_embedder()
    vector = embedder.encode_query(query)
    with open_qdrant_client() as client:
        hits = qdrant_search(client, collection, vector, doc_limit)
    if not hits:
        return []
    by_doc_id: dict[str, float] = {}
    for hit in hits:
        payload = getattr(hit, "payload", None) or {}
        doc_id = str(payload.get("doc_id") or "")
        if not doc_id:
            continue
        by_doc_id[doc_id] = max(float(getattr(hit, "score", 0.0) or 0.0), by_doc_id.get(doc_id, 0.0))
    if not by_doc_id:
        return []
    rows = documents_by_id(conn, list(by_doc_id))
    for row in rows:
        row["embedding_score"] = by_doc_id.get(row["doc_id"], 0.0)
    return sorted(rows, key=lambda row: float(row.get("embedding_score") or 0), reverse=True)


def merge_recall_results(
    keyword_docs: list[dict[str, Any]],
    embedding_docs: list[dict[str, Any]],
    parsed_query: dict[str, Any],
    *,
    limit: int,
    keyword_weight: float,
    embedding_weight: float,
    evidence_weight: float,
) -> list[dict[str, Any]]:
    docs: dict[str, dict[str, Any]] = {}
    for item in keyword_docs:
        doc = docs.setdefault(item["doc_id"], dict(item))
        doc["keyword_score"] = max(float(doc.get("keyword_score") or 0), float(item.get("keyword_score") or 0))
        doc["matched_terms"] = unique_texts([*doc.get("matched_terms", []), *item.get("matched_terms", [])])
    for item in embedding_docs:
        doc = docs.setdefault(item["doc_id"], dict(item))
        doc["embedding_score"] = max(float(doc.get("embedding_score") or 0), float(item.get("embedding_score") or 0))

    stocks: dict[str, dict[str, Any]] = {}
    max_keyword = max([float(doc.get("keyword_score") or 0) for doc in docs.values()] or [1.0])
    for doc in docs.values():
        keyword_norm = float(doc.get("keyword_score") or 0) / max(max_keyword, 1.0)
        embedding_norm = clamp01(float(doc.get("embedding_score") or 0))
        evidence = evidence_quality(doc)
        score = keyword_weight * keyword_norm + embedding_weight * embedding_norm + evidence_weight * evidence
        symbol = str(doc.get("symbol") or "")
        stock = stocks.setdefault(
            symbol,
            {
                "symbol": symbol,
                "name": str(doc.get("name") or ""),
                "market": str(doc.get("market") or ""),
                "score": 0.0,
                "keyword_score": 0.0,
                "embedding_score": 0.0,
                "evidence_score": 0.0,
                "matched_terms": [],
                "evidence": [],
            },
        )
        stock["score"] = max(float(stock["score"]), score)
        stock["keyword_score"] = max(float(stock["keyword_score"]), keyword_norm)
        stock["embedding_score"] = max(float(stock["embedding_score"]), embedding_norm)
        stock["evidence_score"] = max(float(stock["evidence_score"]), evidence)
        stock["matched_terms"] = unique_texts([*stock["matched_terms"], *doc.get("matched_terms", [])])
        stock["evidence"].append(render_evidence_doc(doc, parsed_query))

    for stock in stocks.values():
        stock["score"] = round(min(1.0, float(stock["score"]) + 0.03 * math.log1p(len(stock["evidence"]))), 4)
        stock["keyword_score"] = round(float(stock["keyword_score"]), 4)
        stock["embedding_score"] = round(float(stock["embedding_score"]), 4)
        stock["evidence_score"] = round(float(stock["evidence_score"]), 4)
        stock["evidence"] = sorted(
            stock["evidence"],
            key=lambda item: (
                float(item.get("keyword_score") or 0),
                float(item.get("embedding_score") or 0),
                item.get("doc_type") == "concept",
            ),
            reverse=True,
        )[:5]
    return sorted(stocks.values(), key=lambda item: float(item["score"]), reverse=True)[:limit]


def is_strict_primary_query(primary_terms: list[str]) -> bool:
    if not primary_terms:
        return False
    if len(primary_terms) == 1:
        term = str(primary_terms[0]).strip()
        if re.fullmatch(r"[A-Za-z0-9+.\-]{2,8}", term):
            return True
        if 2 <= len(normalize_term(term)) <= 4:
            return True
    english_like = [term for term in primary_terms if re.search(r"[A-Za-z]", term)]
    return len(english_like) == len(primary_terms) and len(primary_terms) <= 2


def evidence_matches_primary_term(evidence: dict[str, Any], primary_term: str) -> bool:
    normalized_primary = normalize_term(primary_term)
    if not normalized_primary:
        return False
    matched_terms = evidence.get("matched_terms") or []
    if any(normalize_term(term) == normalized_primary for term in matched_terms):
        return True
    haystacks = [
        str(evidence.get("title") or ""),
        str(evidence.get("snippet") or ""),
    ]
    for haystack in haystacks:
        compact = normalize_term(haystack)
        if normalized_primary in compact:
            return True
        if re.search(r"[A-Za-z]", primary_term):
            if re.search(rf"(?<![a-z0-9]){re.escape(normalized_primary)}(?![a-z0-9])", normalize_text(haystack)):
                return True
    return False


def count_primary_term_matches(stock: dict[str, Any], primary_terms: list[str]) -> int:
    evidence = list(stock.get("evidence") or [])
    if not evidence or not primary_terms:
        return 0
    matched = 0
    for term in primary_terms:
        if any(evidence_matches_primary_term(item, term) for item in evidence[:3]):
            matched += 1
    return matched


def compute_rerank_score(stock: dict[str, Any], parsed_query: dict[str, Any]) -> tuple[float, int]:
    primary_terms = list(parsed_query.get("primary_terms") or [])
    primary_matches = count_primary_term_matches(stock, primary_terms)
    base_score = float(stock.get("score") or 0)
    keyword_score = float(stock.get("keyword_score") or 0)
    embedding_score = float(stock.get("embedding_score") or 0)
    primary_ratio = primary_matches / max(len(primary_terms), 1)
    rerank = base_score + 0.28 * primary_ratio
    if primary_matches == 0:
        rerank -= 0.22
    if keyword_score < 0.08 and embedding_score > 0.25:
        rerank -= 0.18
    if primary_matches > 0 and keyword_score >= 0.2:
        rerank += 0.08
    if is_strict_primary_query(primary_terms) and primary_matches == 0:
        rerank = min(rerank, 0.18)
    return round(clamp01(rerank), 4), primary_matches


def rerank_and_filter_results(
    results: list[dict[str, Any]],
    parsed_query: dict[str, Any],
    *,
    min_score: float,
    limit: int,
) -> list[dict[str, Any]]:
    reranked: list[dict[str, Any]] = []
    for stock in results:
        rerank_score, primary_matches = compute_rerank_score(stock, parsed_query)
        stock["rerank_score"] = rerank_score
        stock["primary_match_count"] = primary_matches
        if rerank_score < min_score:
            continue
        if is_strict_primary_query(parsed_query.get("primary_terms") or []) and primary_matches == 0:
            continue
        evidence = list(stock.get("evidence") or [])
        primary_terms = list(parsed_query.get("primary_terms") or [])
        matched_evidence = [
            item
            for item in evidence
            if (item.get("matched_terms") or [])
            or any(evidence_matches_primary_term(item, term) for term in primary_terms)
        ]
        if matched_evidence:
            stock["evidence"] = matched_evidence[:3] + [item for item in evidence if item not in matched_evidence][:2]
            stock["evidence"] = stock["evidence"][:5]
        reranked.append(stock)
    reranked.sort(
        key=lambda item: (
            float(item.get("rerank_score") or 0),
            float(item.get("keyword_score") or 0),
            float(item.get("score") or 0),
        ),
        reverse=True,
    )
    return reranked[:limit]


def render_evidence_doc(doc: dict[str, Any], parsed_query: dict[str, Any]) -> dict[str, Any]:
    terms = list(parsed_query.get("expanded_terms") or [])
    return {
        "doc_id": doc.get("doc_id"),
        "doc_type": doc.get("doc_type"),
        "doc_type_label": DOC_TYPE_LABELS.get(str(doc.get("doc_type") or ""), str(doc.get("doc_type") or "")),
        "title": doc.get("title"),
        "event_date": doc.get("event_date") or "",
        "source_table": doc.get("source_table"),
        "snippet": snippet_for_terms(str(doc.get("text") or ""), terms),
        "matched_terms": doc.get("matched_terms", []),
        "keyword_score": round(float(doc.get("keyword_score") or 0), 4),
        "embedding_score": round(float(doc.get("embedding_score") or 0), 4),
    }


def source_snapshot(
    *,
    iwencai_db_path: str | Path | None = None,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    docs = documents if documents is not None else build_source_documents(iwencai_db_path=iwencai_db_path)
    symbols = sorted({str(doc["symbol"]).upper() for doc in docs if doc.get("symbol")})
    doc_type_counts: dict[str, int] = {}
    for doc in docs:
        doc_type = str(doc.get("doc_type") or "")
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
    return {
        "db_path": str(Path(iwencai_db_path or IWENCAI_PROFILE_DB_PATH).expanduser()),
        "symbol_count": len(symbols),
        "document_count": len(docs),
        "symbols_hash": stable_hash(symbols),
        "doc_type_counts": doc_type_counts,
    }


def rebuild_reason(force: bool, previous_hash: str, source: dict[str, Any], previous_schema_version: str = "") -> str:
    current_hash = str(source.get("symbols_hash") or "")
    if force:
        return "force"
    if previous_schema_version != RECALL_SCHEMA_VERSION:
        return "schema_version_changed"
    if not previous_hash:
        return "initial_build"
    if previous_hash != current_hash:
        return "new_iwencai_profile_symbols"
    return ""


def bge_device_name() -> str:
    return os.environ.get("IWENCAI_BGE_DEVICE", "cpu").strip() or "cpu"


def local_bge_model_dir(model_name: str | None = None) -> Path:
    override = os.environ.get("IWENCAI_BGE_MODEL_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    name = model_name or bge_model_name()
    slug = name.split("/")[-1] if "/" in name else name
    return IWENCAI_BGE_MODELS_DIR / slug


def ensure_local_bge_model(model_name: str | None = None) -> Path:
    name = model_name or bge_model_name()
    target = local_bge_model_dir(name)
    if target.exists() and (target / "config.json").exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - optional dependency path.
        raise RuntimeError(
            "huggingface_hub is required to download the local BGE model. "
            "Install requirements.txt or run scripts/download_iwencai_bge_model.py first."
        ) from exc
    snapshot_download(
        repo_id=name,
        local_dir=str(target),
        local_dir_use_symlinks=False,
    )
    return target


def get_bge_embedder(model_name: str | None = None) -> "BgeEmbedder":
    name = model_name or bge_model_name()
    cached = _BGE_EMBEDDER_CACHE.get(name)
    if cached is not None:
        return cached
    embedder = BgeEmbedder(name)
    _BGE_EMBEDDER_CACHE[name] = embedder
    return embedder


def vector_to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def blob_to_vector(blob: bytes) -> list[float]:
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def load_embedding_cache(
    conn: sqlite3.Connection,
    documents: list[dict[str, Any]],
    embedding_model: str,
) -> dict[str, dict[str, Any]]:
    if not documents:
        return {}
    doc_ids = [str(doc["doc_id"]) for doc in documents]
    placeholders = ",".join("?" for _ in doc_ids)
    rows = conn.execute(
        f"""
        select doc_id, text_hash, vector_dim, vector_blob
        from iwencai_recall_embeddings
        where embedding_model = ? and doc_id in ({placeholders})
        """,
        [embedding_model, *doc_ids],
    ).fetchall()
    cached: dict[str, dict[str, Any]] = {}
    for row in rows:
        cached[str(row["doc_id"])] = {
            "text_hash": str(row["text_hash"]),
            "vector": blob_to_vector(bytes(row["vector_blob"])),
            "vector_dim": int(row["vector_dim"]),
        }
    return cached


def save_embedding_cache(
    conn: sqlite3.Connection,
    documents: list[dict[str, Any]],
    vectors: list[list[float]],
    embedding_model: str,
) -> None:
    timestamp = now_iso()
    for doc, vector in zip(documents, vectors):
        conn.execute(
            """
            insert into iwencai_recall_embeddings (
              doc_id, text_hash, embedding_model, vector_dim, vector_blob, updated_at
            )
            values (?, ?, ?, ?, ?, ?)
            on conflict(doc_id) do update set
              text_hash = excluded.text_hash,
              embedding_model = excluded.embedding_model,
              vector_dim = excluded.vector_dim,
              vector_blob = excluded.vector_blob,
              updated_at = excluded.updated_at
            """,
            (
                doc["doc_id"],
                doc["text_hash"],
                embedding_model,
                len(vector),
                vector_to_blob(vector),
                timestamp,
            ),
        )


def prune_embedding_cache(conn: sqlite3.Connection, active_doc_ids: set[str]) -> int:
    if not active_doc_ids:
        return 0
    placeholders = ",".join("?" for _ in active_doc_ids)
    cursor = conn.execute(
        f"delete from iwencai_recall_embeddings where doc_id not in ({placeholders})",
        list(active_doc_ids),
    )
    return int(cursor.rowcount or 0)


class BgeEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional local install.
            raise RuntimeError(
                "sentence-transformers is required for BGE embeddings. "
                "Install requirements.txt before building the recall index."
            ) from exc
        model_path = ensure_local_bge_model(model_name)
        device = bge_device_name()
        self.model = SentenceTransformer(str(model_path), device=device)
        self.model_path = str(model_path)
        self.device = device

    def vector_size(self, text: str) -> int:
        vector = self.encode_documents([text])[0]
        return len(vector)

    def encode_query(self, query: str) -> list[float]:
        return self.encode_documents([query])[0]

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            batch_size=max(1, int(os.environ.get("IWENCAI_BGE_BATCH_SIZE", "64"))),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]


def qdrant_local_path() -> Path:
    path = Path(os.environ.get("IWENCAI_QDRANT_PATH", IWENCAI_QDRANT_LOCAL_PATH)).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def qdrant_access_error(exc: Exception) -> RuntimeError:
    message = str(exc)
    if "already accessed by another instance" in message:
        path = qdrant_local_path()
        return RuntimeError(
            "Qdrant 本地目录正被其他进程占用（通常是正在运行的 uvicorn）。"
            f"路径：{path}。"
            "请先停止 API 后再执行重建，或设置 QDRANT_URL 使用独立 Qdrant 服务。"
        )
    if isinstance(exc, RuntimeError):
        return exc
    return RuntimeError(message)


@contextmanager
def open_qdrant_client():
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:  # pragma: no cover - depends on optional local install.
        raise RuntimeError(
            "qdrant-client is required for the iWenCai embedding recall database. "
            "Install requirements.txt before building or searching embeddings."
        ) from exc
    url = os.environ.get("QDRANT_URL", "").strip()
    api_key = os.environ.get("QDRANT_API_KEY", "").strip() or None
    timeout = float(os.environ.get("QDRANT_TIMEOUT", "60"))
    if url:
        key = ("url", url, api_key or "", timeout)
        if key not in _QDRANT_CLIENT_CACHE:
            _QDRANT_CLIENT_CACHE[key] = QdrantClient(url=url, api_key=api_key, timeout=timeout)
        yield _QDRANT_CLIENT_CACHE[key]
        return
    try:
        client = QdrantClient(path=str(qdrant_local_path()), timeout=timeout)
    except Exception as exc:
        raise qdrant_access_error(exc) from exc
    try:
        yield client
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def create_qdrant_collection(client: Any, collection_name: str, vector_size: int) -> None:
    from qdrant_client.http.models import Distance, VectorParams

    if collection_exists(client, collection_name):
        delete_qdrant_collection(client, collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def upload_documents_to_qdrant(
    client: Any,
    collection_name: str,
    embedder: BgeEmbedder,
    documents: list[dict[str, Any]],
    *,
    batch_size: int,
    conn: sqlite3.Connection | None = None,
) -> dict[str, int]:
    from qdrant_client.http.models import PointStruct

    clean_batch_size = max(1, batch_size)
    cache_hits = 0
    encoded = 0
    for start in range(0, len(documents), clean_batch_size):
        batch = documents[start : start + clean_batch_size]
        cached = load_embedding_cache(conn, batch, embedder.model_name) if conn is not None else {}
        vectors: list[list[float] | None] = [None] * len(batch)
        misses: list[tuple[int, dict[str, Any]]] = []
        for index, doc in enumerate(batch):
            hit = cached.get(str(doc["doc_id"]))
            if hit and hit["text_hash"] == doc["text_hash"]:
                vectors[index] = hit["vector"]
                cache_hits += 1
            else:
                misses.append((index, doc))
        if misses:
            encoded_vectors = embedder.encode_documents([embedding_text(doc) for _, doc in misses])
            if conn is not None:
                save_embedding_cache(conn, [doc for _, doc in misses], encoded_vectors, embedder.model_name)
            for (index, _), vector in zip(misses, encoded_vectors):
                vectors[index] = vector
            encoded += len(misses)
        points = [
            PointStruct(
                id=int(doc["point_id"]),
                vector=vector,
                payload={
                    "doc_id": doc["doc_id"],
                    "symbol": doc["symbol"],
                    "name": doc["name"],
                    "market": doc["market"],
                    "doc_type": doc["doc_type"],
                    "title": doc["title"],
                    "event_date": doc["event_date"],
                    "source_table": doc["source_table"],
                },
            )
            for doc, vector in zip(batch, vectors)
            if vector is not None
        ]
        client.upsert(collection_name=collection_name, points=points, wait=True)
        if conn is not None:
            conn.commit()
    return {"cache_hits": cache_hits, "encoded": encoded}


def qdrant_search(client: Any, collection_name: str, vector: list[float], limit: int) -> list[Any]:
    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
    result = client.query_points(
        collection_name=collection_name,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    return list(getattr(result, "points", result))


def qdrant_collection_count(collection_name: str) -> int:
    with open_qdrant_client() as client:
        if not collection_exists(client, collection_name):
            return 0
        result = client.count(collection_name=collection_name, exact=True)
        return int(getattr(result, "count", 0))


def collection_exists(client: Any, collection_name: str) -> bool:
    if hasattr(client, "collection_exists"):
        return bool(client.collection_exists(collection_name))
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False


def delete_qdrant_collection(client: Any, collection_name: str) -> None:
    if collection_exists(client, collection_name):
        client.delete_collection(collection_name=collection_name)


def cleanup_qdrant_collections(client: Any, *, keep: str) -> None:
    base = qdrant_collection_base()
    try:
        collections = client.get_collections().collections
    except Exception:
        return
    for item in collections:
        name = str(getattr(item, "name", ""))
        if name != keep and name.startswith(f"{base}_"):
            try:
                client.delete_collection(collection_name=name)
            except Exception:
                pass


def planned_qdrant_collection_name() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{qdrant_collection_base()}_{stamp}"


def qdrant_collection_base() -> str:
    return os.environ.get("IWENCAI_QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION_BASE).strip() or DEFAULT_QDRANT_COLLECTION_BASE


def bge_model_name() -> str:
    return os.environ.get("IWENCAI_BGE_MODEL", DEFAULT_BGE_MODEL).strip() or DEFAULT_BGE_MODEL


def embedding_text(doc: dict[str, Any]) -> str:
    parts = [
        f"股票：{doc.get('symbol')} {doc.get('name')}",
        f"类型：{DOC_TYPE_LABELS.get(str(doc.get('doc_type') or ''), doc.get('doc_type'))}",
        f"标题：{doc.get('title')}",
        f"正文：{doc.get('text')}",
    ]
    return clean_text("。".join(str(part) for part in parts))[:2400]


def documents_by_id(conn: sqlite3.Connection, doc_ids: list[str]) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    placeholders = ",".join("?" for _ in doc_ids)
    rows = conn.execute(
        f"""
        select *
        from iwencai_recall_documents
        where doc_id in ({placeholders})
        """,
        doc_ids,
    ).fetchall()
    by_id = {row["doc_id"]: dict(row) for row in rows}
    return [by_id[doc_id] for doc_id in doc_ids if doc_id in by_id]


def evidence_quality(doc: dict[str, Any]) -> float:
    base = DOC_TYPE_EVIDENCE_WEIGHT.get(str(doc.get("doc_type") or ""), 0.6)
    event_date = str(doc.get("event_date") or "")
    if re.fullmatch(r"\d{8}", event_date):
        year = int(event_date[:4])
        if year >= datetime.now().year - 1:
            base += 0.06
    return clamp01(base)


def snippet_for_terms(text: str, terms: list[str], *, width: int = 120) -> str:
    clean = clean_text(text)
    normalized_clean = normalize_text(clean)
    match_index = -1
    for term in terms:
        needle = normalize_text(term)
        if not needle:
            continue
        normalized_index = normalized_clean.find(needle)
        if normalized_index >= 0:
            compact_before = normalized_clean[:normalized_index]
            match_index = min(len(clean), len(compact_before))
            break
    if match_index < 0:
        return clean[:width] + ("..." if len(clean) > width else "")
    start = max(0, match_index - width // 3)
    end = min(len(clean), start + width)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end]}{suffix}"


def start_recall_run(conn: sqlite3.Connection, reason: str, source: dict[str, Any]) -> int:
    cursor = conn.execute(
        """
        insert into iwencai_recall_runs (
          status, reason, started_at, source_symbols_hash, source_symbol_count, document_count,
          embedding_model
        )
        values ('running', ?, ?, ?, ?, ?, ?)
        """,
        (
            reason,
            now_iso(),
            str(source.get("symbols_hash") or ""),
            int(source.get("symbol_count") or 0),
            int(source.get("document_count") or 0),
            bge_model_name(),
        ),
    )
    return int(cursor.lastrowid)


def finish_recall_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    source: dict[str, Any],
    qdrant_collection: str,
    counts: dict[str, Any],
    error: str,
) -> None:
    conn.execute(
        """
        update iwencai_recall_runs
        set status = ?,
            finished_at = ?,
            source_symbols_hash = ?,
            source_symbol_count = ?,
            document_count = ?,
            qdrant_collection = ?,
            embedding_model = ?,
            counts_json = ?,
            error = ?
        where id = ?
        """,
        (
            status,
            now_iso(),
            str(source.get("symbols_hash") or ""),
            int(source.get("symbol_count") or 0),
            int(source.get("document_count") or 0),
            qdrant_collection,
            bge_model_name(),
            json_text(counts),
            error[:2000],
            run_id,
        ),
    )


def recall_state(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"] or "")
        for row in conn.execute("select key, value from iwencai_recall_state")
    }


def set_recall_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        insert into iwencai_recall_state (key, value, updated_at)
        values (?, ?, ?)
        on conflict(key) do update set
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (key, value, now_iso()),
    )


def scalar_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"select count(*) from {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


GENERIC_NOISE_TERMS = {
    "公司",
    "股份",
    "有限",
    "集团",
    "公告",
    "根据",
    "互动",
    "投资",
    "项目",
    "业务",
    "产品",
    "相关",
    "主要",
    "目前",
    "领域",
    "技术",
    "发展",
    "实现",
    "提供",
    "客户",
    "市场",
    "行业",
    "概念",
    "纳入",
}


def auto_query_terms(value: Any) -> list[str]:
    text = clean_text(value)
    terms: list[str] = []
    english_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.\-]{1,24}", text)
    for token in english_tokens:
        terms.append(token)
    residual = re.sub(r"[A-Za-z][A-Za-z0-9+.\-]{1,24}", " ", text)
    if clean_text(residual):
        terms.extend(auto_ngram_terms(residual, max_terms=QUERY_NGRAM_MAX_TERMS))
    elif not terms:
        terms.extend(auto_ngram_terms(text, max_terms=QUERY_NGRAM_MAX_TERMS))
    return unique_texts(terms)


def auto_ngram_terms(value: Any, *, max_terms: int) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for chunk in compact_search_chunks(value):
        if not useful_auto_term(chunk):
            continue
        add_auto_term(terms, seen, chunk, max_terms)
        for part in chunk_windows(chunk):
            for segment in ngram_segments(part):
                length = len(segment)
                if length < 2:
                    continue
                short_max = min(4, length)
                for size in range(2, short_max + 1):
                    for start in range(0, length - size + 1):
                        if len(terms) >= max_terms:
                            return terms
                        add_auto_term(terms, seen, segment[start : start + size], max_terms)
                for size in range(5, min(8, length) + 1):
                    for start in range(0, length - size + 1):
                        if len(terms) >= max_terms:
                            return terms
                        add_auto_term(terms, seen, segment[start : start + size], max_terms)
    return terms


def ngram_segments(value: str) -> list[str]:
    return [
        segment
        for segment in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", value)
        if len(segment) >= 2
    ]


def compact_search_chunks(value: Any) -> list[str]:
    text = normalize_text(value)
    text = re.sub(r"[^0-9a-z+\-.\u4e00-\u9fff]+", " ", text)
    chunks: list[str] = []
    for chunk in text.split():
        normalized = normalize_term(chunk)
        if len(normalized) >= 2:
            chunks.append(normalized)
    return chunks


def chunk_windows(chunk: str, *, size: int = 48, overlap: int = 8) -> list[str]:
    if len(chunk) <= size:
        return [chunk]
    windows: list[str] = []
    step = max(1, size - overlap)
    for start in range(0, len(chunk), step):
        part = chunk[start : start + size]
        if len(part) >= 2:
            windows.append(part)
        if start + size >= len(chunk):
            break
    return windows


def add_auto_term(terms: list[str], seen: set[str], term: str, max_terms: int) -> None:
    normalized = normalize_term(term)
    if len(terms) >= max_terms or not useful_auto_term(normalized) or normalized in seen:
        return
    seen.add(normalized)
    terms.append(term)


def useful_auto_term(term: str) -> bool:
    normalized = normalize_term(term)
    if len(normalized) < 2:
        return False
    if normalized in GENERIC_NOISE_TERMS:
        return False
    if normalized.isdigit():
        return False
    return bool(re.search(r"[a-z\u4e00-\u9fff]", normalized))


def split_matched_terms(value: Any) -> list[str]:
    if not value:
        return []
    return unique_texts([item.strip() for item in str(value).split(",") if item.strip()])


def keyword_blob(parts: list[Any]) -> str:
    text = normalize_text(" ".join(str(part or "") for part in parts))
    compact = re.sub(r"\s+", "", text)
    return f"{text} {compact}"


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_term(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"[\s_\-—·.,，、;；:：/\\|+]+", "", text)
    text = re.sub(r"[()（）\[\]【】{}<>《》\"'“”‘’]", "", text)
    return text.strip()


def clean_text(value: Any) -> str:
    text = str(value or "").replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        key = normalize_term(text)
        if not text or not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str, separators=(",", ":"))


def escape_like(value: str) -> str:
    return value.replace("%", "\\%").replace("_", "\\_")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def int_text(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
