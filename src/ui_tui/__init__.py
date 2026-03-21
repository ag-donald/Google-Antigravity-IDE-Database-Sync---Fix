"""
TUI — Terminal User Interface for Antigravity Database Manager.

Enterprise-grade component-based TUI framework built entirely with
Python standard library (zero external dependencies).

Architecture:
  - engine.py      — Terminal I/O with double-buffered rendering
  - theme.py       — Semantic color palette and style system
  - events.py      — Typed event bus, key bindings, focus management
  - core.py        — Component base class and layout engine
  - components.py  — Production component library (20+ components)
  - animation.py   — Easing functions and animation manager
  - views.py       — MVU screen definitions using components
  - app.py         — Application controller with adaptive event loop
"""
