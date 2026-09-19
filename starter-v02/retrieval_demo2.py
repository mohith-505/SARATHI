"""Harder, more realistic corpus: many semantically near-identical chunks that
differ only in an exact identifier. This is what real technical notes look like,
and it is where dense-only retrieval actually breaks."""
import sqlite3, re, numpy as np, random
random.seed(0)

CORPUS = []
# 1. Near-duplicate error notes: same MEANING, different exact identifier.
for code, cause in [("404","the endpoint path was wrong"),
                    ("429","the provider rate limit was hit"),
                    ("500","the upstream server crashed"),
                    ("502","the gateway could not reach the backend"),
                    ("503","the service was temporarily unavailable")]:
    CORPUS.append((f"http{code}",
        f"The request failed with HTTP status {code}. Investigation showed {cause}. "
        f"Retrying the same request did not help and the fix was on the server side."))
for errno, what in [("28","No space left on device"),("13","Permission denied"),
                    ("24","Too many open files"),("32","Broken pipe")]:
    CORPUS.append((f"errno{errno}",
        f"Saving the checkpoint raised OSError with errno {errno}, {what}. "
        f"The training loop aborted and the partial file had to be removed."))
for cuda, what in [("700","an illegal memory access was encountered"),
                   ("2","out of memory"),("999","unknown error"),
                   ("77","an illegal address during kernel execution")]:
    CORPUS.append((f"cuda{cuda}",
        f"The process aborted with CUDA error {cuda}, {what}. "
        f"The GPU had to be reset before the next run would start."))
# 2. Conceptual chunks (paraphrase-friendly, no distinctive tokens)
CORPUS += [
 ("vram","Weights at four bit quantisation take roughly half a gigabyte per billion parameters, so a mid sized model needs about four gigabytes just to hold them."),
 ("kv","The attention cache grows in proportion to how much text you keep in the window, which is why long conversations eat memory that the weights did not."),
 ("bandwidth","Generation speed is limited by how fast the card can read its own memory, not by arithmetic throughput, which is why a smaller model feels faster."),
 ("offload","Once the layers stop fitting on the card they spill into system memory and throughput collapses, because the link to main memory is far slower."),
 ("precision","Handing the model twenty loosely related passages produces worse answers than handing it three tightly relevant ones, because attention gets diluted."),
 ("rerank","Scoring the question and the passage together is slower for each pair but much sharper than comparing two independently computed vectors."),
 ("chunk","Splitting on document structure instead of fixed character counts keeps ideas intact, and carrying the section heading into each piece helps a lot."),
 ("trust","Anything pulled off the open web has to be treated as hostile input and must never override something the person told you directly."),
 ("supersede","When newer information disagrees with older information, close the old record with an end date and point it at the replacement instead of deleting it."),
 ("taint","After hostile text lands in the window, the permissions available for the rest of that turn are reduced so an embedded instruction cannot reach a shell."),
 ("stall","When the assistant keeps taking the same action over and over, make it explain why the last attempt did not work before it is allowed to try again."),
 ("sandbox","Untrusted programs run inside an isolated container with networking switched off and the root filesystem mounted read only."),
]
# 3. Filler distractors so top-k actually has to discriminate
for i in range(60):
    CORPUS.append((f"filler{i}",
      f"General note {i} about configuration, logging, deployment and routine maintenance "
      f"of the system, covering setup steps and operational details of component {i}."))

ids  = [c[0] for c in CORPUS]
docs = [c[1] for c in CORPUS]
byid = dict(CORPUS)

QUERIES = [
 ("CUDA error 700",                                   {"cuda700"}, "exact-id"),
 ("errno 28",                                         {"errno28"}, "exact-id"),
 ("HTTP 429",                                         {"http429"}, "exact-id"),
 ("what does HTTP 502 mean",                          {"http502"}, "exact-id"),
 ("OSError errno 24",                                 {"errno24"}, "exact-id"),
 ("how much gpu memory do the weights need",          {"vram"},    "paraphrase"),
 ("why does a long chat use more memory",             {"kv"},      "paraphrase"),
 ("why is generation slow even on a fast gpu",        {"bandwidth","offload"}, "paraphrase"),
 ("should I put more or fewer passages in the prompt",{"precision"},"paraphrase"),
 ("how do I stop it doing the same thing repeatedly", {"stall"},   "paraphrase"),
 ("can I let a web page tell the assistant what to do",{"trust","taint"},"paraphrase"),
 ("what to do when new info contradicts old info",    {"supersede"},"paraphrase"),
]

# ---------- sparse: FTS5 BM25 ----------
db = sqlite3.connect(":memory:")
db.execute("CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED, text)")
db.executemany("INSERT INTO fts(id,text) VALUES(?,?)", CORPUS)
STOP = set("the a an of to in is it and or for with that this what how do i my does on".split())
def sparse(q,k=10):
    terms=[t for t in re.findall(r"[A-Za-z0-9_]+",q) if len(t)>1 and t.lower() not in STOP]
    if not terms: return []
    try:
        rows=db.execute("SELECT id FROM fts WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?",
                        (" OR ".join(terms),k)).fetchall()
    except sqlite3.OperationalError: return []
    return [r[0] for r in rows]

# ---------- dense: LSA, with the realistic weakness of real bi-encoders ----------
# Real embedding models pool subword tokens into one vector; rare exact strings
# like "700" or "28" get diluted rather than preserved. Emulate by excluding
# pure-numeric tokens from the dense representation.
def toks(t, dense_mode):
    ws = re.findall(r"[a-z0-9]+", t.lower())
    return [w for w in ws if not (dense_mode and w.isdigit())]
vocab = sorted({w for d in docs for w in toks(d,True)})
vi={w:i for i,w in enumerate(vocab)}
def bow(t):
    v=np.zeros(len(vocab),dtype=np.float32)
    for w in toks(t,True):
        if w in vi: v[vi[w]]+=1
    return v
X=np.stack([bow(d) for d in docs]); dfr=(X>0).sum(0)
idf=np.log((1+len(docs))/(1+dfr))+1; Xt=X*idf
U,S,Vt=np.linalg.svd(Xt,full_matrices=False); DIM=40
proj=Vt[:DIM].T; E=Xt@proj; E/= (np.linalg.norm(E,axis=1,keepdims=True)+1e-9)
def dense(q,k=10):
    v=(bow(q)*idf)@proj; n=np.linalg.norm(v)
    if n<1e-9: return []
    return [ids[i] for i in np.argsort(-(E@(v/n)))[:k]]

def rrf(lists,k=10,c=60):
    sc={}
    for l in lists:
        for r,d in enumerate(l): sc[d]=sc.get(d,0)+1/(c+r+1)
    return [d for d,_ in sorted(sc.items(),key=lambda x:-x[1])[:k]]

# reranker: exact-match-aware cross scoring (a real cross-encoder sees both together)
allw=set(vocab)|{w for d in docs for w in re.findall(r"[a-z0-9]+",d.lower())}
widf={}
for w in allw:
    c=sum(1 for d in docs if w in re.findall(r"[a-z0-9]+",d.lower()))
    widf[w]=np.log((1+len(docs))/(1+c))+1
def rerank(q,cand,k=3):
    qt=set(w for w in re.findall(r"[a-z0-9]+",q.lower()) if w not in STOP)
    def sc(d):
        dt=set(re.findall(r"[a-z0-9]+",byid[d].lower()))
        return sum(widf.get(w,1) for w in qt&dt)
    return sorted(cand,key=sc,reverse=True)[:k]

def ev(fn,k,label):
    rec=prec=mrr=0.0; bykind={}
    for q,gold,kind in QUERIES:
        got=fn(q)[:k]; hits=[d for d in got if d in gold]
        r=len(hits)/len(gold); rec+=r; prec+=len(hits)/max(len(got),1)
        m=0
        for i,d in enumerate(got):
            if d in gold: m=1/(i+1); break
        mrr+=m
        bykind.setdefault(kind,[]).append(r)
    n=len(QUERIES)
    ex=np.mean(bykind['exact-id']); pa=np.mean(bykind['paraphrase'])
    print(f"{label:<24} recall@{k}={rec/n:.2f}  prec@{k}={prec/n:.2f}  MRR={mrr/n:.2f}"
          f"   | exact-id {ex:.2f}  paraphrase {pa:.2f}")

print(f"corpus: {len(CORPUS)} chunks, {len(QUERIES)} gold-labelled queries\n")
print("=== top-10: naive RAG, everything dumped into context ===")
ev(lambda q: dense(q,10),10,"dense only")
ev(lambda q: sparse(q,10),10,"BM25 only")
ev(lambda q: rrf([dense(q,10),sparse(q,10)]),10,"hybrid RRF")
print("\n=== top-3: what you should actually inject ===")
ev(lambda q: dense(q,3),3,"dense only")
ev(lambda q: sparse(q,3),3,"BM25 only")
ev(lambda q: rrf([dense(q,10),sparse(q,10)],3),3,"hybrid RRF")
ev(lambda q: rerank(q,rrf([dense(q,20),sparse(q,20)],20),3),3,"hybrid RRF + rerank")
print("\n=== per-query at top-3 ===")
print(f"  {'dense':>5} {'bm25':>5} {'hyb+rr':>7}   query")
for q,gold,kind in QUERIES:
    d="Y" if set(dense(q,3))&gold else "."
    s="Y" if set(sparse(q,3))&gold else "."
    h="Y" if set(rerank(q,rrf([dense(q,20),sparse(q,20)],20),3))&gold else "."
    print(f"  {d:>5} {s:>5} {h:>7}   {q}")
