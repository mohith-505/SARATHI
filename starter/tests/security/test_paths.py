import os, tempfile
from pathlib import Path
import sys; sys.path.insert(0, "src")
from sarathi.security.paths import PathPolicy, PolicyDenied

def build(tmp):
    ws = Path(tmp)/"workspace"; ws.mkdir()
    secret = Path(tmp)/"secrets"; secret.mkdir()
    (secret/"id_rsa").write_text("PRIVATE")
    (ws/"ok.txt").write_text("hello")
    return ws, secret, PathPolicy(
        allow_read=[str(ws)], allow_write=[str(ws)],
        deny_roots=[str(secret)], deny_globs=["*.pem", ".env", "id_*"],
    )

def run():
    tmp = tempfile.mkdtemp()
    ws, secret, pol = build(tmp)
    results = []

    def expect(desc, fn, should_pass):
        try:
            fn(); ok = True; err = ""
        except PolicyDenied as e:
            ok = False; err = str(e)
        passed = (ok == should_pass)
        results.append((passed, desc, err))

    expect("normal read inside workspace", lambda: pol.check(str(ws/"ok.txt")), True)
    expect("write inside workspace", lambda: pol.check(str(ws/"new.txt"), "write"), True)
    expect("read outside any root", lambda: pol.check("/etc/passwd"), False)
    expect("traversal ../../etc/passwd", lambda: pol.check(str(ws/".."/".."/"etc"/"passwd")), False)
    expect("denied dir direct", lambda: pol.check(str(secret/"id_rsa")), False)
    expect("denied glob id_*", lambda: pol.check(str(ws/"id_rsa")), False)
    expect("denied glob .env", lambda: pol.check(str(ws/".env")), False)
    expect("denied glob *.pem", lambda: pol.check(str(ws/"cert.pem")), False)

    # symlink escape: workspace/link -> secrets
    link = ws/"link"
    os.symlink(str(secret), str(link))
    expect("symlink escape to denied dir", lambda: pol.check(str(link/"id_rsa")), False)

    # symlink to an allowed-looking but outside path
    outside = Path(tmp)/"outside"; outside.mkdir(); (outside/"x.txt").write_text("x")
    os.symlink(str(outside), str(ws/"out"))
    expect("symlink escape outside roots", lambda: pol.check(str(ws/"out"/"x.txt")), False)

    for passed, desc, err in results:
        print(("PASS " if passed else "FAIL ") + desc + ("  <- " + err if err and not passed else ""))
    print(f"\n{sum(p for p,_,_ in results)}/{len(results)} passed")

run()
