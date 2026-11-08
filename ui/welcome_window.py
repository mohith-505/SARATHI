"""SARATHI — Native Graphical Welcome Window.

Loads and displays the authentic 1024x322 original reference artwork directly.
Brings itself to the front of the desktop when launched from dev.ps1,
and transitions smoothly into the working SARATHI interface.
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
import webbrowser
from pathlib import Path


class SarathiWelcomeWindow:
    def __init__(
        self,
        asset_path: str | Path | None = None,
        auto_transition: bool = True,
        timeout_seconds: float = 4.0,
        open_url: str = "http://127.0.0.1:5173",
    ) -> None:
        self.auto_transition = auto_transition
        self.timeout_seconds = timeout_seconds
        self.open_url = open_url

        if asset_path:
            self.asset_path = Path(asset_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent
            candidates = [
                base_dir / "assets" / "branding" / "sarathi-welcome.png",
                base_dir / "frontend" / "public" / "assets" / "branding" / "sarathi-welcome.png",
                base_dir / "assets" / "branding" / "sarathi_welcome_reference.png",
            ]
            self.asset_path = next((p for p in candidates if p.exists()), candidates[0])

        self.root = tk.Tk()
        self.root.title("SARATHI ~ Your AI Companion")
        self.root.configure(bg="#020609")

        # Dimensions: exactly matches 1024x322 original reference
        self.width = 1024
        self.height = 322

        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, (screen_w - self.width) // 2)
        pos_y = max(0, (screen_h - self.height) // 2)
        self.root.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")
        self.root.overrideredirect(True)  # Frameless to match reference artwork titlebar

        # Ensure the window immediately appears in the foreground
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        # Lower topmost priority after 1200ms so other windows can be focused normally
        self.root.after(1200, self._relax_topmost)

        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()
        self._bind_events()

        if self.auto_transition and self.timeout_seconds > 0:
            delay_ms = int(self.timeout_seconds * 1000)
            self.root.after(delay_ms, lambda: self.close_and_transition(open_browser=True))

    def _relax_topmost(self) -> None:
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="#020609",
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img_tk = None
        if self.asset_path.exists():
            try:
                self.img_tk = tk.PhotoImage(file=str(self.asset_path))
                self.canvas.create_image(0, 0, image=self.img_tk, anchor=tk.NW)
            except Exception as e:
                print(f"[Warning] Failed to load image {self.asset_path}: {e}", file=sys.stderr)

        if not self.img_tk:
            # Fallback error display
            self.canvas.create_text(
                self.width // 2,
                self.height // 2 - 20,
                text="SARATHI ~ Asset Missing",
                fill="#ff3355",
                font=("Segoe UI", 16, "bold"),
            )
            self.canvas.create_text(
                self.width // 2,
                self.height // 2 + 15,
                text=f"Please verify '{self.asset_path}' exists.\nClick anywhere to proceed to SARATHI HUD.",
                fill="#d9e3e8",
                font=("Segoe UI", 10),
            )

    def _bind_events(self) -> None:
        # Window drag via canvas top region (titlebar region)
        self.canvas.bind("<ButtonPress-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        # Keyboard launch
        self.root.bind("<Return>", lambda e: self.close_and_transition(open_browser=True))
        self.root.bind("<space>", lambda e: self.close_and_transition(open_browser=True))
        self.root.bind("<Escape>", lambda e: self.close_and_transition(open_browser=True))

    def _on_click(self, event: tk.Event) -> None:
        # Check if clicked on close button region (top right x > 985, y < 35)
        if event.x > 985 and event.y < 35:
            self.close_and_transition(open_browser=False)
            return

        # Check if clicked on min button region (x: 915..945, y < 35)
        if 915 <= event.x <= 945 and event.y < 35:
            self.close_and_transition(open_browser=True)
            return

        # Record for dragging
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        # If clicked anywhere else, transition into SARATHI
        if event.y > 35:
            self.close_and_transition(open_browser=True)

    def _on_drag(self, event: tk.Event) -> None:
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def close_and_transition(self, open_browser: bool = True) -> None:
        if open_browser and self.open_url:
            try:
                webbrowser.open(self.open_url)
            except Exception as e:
                print(f"[Info] Opening browser at {self.open_url}: {e}")
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="SARATHI — Original Welcome Window")
    parser.add_argument("--asset", type=str, default=None, help="Path to original artwork")
    parser.add_argument("--no-auto-transition", action="store_true", help="Disable auto-transition")
    parser.add_argument("--timeout", type=float, default=4.0, help="Timeout before auto-transition")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:5173", help="SARATHI HUD URL")
    args = parser.parse_args()

    app = SarathiWelcomeWindow(
        asset_path=args.asset,
        auto_transition=not args.no_auto_transition,
        timeout_seconds=args.timeout,
        open_url=args.url,
    )
    app.run()


if __name__ == "__main__":
    main()
