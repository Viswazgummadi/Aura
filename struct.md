# 📁 Project Structure

```bash
aura/
├── agent_graph.png
├── credentials.json
├── gmail_history.json
├── gmail_history_tracker.py
├── main.py
├── models.json
├── notes.json
├── README.md
├── requirements.txt
├── struct.md
├── tasks.json
├── token.json
├── venv/
├── __pycache__/
│   └── (compiled cache files)
└── src/
    ├── __init__.py
    ├── __pycache__/
    │   └── __init__.cpython-312.pyc
    ├── agent/
    │   ├── __init__.py
    │   ├── core.py
    │   ├── graph.py
    │   ├── invoker.py
    │   ├── __pycache__/
    │   │   ├── core.cpython-312.pyc
    │   │   ├── graph.cpython-312.pyc
    │   │   ├── invoker.cpython-312.pyc
    │   │   └── __init__.cpython-312.pyc
    │   └── tools/
    │       ├── __init__.py
    │       ├── calendar.py
    │       ├── gmail.py
    │       ├── gmail_watcher.py
    │       ├── notes.py
    │       ├── tasks.py
    │       ├── __pycache__/
    │       │   ├── calendar.cpython-312.pyc
    │       │   ├── gmail.cpython-312.pyc
    │       │   ├── gmail_watcher.cpython-312.pyc
    │       │   ├── notes.cpython-312.pyc
    │       │   ├── tasks.cpython-312.pyc
    │       │   └── __init__.cpython-312.pyc
    ├── bot/
    │   ├── __init__.py
    │   ├── client.py
    │   ├── webserver.py
    │   ├── __pycache__/
    │   │   ├── client.cpython-312.pyc
    │   │   ├── webserver.cpython-312.pyc
    │   │   └── __init__.cpython-312.pyc
    │   ├── cogs/
    │   │   ├── auth_cog.py
    │   │   ├── model_management_cog.py
    │   │   ├── notes_cog.py
    │   │   ├── tasks_cog.py
    │   │   ├── tools_cog.py
    │   │   ├── __pycache__/
    │   │   │   ├── auth_cog.cpython-312.pyc
    │   │   │   ├── model_management_cog.cpython-312.pyc
    │   │   │   ├── notes_cog.cpython-312.pyc
    │   │   │   ├── tasks_cog.cpython-312.pyc
    │   │   │   └── tools_cog.cpython-312.pyc
    │   └── ui/
    │       ├── event_ui.py
    │       ├── mail_ui.py
    │       └── __pycache__/
    │           ├── event_ui.cpython-312.pyc
    │           └── mail_ui.cpython-312.pyc
    └── core/
        ├── __init__.py
        ├── config.py
        ├── gcp_auth.py
        ├── model_manager.py
        └── __pycache__/
            ├── config.cpython-312.pyc
            ├── gcp_auth.cpython-312.pyc
            ├── model_manager.cpython-312.pyc
            └── __init__.cpython-312.pyc

```

