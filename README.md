<div align="center">

# ⚡ ClaudeForge

**Universal installer, hardware benchmarker, and model recommender for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](https://github.com/at0m-b0mb/ClaudeForge)
[![Ollama](https://img.shields.io/badge/Ollama-Native%20Integration-black)](https://ollama.ai)

*Detect your hardware → benchmark performance → recommend the best model → install Claude Code → run AI offline with Ollama.*

</div>

---

## ✨ What is ClaudeForge?

ClaudeForge is an all-in-one setup tool for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). It automatically:

1. 🔍 **Detects** your CPU, RAM, GPU, and storage
2. ⚡ **Benchmarks** your machine and assigns a performance tier
3. 🤖 **Recommends** the best Claude API model and compatible local models
4. 📦 **Installs** Claude Code CLI with one click
5. 🔗 **Creates** a `claude-local` alias that routes Claude Code **directly** to a local Ollama model — no proxy, no Python dependencies

---

## 🚀 Quick Start

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/at0m-b0mb/ClaudeForge/main/install.sh | bash
```

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
iwr -useb https://raw.githubusercontent.com/at0m-b0mb/ClaudeForge/main/install.ps1 | iex
```

### From source

```bash
git clone https://github.com/at0m-b0mb/ClaudeForge.git
cd ClaudeForge
pip install -r requirements.txt
python main.py            # CLI wizard
python main.py --gui      # Modern graphical interface
```

---

## 🖥️ GUI

Launch the modern graphical interface with:

```bash
pip install customtkinter
python main.py --gui
```

The GUI features a dark-mode sidebar with six pages:

| Page | Description |
|---|---|
| **Dashboard** | System summary, Claude Code status, quick actions |
| **Hardware** | Full CPU / RAM / GPU / disk breakdown |
| **Benchmark** | Animated score bars, tier badge, overall score |
| **Models** | Recommendations + full catalog with requirements and benchmark scores |
| **Install** | Prerequisites checklist, one-click Claude Code install with live log |
| **Aliases** | Create / manage `claude-local` with direct Ollama integration |

---

## 📟 CLI Usage

```
python main.py                   Full interactive setup wizard (default)
python main.py --gui             Launch the graphical interface
python main.py --detect          Detect and display hardware only
python main.py --benchmark       Detect + benchmark + model recommendations
python main.py --models          Browse the full model catalog
python main.py --install         Install Claude Code (skip hardware steps)
python main.py --check           Check prerequisites only
python main.py --no-benchmark    Full setup but skip the benchmark step
python main.py --report FILE     Save hardware/benchmark data to JSON
python main.py --quiet           Less verbose output
```

### Local Alias (Ollama)

```
python main.py --alias                        Create alias (default: claude-local)
python main.py --alias --alias-name NAME      Custom alias name
python main.py --alias --alias-model ID       Specific Ollama model ID
python main.py --alias --alias-url URL        Custom Ollama URL (default: http://localhost:11434)
python main.py --alias-list                   List all local aliases
python main.py --alias-remove NAME            Delete a local alias
```

---

## 🔗 Ollama Integration — Direct, No Proxy

ClaudeForge uses Ollama's **native Anthropic-compatible API** to route Claude Code to a local model — **zero proxy processes, zero extra Python packages**.

> See [docs.ollama.com/integrations/claude-code](https://docs.ollama.com/integrations/claude-code)

When you create a `claude-local` alias, ClaudeForge writes a shell wrapper that:

```bash
# What the wrapper does under the hood:
export ANTHROPIC_BASE_URL="http://localhost:11434"
export ANTHROPIC_API_KEY="ollama"
exec claude --model qwen2.5-coder:7b "$@"
```

**Result:** two commands, perfectly coexisting:

```bash
claude          # → Anthropic cloud API (your ANTHROPIC_API_KEY)
claude-local    # → Ollama locally      (no API key, no cost, full privacy)
```

### Quick start with Ollama

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull a model
ollama pull qwen2.5-coder:7b

# 3. Create the alias
python main.py --alias --alias-model qwen2.5-coder:7b

# 4. Use it
claude-local "Explain this function"
```

---

## 🤖 Model Catalog

### Claude API Models

| Model | Tier | Context | HumanEval | SWE-bench | Best For |
|---|---|---|---|---|---|
| **Claude 3.7 Sonnet** | Balanced | 200K | 96% | 62% | Hardest coding, reasoning, planning |
| **Claude 3.5 Sonnet** | Balanced | 200K | 93% | 49% | Most projects, complex debugging |
| **Claude Opus 4.5** | Powerful | 200K | 95% | 55% | Largest codebases, highest quality |
| **Claude 3.5 Haiku** | Fast | 200K | 72% | 40% | Autocomplete, quick edits, cost |

### Top Local Models (via Ollama)

| Model | VRAM | RAM | HumanEval | Pull Command |
|---|---|---|---|---|
| **DeepSeek R1 70B** | 44 GB | 64 GB | 90% | `ollama pull deepseek-r1:70b` |
| **Llama 3.3 70B** | 42 GB | 64 GB | 85% | `ollama pull llama3.3:70b` |
| **Qwen 2.5 Coder 32B** | 22 GB | 36 GB | 92% | `ollama pull qwen2.5-coder:32b` |
| **Gemma 3 27B** | 18 GB | 32 GB | 89% | `ollama pull gemma3:27b` |
| **Codestral 22B** | 16 GB | 24 GB | 90% | `ollama pull codestral:22b` |
| **DeepSeek R1 14B** | 10 GB | 16 GB | 78% | `ollama pull deepseek-r1:14b` |
| **Qwen 2.5 Coder 14B** | 10 GB | 16 GB | 88% | `ollama pull qwen2.5-coder:14b` |
| **Qwen 2.5 Coder 7B** | 5.5 GB | 10 GB | 82% | `ollama pull qwen2.5-coder:7b` |
| **Gemma 3 4B** | 3.2 GB | 6 GB | 58% | `ollama pull gemma3:4b` |
| **Llama 3.2 1B** | 1.2 GB | 4 GB | 28% | `ollama pull llama3.2:1b` |

---

## 🧠 Hardware Recommendation Logic

| Strategy | Condition | API Model | Local Candidates |
|---|---|---|---|
| `api_only` | No GPU / VRAM < 6 GB | Sonnet (primary), Haiku (alt) | — |
| `local_capable` | 6–16 GB VRAM | Sonnet | qwen2.5-coder:7b, deepseek-r1:7b |
| `local_preferred` | > 16 GB VRAM | Sonnet | qwen2.5-coder:32b, deepseek-r1:70b, … |

> **Apple Silicon note:** Unified memory is treated as the GPU VRAM pool (70% of system RAM), so a 32 GB M-series Mac is classified as `local_preferred`.

---

## 🏗️ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1  Hardware Detection                                      │
│          Scans CPU, RAM, GPU(s), disk, OS                        │
├─────────────────────────────────────────────────────────────────┤
│  Step 2  Performance Benchmark                                   │
│          8-second CPU (single + multi-core) + memory bandwidth   │
│          → Score 0–100  → Tier: low / mid / high / ultra         │
├─────────────────────────────────────────────────────────────────┤
│  Step 3  Model Recommendation                                    │
│          Maps score + VRAM → best Claude API + local models      │
├─────────────────────────────────────────────────────────────────┤
│  Step 4  Prerequisites Check                                     │
│          Verifies Python, Node.js ≥18, npm, git, curl            │
├─────────────────────────────────────────────────────────────────┤
│  Step 5  Install Claude Code                                     │
│          npm install -g @anthropic-ai/claude-code                │
├─────────────────────────────────────────────────────────────────┤
│  Step 6  Local Alias (Optional)                                  │
│          claude-local → Ollama direct (no proxy, no cost)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Requirements

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| Node.js *(auto-installed)* | ≥ 18 |
| npm *(bundled with Node)* | ≥ 9 |

**Python packages** (installed automatically):

```
rich>=13.7.0       Beautiful terminal UI
psutil>=5.9.0      Hardware detection
requests>=2.31.0   Live model data fetching
questionary>=2.0.1 Interactive CLI prompts
customtkinter>=5.2.2  GUI (optional, only for --gui)
```

**For local Ollama alias** — no extras needed! Just [Ollama](https://ollama.ai).

---

## 📁 Project Structure

```
ClaudeForge/
├── main.py                      Entry point & CLI
├── install.sh                   macOS/Linux bootstrap
├── install.ps1                  Windows PowerShell bootstrap
├── requirements.txt
├── data/
│   └── models.json              Model catalog with requirements & benchmarks
└── src/
    ├── gui/
    │   ├── app.py               Main window, sidebar, shared helpers
    │   └── pages/
    │       ├── dashboard.py     Welcome + quick actions
    │       ├── hardware_page.py System hardware cards
    │       ├── benchmark_page.py Animated benchmark + score
    │       ├── models_page.py   Recommendations + full catalog
    │       ├── install_page.py  Prereq check + Claude Code install
    │       └── alias_page.py    Ollama alias manager
    ├── hardware/
    │   ├── detector.py          CPU, RAM, GPU, disk, OS detection
    │   └── benchmark.py         CPU + memory benchmarks, scoring
    ├── models/
    │   ├── database.py          Model data loader + new fields
    │   ├── recommender.py       Maps hardware → recommendations
    │   └── (model_fetcher.py)   Live Anthropic/Ollama data fetch
    ├── setup/
    │   ├── alias_manager.py     Ollama direct alias (no proxy!)
    │   ├── claude_installer.py  npm install claude-code
    │   ├── configurator.py      API key, settings, CLAUDE.md
    │   ├── node_installer.py    Auto-install Node.js
    │   └── prerequisites.py     Check deps
    └── ui/
        ├── banner.py            ASCII art + log helpers
        ├── components.py        Rich tables, panels
        └── wizard.py            Interactive CLI wizard
```

---

## 🖥️ Supported Platforms

| Platform | Status | Notes |
|---|---|---|
| macOS (Apple Silicon M1–M4) | ✅ Full | Metal GPU, unified memory, native Ollama |
| macOS (Intel) | ✅ Full | NVIDIA/AMD GPU via nvidia-smi/lspci |
| Ubuntu / Debian | ✅ Full | apt-based Node.js install |
| Fedora / RHEL / Rocky | ✅ Full | dnf-based Node.js install |
| Arch Linux | ✅ Full | pacman-based Node.js install |
| Windows 10/11 | ✅ Supported | winget / choco Node.js install |
| WSL2 | ✅ Full | Treated as Linux |

---

## 🤝 Contributing

PRs and issues are welcome!

Ideas for future features:
- [ ] Network speed benchmark
- [ ] Docker-based isolated install mode
- [ ] GitHub Actions CI integration
- [ ] Auto-update checker
- [ ] LM Studio / llama.cpp provider support
- [ ] Model download progress in GUI
- [ ] One-click `ollama pull` from the Models page

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Made with ❤️ for the Claude Code community

[Anthropic Claude Code](https://docs.anthropic.com/en/docs/claude-code) · [Ollama](https://ollama.ai) · [GitHub](https://github.com/at0m-b0mb/ClaudeForge)

</div>

