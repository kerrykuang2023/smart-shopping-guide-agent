# 1Panel / FusionXplay Application Package

This directory contains the application package files for installing Smart Shopping Guide Agent on 1Panel-based systems (including FusionXplay on FusionXpark GB10).

## Structure

```
1panel/smart-guide-agent/
├── logo.png                  # App icon (180x180, ≤10KB)
├── data.yml                  # App-level metadata
├── README.md                 # App description
│
└── 0.1.0/                    # Version directory
    ├── data.yml              # Version-level config + install form
    ├── docker-compose.yml    # Container orchestration
    ├── data/                 # Data mount templates
    └── scripts/              # Lifecycle hooks
        ├── init.sh           # Pre-install initialization
        ├── upgrade.sh        # Upgrade procedures
        └── uninstall.sh      # Cleanup on uninstall
```

## Installation Methods

### Method 1: Local Application Directory

```bash
sudo cp -r smart-guide-agent /opt/1panel/resource/apps/local/
# Refresh 1Panel app store in web UI
```

### Method 2: Via 1Panel CLI (v1.3+)

```bash
1panel app init smart-guide-agent 0.1.0
```

### Method 3: Public App Store Submission (Future)

Submit a PR to the official 1Panel appstore repo:
https://github.com/1Panel-dev/appstore

## Form Fields (User Configuration)

When installing via 1Panel, users will be prompted for:

- **Service Port** (default: 8080)
- **Model Storage Path** (default: ./data/models)
- **Knowledge Base Path** (default: ./data/knowledge)
- **Vision Model** (default: qwen2.5-vl-7b-instruct)
- **GPU Allocation** (default: all)

## Status

> Will be populated in Phase 2 (Week 2-3) once backend MVP is stable
