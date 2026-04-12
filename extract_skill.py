#!/usr/bin/env python3
"""
extract_skill.py
----------------
Read an OpenCode session from opencode.db, send conversation text to local
Ollama, and write extracted skills as SKILL.md files into the skills directory.

Usage:
    python extract_skill.py [session_id] [--check-only] [--force]

Modes:
    (no args)       Process the most recently updated session, with time-guard.
    session_id      Process a specific session, with time-guard.
    --check-only    Only print whether the session needs processing. No Ollama call.
    --force         Skip time-guard and reprocess even if already extracted.

Time-guard logic:
    A session needs processing when BOTH are true:
      1. session.time_updated > last_skill_commit_timestamp
         (session was active after skills were last committed)
      2. session_id NOT in extracted_sessions.json
         (this session has never been processed)
    This prevents re-running Ollama on every startup for old sessions.
"""

import sys
import io
# Force UTF-8 for console output (fixes Windows GBK encoding issues)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import sqlite3
import json
import re
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH          = r"C:\Users\Administrator\.local\share\opencode\opencode.db"
SKILLS_DIR       = r"C:\OpenSpace\openspace\skills"
EXTRACTED_LOG    = r"C:\Users\Administrator\.config\opencode\extracted_sessions.json"
OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "qwen2.5-coder:14b"
MAX_CHARS        = 12000
# ───────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a technical skill extractor for a developer knowledge base.

Given a developer conversation, extract REUSABLE technical skills as a JSON array.

Output ONLY a JSON array (with ```json fence), no other text:
```json
[
  {
    "name": "kebab-case-name",
    "description": "One sentence what this skill teaches",
    "tags": ["tag1", "tag2"],
    "content": "Full SKILL.md markdown with frontmatter:\\n---\\nname: <name>\\ndescription: <desc>\\ntags: [<tags>]\\n---\\n# Title\\n## Applicable Scenarios\\n## Tech Stack\\n## Implementation\\n```code example```\\n## Notes"
  }
]
```

Rules:
- Only extract genuinely reusable patterns (algorithms, design patterns, API usage, architecture)
- Skip trivial operations (simple git commands, basic file reads, one-off bug fixes)
- If no reusable skills: output ```json\n[]\n```

CONVERSATION:
"""


# ── Time helpers ───────────────────────────────────────────────────────────────

def get_last_skill_commit_ts() -> int:
    """Return the Unix timestamp (seconds) of the latest commit in SKILLS_DIR git log."""
    try:
        result = subprocess.run(
            ["git", "-C", SKILLS_DIR, "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=10
        )
        ts_str = result.stdout.strip()
        if ts_str:
            return int(ts_str)
    except Exception:
        pass
    return 0


def get_session_time_updated(db_path: str, session_id: str) -> int:
    """Return session.time_updated in milliseconds."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT time_updated FROM session WHERE id=?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def session_needs_processing(session_id: str, force: bool = False) -> tuple[bool, str]:
    """
    Returns (needs_processing, reason_string).

    Checks:
      1. Already in extracted_sessions.json → skip (unless --force)
      2. session.time_updated (ms) vs last skill commit timestamp (s)
         If session was last active BEFORE the last skill commit → skip
         (means it was processed in a previous run)
    """
    if force:
        return True, "force flag set"

    # Check extracted log
    log = load_extracted_log()
    if session_id in log:
        entry = log[session_id]
        return False, f"already extracted on {entry.get('extracted_at', '?')}"

    # Check time: session.time_updated (ms) vs last_skill_commit (s)
    session_ts_ms = get_session_time_updated(DB_PATH, session_id)
    last_commit_ts_s = get_last_skill_commit_ts()

    session_ts_s = session_ts_ms / 1000.0

    if session_ts_s <= last_commit_ts_s:
        t_session = datetime.fromtimestamp(session_ts_s).strftime("%Y-%m-%d %H:%M:%S")
        t_commit  = datetime.fromtimestamp(last_commit_ts_s).strftime("%Y-%m-%d %H:%M:%S")
        return False, f"session last active {t_session} is before last skill commit {t_commit}"

    t_session = datetime.fromtimestamp(session_ts_s).strftime("%Y-%m-%d %H:%M:%S")
    t_commit  = datetime.fromtimestamp(last_commit_ts_s).strftime("%Y-%m-%d %H:%M:%S")
    return True, f"session last active {t_session} > last skill commit {t_commit}"


# ── Extracted log ──────────────────────────────────────────────────────────────

def load_extracted_log() -> dict:
    if not os.path.exists(EXTRACTED_LOG):
        return {}
    try:
        with open(EXTRACTED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_extracted_log(log: dict):
    with open(EXTRACTED_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def mark_session_extracted(session_id: str, title: str, skills_written: int):
    log = load_extracted_log()
    log[session_id] = {
        "title": title,
        "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "skills_written": skills_written,
    }
    save_extracted_log(log)


# ── Session text ───────────────────────────────────────────────────────────────

def get_session_info(db_path: str, session_id: str | None) -> tuple[str, str, int]:
    """Return (session_id, title, time_updated_ms)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if session_id:
        cur.execute("SELECT id, title, time_updated FROM session WHERE id=?", (session_id,))
    else:
        cur.execute("SELECT id, title, time_updated FROM session ORDER BY time_updated DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        raise ValueError("No session found")
    return row[0], row[1] or "untitled", row[2] or 0


def get_conversation_text(db_path: str, session_id: str) -> str:
    """Return conversation as plain text, truncated to MAX_CHARS."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.data, m.data
        FROM part p
        JOIN message m ON p.message_id = m.id
        WHERE p.session_id = ?
        ORDER BY p.time_created ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()

    lines = []
    for part_raw, msg_raw in rows:
        try:
            part = json.loads(part_raw)
            msg  = json.loads(msg_raw)
        except Exception:
            continue
        if part.get("type") != "text":
            continue
        text = part.get("text", "").strip()
        if not text:
            continue
        role = msg.get("role", "unknown")
        lines.append(f"[{role}]: {text}")

    conversation = "\n\n".join(lines)
    if len(conversation) > MAX_CHARS:
        conversation = conversation[:MAX_CHARS] + "\n...[truncated]"
    return conversation


# ── Ollama ─────────────────────────────────────────────────────────────────────

def ask_ollama(conversation: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + conversation,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 4096},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e


def parse_skills(raw: str) -> list[dict]:
    # 1. Try ```json ... ``` fence
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        # 2. Bare [...] block
        bare = re.search(r"\[.*\]", raw, re.DOTALL)
        if not bare:
            return []
        candidate = bare.group()
    try:
        skills = json.loads(candidate)
        if isinstance(skills, list):
            return skills
    except json.JSONDecodeError as e:
        print(f"[extract_skill] JSON parse error: {e}")
    return []


def write_skill(skill: dict, skills_dir: str) -> str | None:
    name    = skill.get("name", "").strip()
    content = skill.get("content", "").strip()
    if not name or not content:
        return None
    name = re.sub(r"[^a-z0-9\-]", "-", name.lower()).strip("-")
    skill_dir  = os.path.join(skills_dir, name)
    skill_file = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_file):
        print(f"  [skip] {name} already exists")
        return None
    os.makedirs(skill_dir, exist_ok=True)
    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [written] {skill_file}")
    return skill_file


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    check_only = "--check-only" in args
    force      = "--force" in args
    session_id_arg = next((a for a in args if not a.startswith("--")), None)

    # 1. Resolve session
    try:
        sid, title, time_updated_ms = get_session_info(DB_PATH, session_id_arg)
    except ValueError as e:
        print(f"[error] {e}")
        sys.exit(1)

    t_updated = datetime.fromtimestamp(time_updated_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[extract_skill] Session : {sid}")
    print(f"[extract_skill] Title   : {title}")
    print(f"[extract_skill] Updated : {t_updated}")

    # 2. Time-guard check
    needs, reason = session_needs_processing(sid, force=force)
    print(f"[extract_skill] Status  : {'NEEDS PROCESSING' if needs else 'SKIP'} — {reason}")

    if check_only or not needs:
        sys.exit(0 if not needs else 0)

    # 3. Get conversation text
    conversation = get_conversation_text(DB_PATH, sid)
    if not conversation.strip():
        print("[extract_skill] No conversation text found.")
        mark_session_extracted(sid, title, 0)
        sys.exit(0)

    print(f"[extract_skill] Conv len: {len(conversation)} chars")
    print(f"[extract_skill] Sending to Ollama ({OLLAMA_MODEL})...")

    # 4. Ask Ollama
    try:
        raw_response = ask_ollama(conversation)
    except RuntimeError as e:
        print(f"[error] {e}")
        sys.exit(1)

    print(f"[extract_skill] Response: {len(raw_response)} chars")

    # 5. Parse and write
    skills = parse_skills(raw_response)
    if not skills:
        print("[extract_skill] No reusable skills found in this session.")
        mark_session_extracted(sid, title, 0)
        sys.exit(0)

    print(f"[extract_skill] Found {len(skills)} skill(s):")
    written = []
    for skill in skills:
        path = write_skill(skill, SKILLS_DIR)
        if path:
            written.append(path)

    # 6. Record as processed (regardless of how many were written)
    mark_session_extracted(sid, title, len(written))

    if written:
        print(f"\n[extract_skill] Written {len(written)} new skill(s). Auto-push watcher will sync.")
    else:
        print("[extract_skill] No new files written (skills may already exist).")


if __name__ == "__main__":
    main()
