"""
Enables ``python -m`` and ``zipapp`` execution.

When this file exists at the package root, both of these work:
  - ``python -m antigravity_database_manager``  (from parent directory)
  - ``python AgmerciumRecovery.pyz``   (zipapp archive)
"""

from antigravity_database_manager import main

if __name__ == "__main__":
    main()
