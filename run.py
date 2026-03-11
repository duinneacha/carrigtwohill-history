#!/usr/bin/env python3
"""
Carrigtwohill Historical Research Repository
============================================
Usage:
  python run.py          — start web interface (http://localhost:5050)
  python run.py collect  — run collector only (no web server)
  python run.py both     — collect first, then start web server
"""

import sys
import os

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(__file__))

import db

def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "web"

    if mode == "--purge-blocked":
        db.init_db()
        removed = db.purge_blocked_articles()
        print(f"Purged {removed} article(s) from blocked domains.")
        return

    if mode in ("collect", "both"):
        print("Running content collector …")
        import collect
        collect.run_all(verbose=True)

    if mode in ("web", "both", ""):
        import app as flask_app
        db.init_db()
        flask_app.start_scheduler()
        print("━" * 60)
        print("  🏰 Carrigtwohill Historical Research Repository")
        print("  🌐 Open your browser at: http://localhost:5050")
        print("  ⏹  Press Ctrl+C to stop")
        print("━" * 60)
        flask_app.app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)

    elif mode == "collect":
        pass  # already done above

    else:
        print(f"Unknown mode '{mode}'. Use: collect | web | both")


if __name__ == "__main__":
    main()
