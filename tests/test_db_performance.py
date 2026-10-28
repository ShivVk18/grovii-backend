"""DB-02: loading one storyboard with all its parts must not multiply rows.

With 7 joinedloads, Postgres returns the cartesian product of all child
collections in one result (5 scenes x 5 hooks x 3 captions x 15 hashtags x
3 music = 3,375 rows for one storyboard). selectinload issues one small
query per relation instead, returning only the real rows.
"""
from sqlalchemy import event

from src.database import engine
from src.models import (
    Caption,
    Hashtag,
    Hook,
    MusicSuggestion,
    RepurposeContent,
    Scene,
    Storyboard,
    Trend,
)

CHILDREN = {"scenes": 5, "hooks": 5, "captions": 3, "hashtags": 15, "music": 3, "trends": 1, "repurpose": 1}
REAL_ROWS = 1 + sum(CHILDREN.values())  # 34


def _seed(db, user):
    sb = Storyboard(user_id=user.id, idea="x" * 10, goal="educate", tone="calm", style="pov",
                    audience="ab", duration=30, platform="reels", status="completed")
    db.add(sb)
    db.flush()
    db.add_all([Scene(storyboard_id=sb.id, scene_number=i) for i in range(5)]
               + [Hook(storyboard_id=sb.id, hook=f"h{i}", selected=False) for i in range(5)]
               + [Caption(storyboard_id=sb.id, caption=f"c{i}") for i in range(3)]
               + [Hashtag(storyboard_id=sb.id, hashtag=f"#t{i}") for i in range(15)]
               + [MusicSuggestion(storyboard_id=sb.id, song_name=f"s{i}") for i in range(3)]
               + [Trend(storyboard_id=sb.id), RepurposeContent(storyboard_id=sb.id, linkedin="x")])
    db.commit()
    return sb.id


def measure(fn):
    stats = {"queries": 0, "rows": 0}

    def after(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            stats["queries"] += 1
            stats["rows"] += max(cursor.rowcount, 0)

    event.listen(engine, "after_cursor_execute", after)
    try:
        result = fn()
    finally:
        event.remove(engine, "after_cursor_execute", after)
    return result, stats


def test_storyboard_with_relations_returns_only_real_rows(db, user):
    from src.repositories.storyboard_repository import get_storyboard_with_relations

    sb_id, uid = _seed(db, user), user.id  # read ids first: no lazy reloads inside the measurement
    db.expire_all()
    sb, stats = measure(lambda: get_storyboard_with_relations(db, sb_id, uid))

    for rel, n in CHILDREN.items():
        value = getattr(sb, rel)
        assert (len(value) if isinstance(value, list) else int(value is not None)) == n, rel
    print(f"\nget_storyboard_with_relations: {stats['queries']} queries, {stats['rows']} rows")
    assert stats["rows"] <= REAL_ROWS
    assert stats["queries"] <= 1 + len(CHILDREN)


def test_pool_is_sized_from_env_with_pre_ping():
    import os
    import subprocess
    import sys

    code = ("from src.database import engine as e; p = e.pool; "
            "print(p.size(), p._max_overflow, p._timeout, e.pool._pre_ping)")
    env = {**os.environ, "DB_POOL_SIZE": "7", "DB_MAX_OVERFLOW": "3", "DB_POOL_TIMEOUT": "4"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["7", "3", "4.0", "True"]


def test_worker_process_uses_a_small_pool():
    import os
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k not in ("DB_POOL_SIZE", "DB_MAX_OVERFLOW")}
    code = ("from unittest.mock import patch\n"
            "with patch('rq.SimpleWorker'):\n"
            "    import src.services.worker\n"
            "from src.database import engine as e\n"
            "print(e.pool.size(), e.pool._max_overflow)")
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["2", "1"]
