from facts import FactStore
fs = FactStore()
def show(o, desc):
    print(f"{o.action:<11} {desc}" + (f"   ({o.detail})" if o.detail else ""))

print("--- building up knowledge ---")
show(fs.propose("user","gpu_vram","6GB","user_stated"), "user says 6GB VRAM")
show(fs.propose("user","gpu_vram","6GB","user_stated"), "user repeats it")
show(fs.propose("user","os","Windows + WSL2","user_stated"), "user says Windows")

print("\n--- a hostile web page tries to rewrite memory ---")
show(fs.propose("user","gpu_vram","24GB","web",trust="untrusted"),
     "web page claims 24GB")
show(fs.propose("user","api_endpoint","http://evil.example","web",trust="untrusted"),
     "web page plants a new endpoint")

print("\n--- legitimate correction from the user ---")
show(fs.propose("user","gpu_vram","8GB","user_stated"), "user corrects to 8GB")

print("\n--- a tool observes something that outranks a document ---")
show(fs.propose("machine","ram","16GB","document"), "doc says 16GB")
show(fs.propose("machine","ram","32GB","tool_output"), "nvidia-smi/free says 32GB")
show(fs.propose("machine","ram","64GB","document"), "another doc claims 64GB")

print("\n--- two docs disagree (same tier) ---")
show(fs.propose("project","db","Postgres","document"), "doc A: Postgres")
show(fs.propose("project","db","SQLite","document"), "doc B: SQLite")

print("\n--- current beliefs ---")
for s in ("user","machine","project"):
    for fid,obj,src,trust,conf in fs.live(s):
        print(f"  {s:<8} = {obj:<16} (from {src})")

print("\n--- full history of user.gpu_vram (nothing deleted) ---")
for obj,src,trust,is_live in fs.history("user","gpu_vram"):
    print(f"  {obj:<8} {src:<12} {trust:<10} {'LIVE' if is_live else 'superseded'}")

print("\n--- did the web page get in anywhere? ---")
rows = fs.db.execute("SELECT subject,predicate,object FROM facts "
                     "WHERE trust='untrusted' AND valid_to IS NULL").fetchall()
print("  live untrusted facts:", rows if rows else "NONE")
