"""
MVU Application Controller — the TUI main loop.

Manages the screen stack, event loop, and terminal engine lifecycle.
"""

from __future__ import annotations

from ..core.lifecycle import ApplicationContext
from .engine import TerminalEngine, Key, KeyEvent
from .views import (
    HomeView, ConversationBrowserView, ConversationDataView, 
    RecoveryWizardView, MergeWizardView, HelpOverlay,
    WorkspaceBrowserView, StorageBrowserView,
)


class App:
    """
    The main MVU application controller.

    Entry point for the full-screen TUI experience.
    """

    def __init__(self, ctx: ApplicationContext) -> None:
        self.ctx = ctx
        self.engine = TerminalEngine()
        self.screen_stack: list[object] = []

    def run(self) -> None:
        # Register cleanup with lifecycle manager
        self.ctx.register_tui_cleanup(self.engine.exit_fullscreen)
        self.ctx.perform_preflight_checks()
        self.engine.enter_fullscreen()

        try:
            home = HomeView(self.ctx.db_path)
            self._push(home)

            while self.screen_stack:
                cols, rows = self.engine.get_size()
                current = self.screen_stack[-1]
                frame = current.view(cols, rows)
                self.engine.paint(frame)

                key = self.engine.getch()
                action = current.update(key)

                if action is None:
                    continue
                elif action == "back":
                    self._pop()
                elif action == "quit":
                    break
                elif action.startswith("push:"):
                    screen = self._create_screen(action)
                    if screen:
                        self._push(screen)
        finally:
            self.engine.exit_fullscreen()

    def _push(self, screen: object) -> None:
        self.screen_stack.append(screen)
        if hasattr(screen, 'on_enter'):
            screen.on_enter()

    def _pop(self) -> None:
        if self.screen_stack:
            self.screen_stack.pop()
        if self.screen_stack and hasattr(self.screen_stack[-1], 'on_enter'):
            self.screen_stack[-1].on_enter()

    def _create_screen(self, action_string: str) -> object | None:
        parts = action_string.split(":")
        name = parts[1]
        
        if name == "browse" and len(parts) >= 3:
            db_path = ":".join(parts[2:])
            return ConversationBrowserView(db_path)
        elif name == "view" and len(parts) >= 4:
            db_path = ":".join(parts[2:-1])
            uuid = parts[-1]
            return ConversationDataView(db_path, uuid)
        elif name == "recover":
            return RecoveryWizardView(self.ctx.db_path)
        elif name == "merge":
            source_db = ":".join(parts[2:]) if len(parts) >= 3 else ""
            return MergeWizardView(self.ctx.db_path, source_db)
        elif name == "workspaces" and len(parts) >= 3:
            db_path = ":".join(parts[2:])
            return WorkspaceBrowserView(db_path)
        elif name == "storage":
            import os
            storage_dir = os.path.dirname(self.ctx.db_path)
            return StorageBrowserView(storage_dir)
        elif name == "help":
            return HelpOverlay()
        return None
