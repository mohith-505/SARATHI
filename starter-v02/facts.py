"""Semantic memory with provenance, supersession and trust precedence.

Two rules do most of the work:
  1. Nothing is ever deleted. Contradiction closes a row, it does not remove it.
  2. An untrusted source can never supersede a trusted fact. This is the
     memory-poisoning defence and it is four lines of code.
"""
from __future__ import annotations
import sqlite3, time
from dataclasses import dataclass

# Higher wins. A web page cannot overwrite something you said.
PRECEDENCE = {"user_stated": 4, "tool_output": 3, "document": 2, "web": 1}

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL,
  confidence REAL DEFAULT 0.5,
  source_type TEXT NOT NULL, source_ref TEXT,
  trust TEXT NOT NULL DEFAULT 'trusted',
  valid_from REAL NOT NULL, valid_to REAL,
  superseded_by INTEGER REFERENCES facts(id),
  contested INTEGER DEFAULT 0,
  created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_live ON facts(subject,predicate) WHERE valid_to IS NULL;
"""

@dataclass
class Outcome:
    action: str      # stored | duplicate | superseded | rejected | contested
    fact_id: int | None
    detail: str = ""


class FactStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def live(self, subject, predicate=None):
        q = "SELECT id,object,source_type,trust,confidence FROM facts WHERE subject=? AND valid_to IS NULL"
        a = [subject]
        if predicate: q += " AND predicate=?"; a.append(predicate)
        return self.db.execute(q, a).fetchall()

    def propose(self, subject, predicate, obj, source_type, trust="trusted",
                confidence=0.6, source_ref=None) -> Outcome:
        now = time.time()

        # ---- FIX 1: untrusted sources cannot create LIVE facts at all. ----
        # Blocking only overwrites leaves the hole open: a hostile page simply
        # asserts a subject/predicate you have no prior belief about, and it
        # lands as fact. Quarantine instead; it stays retrievable, clearly
        # labelled, and never speaks with your own authority.
        if trust == "untrusted":
            existing = self.live(subject, predicate)
            nid = self._insert(subject, predicate, obj, min(confidence, 0.3),
                               source_type, trust, source_ref, now)
            self.db.execute("UPDATE facts SET valid_to=? WHERE id=?", (now, nid))
            self.db.commit()
            reason = ("cannot override trusted belief" if existing
                      else "untrusted source cannot assert new facts")
            return Outcome("quarantined", nid, reason)

        existing = self.live(subject, predicate)

        for fid, old_obj, old_src, old_trust, old_conf in existing:
            if old_obj.strip().lower() == obj.strip().lower():
                return Outcome("duplicate", fid, "already known")

            # ---- FIX 2: an explicit user correction is a correction, not a
            # dispute. Only flag "contested" when two non-user sources of equal
            # standing disagree - that is a real ambiguity you should see.
            if source_type == "user_stated" and old_src == "user_stated":
                nid = self._insert(subject,predicate,obj,confidence,source_type,
                                   trust,source_ref,now)
                self.db.execute(
                    "UPDATE facts SET valid_to=?, superseded_by=? WHERE id=?",(now,nid,fid))
                self.db.commit()
                return Outcome("corrected", nid, "user corrected their own statement")

            new_p, old_p = PRECEDENCE.get(source_type,0), PRECEDENCE.get(old_src,0)
            if new_p > old_p:
                nid = self._insert(subject,predicate,obj,confidence,source_type,
                                   trust,source_ref,now)
                self.db.execute(
                    "UPDATE facts SET valid_to=?, superseded_by=? WHERE id=?", (now,nid,fid))
                self.db.commit()
                return Outcome("superseded", nid, f"{old_src} -> {source_type}")
            if new_p < old_p:
                return Outcome("rejected", fid,
                    f"{source_type} outranked by existing {old_src}")
            # Equal precedence + different value: recency wins, but flag it.
            nid = self._insert(subject,predicate,obj,confidence,source_type,
                               trust,source_ref,now)
            self.db.execute("UPDATE facts SET valid_to=?, superseded_by=? WHERE id=?",
                            (now,nid,fid))
            self.db.execute("UPDATE facts SET contested=1 WHERE id=?", (nid,))
            self.db.commit()
            return Outcome("contested", nid, "same-tier disagreement; newer kept, flagged")

        nid = self._insert(subject,predicate,obj,confidence,source_type,trust,source_ref,now)
        self.db.commit()
        return Outcome("stored", nid)

    def _insert(self,s,p,o,c,src,trust,ref,now):
        cur=self.db.execute(
          "INSERT INTO facts(subject,predicate,object,confidence,source_type,source_ref,"
          "trust,valid_from,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
          (s,p,o,c,src,ref,trust,now,now))
        return cur.lastrowid

    def history(self, subject, predicate):
        return self.db.execute(
          "SELECT object,source_type,trust,valid_to IS NULL FROM facts "
          "WHERE subject=? AND predicate=? ORDER BY id",(subject,predicate)).fetchall()
