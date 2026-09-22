# Memory

V0.1 keeps a bounded in-memory conversation and saves the visible transcript plus model usage to local SQLite for diagnostics. It does not reload old sessions into a new chat, and it is not semantic or long-term memory.

V0.6 will separate short-term context, explicitly approved long-term facts, episodic task history, and user-provided documents. It will support `Remember this`, `Forget this`, `What do you remember about me?`, and deletion controls. Nothing should be promoted to long-term memory without a user-visible rule and provenance.
