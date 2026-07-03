# -*- coding: utf-8 -*-
"""
저장소 모듈
- SQLite로 구현 (검증 후 MySQL 전환 시 get_connection()과 SQL 문법만 조정하면 됨)
- 스키마는 raw(원문) / tagged(정제+태깅 결과) 두 테이블로 분리
  → 원본은 항상 보존하고, 태깅 로직이 바뀌어도 재처리 가능하게 설계
"""
import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_date TEXT,
    raw_text TEXT,
    image_url TEXT,
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tagged_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    category TEXT,
    companies TEXT,      -- JSON list
    products TEXT,       -- JSON list
    technologies TEXT,   -- JSON list
    indications TEXT,    -- JSON list
    competitor_flag INTEGER DEFAULT 0,
    sentiment TEXT,       -- 긍정/부정/중립
    summary TEXT,          -- LLM이 생성한 1~2문장 한글 요약
    tagged_at TEXT NOT NULL,
    FOREIGN KEY (article_id) REFERENCES raw_articles(id)
);

CREATE INDEX IF NOT EXISTS idx_raw_url ON raw_articles(url);
CREATE INDEX IF NOT EXISTS idx_tagged_article_id ON tagged_articles(article_id);
"""


@contextmanager
def get_connection():
    """DB 커넥션 컨텍스트 매니저.
    MySQL 전환 시 이 함수만 mysql.connector.connect(...)로 교체하면 나머지 코드는 거의 그대로 사용 가능.
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# 새 컬럼이 추가될 때마다 여기 등록해두면 기존 DB에도 init_db()가 자동으로 반영합니다.
# (SQLite는 스키마 변경을 자동 감지하지 못하므로 직접 관리해야 함)
RAW_ARTICLES_COLUMNS = {
    "image_url": "TEXT",
}


def init_db():
    """테이블이 없으면 생성하고, 기존 DB라면 누락된 컬럼을 자동으로 추가(마이그레이션)한다."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_columns(conn, "raw_articles", RAW_ARTICLES_COLUMNS)


def _migrate_columns(conn, table, required_columns):
    """PRAGMA table_info로 현재 컬럼을 확인하고, 없는 컬럼만 ALTER TABLE로 추가."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for col_name, col_type in required_columns.items():
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            print(f"[storage] 마이그레이션: {table}.{col_name} 컬럼을 추가했습니다.")


def get_existing_urls():
    """이미 수집된 기사 URL 집합 반환 (중복 수집 방지용)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT url FROM raw_articles").fetchall()
        return {row["url"] for row in rows}


def get_existing_titles(limit=500):
    """최근 title 목록 반환 (유사도 기반 중복 판단용)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title FROM raw_articles ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [(row["id"], row["title"]) for row in rows]


def insert_raw_article(source, title, url, published_date, raw_text, image_url=""):
    """원문 기사를 저장하고 새로 생성된 id를 반환. 이미 존재하면 None 반환."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO raw_articles (source, title, url, published_date, raw_text, image_url, collected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (source, title, url, published_date, raw_text, image_url, now),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # UNIQUE(url) 위반 = 이미 수집된 기사
            return None


def get_untagged_articles():
    """아직 태깅되지 않은 raw_articles 목록 반환."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.* FROM raw_articles r
               LEFT JOIN tagged_articles t ON r.id = t.article_id
               WHERE t.id IS NULL"""
        ).fetchall()
        return [dict(row) for row in rows]


def insert_tagged_article(article_id, tag_result):
    """LLM 태깅 결과 저장. tag_result는 dict (tagger.py의 출력 형식)."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tagged_articles
               (article_id, category, companies, products, technologies, indications,
                competitor_flag, sentiment, summary, tagged_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article_id,
                tag_result.get("category"),
                json.dumps(tag_result.get("companies", []), ensure_ascii=False),
                json.dumps(tag_result.get("products", []), ensure_ascii=False),
                json.dumps(tag_result.get("technologies", []), ensure_ascii=False),
                json.dumps(tag_result.get("indications", []), ensure_ascii=False),
                int(tag_result.get("competitor_flag", False)),
                tag_result.get("sentiment"),
                tag_result.get("summary"),
                now,
            ),
        )


def get_articles_missing_image(source="Naver News"):
    """특정 소스 중 image_url이 비어있는 기사 목록 반환 (백필 대상 조회용)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, title, url FROM raw_articles
               WHERE source = ? AND (image_url IS NULL OR image_url = '')""",
            (source,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_image_url(article_id, image_url):
    """기존 기사의 image_url을 갱신 (백필용)."""
    with get_connection() as conn:
        conn.execute("UPDATE raw_articles SET image_url = ? WHERE id = ?", (image_url, article_id))


def get_articles_by_category(category):
    """특정 카테고리로 태깅된 기사 전체를 raw_text 포함해서 반환 (정리/재검토용)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.id, r.source, r.title, r.url, r.published_date, r.raw_text,
                      t.category, t.summary
               FROM raw_articles r
               JOIN tagged_articles t ON r.id = t.article_id
               WHERE t.category = ?
               ORDER BY r.published_date DESC""",
            (category,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_articles(article_ids):
    """주어진 article id 목록을 raw_articles/tagged_articles에서 함께 삭제."""
    if not article_ids:
        return 0
    with get_connection() as conn:
        placeholders = ",".join("?" * len(article_ids))
        conn.execute(f"DELETE FROM tagged_articles WHERE article_id IN ({placeholders})", article_ids)
        cur = conn.execute(f"DELETE FROM raw_articles WHERE id IN ({placeholders})", article_ids)
        return cur.rowcount
def get_tagged_articles_between(start_date, end_date):
    """기간 내 태깅된 기사 전체를 join하여 반환 (트렌드 분석용)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.id, r.source, r.title, r.url, r.published_date, r.image_url,
                      t.category, t.companies, t.products, t.technologies,
                      t.indications, t.competitor_flag, t.sentiment, t.summary
               FROM raw_articles r
               JOIN tagged_articles t ON r.id = t.article_id
               WHERE r.published_date BETWEEN ? AND ?
               ORDER BY r.published_date DESC""",
            (start_date, end_date),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for field in ("companies", "products", "technologies", "indications"):
                d[field] = json.loads(d[field]) if d[field] else []
            result.append(d)
        return result
