import os
from pathlib import Path
from pydantic import BaseModel, Field
from sarathi.core.types import Context, Tier, Trust
from sarathi.security.paths import PathPolicy

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="Path to the file to read")

class ReadFileTool:
    name = "read_file"
    description = "Read the contents of a file"
    tier = Tier.T0
    output_trust = Trust.TRUSTED
    schema = ReadFileArgs

    def __init__(self, policy: PathPolicy):
        self.policy = policy

    async def run(self, args: ReadFileArgs, ctx: Context) -> str:
        p = self.policy.check(args.path, mode="read")
        if not p.is_file():
            raise FileNotFoundError(f"Not a file: {p}")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()


class ListDirArgs(BaseModel):
    path: str = Field(..., description="Directory to list")

class ListDirTool:
    name = "list_dir"
    description = "List contents of a directory"
    tier = Tier.T0
    output_trust = Trust.TRUSTED
    schema = ListDirArgs

    def __init__(self, policy: PathPolicy):
        self.policy = policy

    async def run(self, args: ListDirArgs, ctx: Context) -> str:
        p = self.policy.check(args.path, mode="read")
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        entries = []
        for entry in p.iterdir():
            t = "d" if entry.is_dir() else "f"
            entries.append(f"[{t}] {entry.name}")
        return "\n".join(entries)


class SearchFilesArgs(BaseModel):
    query: str = Field(..., description="String to search for in files")
    path: str = Field(default="workspace", description="Directory to search in")

class SearchFilesTool:
    name = "search_files"
    description = "Search for a string in all files within a directory"
    tier = Tier.T0
    output_trust = Trust.TRUSTED
    schema = SearchFilesArgs

    def __init__(self, policy: PathPolicy):
        self.policy = policy

    async def run(self, args: SearchFilesArgs, ctx: Context) -> str:
        root = self.policy.check(args.path, mode="read")
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        
        results = []
        # Simple recursive search
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            # Double check policy just in case (e.g. symlinks)
            try:
                self.policy.check(str(p), mode="read")
            except Exception:
                continue
            
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if args.query in line:
                            results.append(f"{p.relative_to(root)}:{i}: {line.strip()}")
            except UnicodeDecodeError:
                pass # skip binary files
                
        if not results:
            return "No matches found."
        return "\n".join(results)
