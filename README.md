# NEXUS-Analytics
🚀 NEXUS Analytics
NEXUS Analytics is a self-hosted, zero-trust analytics and network diagnostics platform designed for developers, small businesses, and infrastructure enthusiasts.
It provides real-time technical insights into traffic, devices, and network characteristics — while remaining lightweight, transparent, and fully under your control.

# 🧠 What It Does

NEXUS Analytics is built as a modular microservice system:
-Service
-Port
-Purpose

Harvester:
3333
Collects anonymous technical browser & device metrics (performance, platform, network type, etc.)

Dashboard:
3334
Real-time analytics panel with charts, maps, and statistics

IP Scanner:
3335
Multi-source IP intelligence via public legal APIs

# ✨ Key Features

📊 Live Dashboard – traffic charts, countries, online users
🌍 Geographic Visualization – map-based session overview
🖥 Technical Metrics – platform, CPU cores, RAM class, screen, GPU renderer
🌐 Network Diagnostics – connection type, RTT, bandwidth hints
🔎 IP Intelligence Scanner – aggregates results from multiple public OSINT APIs
⚡ Lightweight – runs even on low-power devices
🧩 Modular – services separated for scalability
🔐 Zero-Trust Architecture – fully self-hosted, no external storage
🧾 Open Source (GPLv3) – auditable and extensible
🛡 Privacy & Ethics
NEXUS Analytics is designed for technical analytics, not surveillance.
The system does NOT:
Identify individuals
Bypass security
Track users across websites
Perform exploitation
All data is limited to technical session-level diagnostics and public IP intelligence from legal sources.
🎯 Intended Use
Website traffic diagnostics
Infrastructure monitoring
Network performance analysis
Educational OSINT research
Developer observability tools
🖥 System Requirements
Dependencies (Linux):

apt install python3 tmux cloudflared

Python packages:
pip install -r requirements.txt
▶️ Quick Start

git clone https://github.com/MirasakaDrakon/NEXUS-Analytics
cd NEXUS-Analytics
bash start.sh
After launch:
Dashboard → http://localhost:3334
IP Scanner → http://localhost:3335
🏗 Architecture
NEXUS uses a microservice model:
Separate services = better isolation
Low resource footprint
Can be deployed locally or behind tunnels (Cloudflare, etc.)
📜 License
GNU GPL v3
You are free to modify, study, and distribute — improvements must remain open.