# Claude Code Setup

> **Universal installer, hardware benchmarker, and model recommender for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).**

Automatically detects your machine's hardware, benchmarks its performance, recommends the right Claude model for your setup, and installs Claude Code — fully configured and ready to use.

---

## Features

| Feature | Description |
|---|---|
| **Hardware Detection** | CPU model, core count, frequency, RAM, GPU (NVIDIA/AMD/Apple Silicon), disk |
| **Performance Benchmark** | Single-core & multi-core CPU, memory bandwidth, composite score |
| **Model Recommendation** | Maps your hardware to the best Claude API model + local Ollama alternatives |
| **One-Command Install** | Installs Node.js, Claude Code, and configures your environment |
| **Cross-Platform** | macOS (Intel + Apple Silicon), Linux (Ubuntu/Debian/Arch/Fedora), Windows |
| **Beautiful TUI** | Rich-based terminal UI with progress bars, color tables, and panels |
| **Ollama Integration** | Detects GPU VRAM and lists local LLMs you can actually run |
| **Shell Profile Patching** | Writes API key and PATH changes to the right profile file automatically |
| **Portable Report** | Export a `--report` JSON file for debugging or sharing your hardware specs |

---

## Quick Start

### macOS / Linux — one-liner

```bash
curl -fsSL https://raw.githubusercontent.com/at0m-b0mb/claude-code-setup/main/install.sh | bash
```

### Windows — PowerShell one-liner

```powershell
# Run once to allow scripts:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

iwr -useb https://raw.githubusercontent.com/at0m-b0mb/claude-code-setup/main/install.ps1 | iex
```

### From a local clone

```bash
git clone https://github.com/at0m-b0mb/claude-code-setup.git
cd claude-code-setup
pip install -r requirements.txt
python main.py
```

---

## Usage

```
python main.py                   Full interactive setup wizard (default)
python main.py --detect          Detect and display hardware only
python main.py --benchmark       Detect + benchmark + model recommendations
python main.py --install         Install Claude Code (skip hardware steps)
python main.py --check           Check prerequisites only
python main.py --no-benchmark    Full setup but skip the benchmark step
python main.py --report FILE     Save hardware/benchmark data to JSON
python main.py --quiet           Less verbose output
```

---

## What it does, step by step

```
Step 1 — Hardware Detection
  Scans CPU, RAM, GPU(s), disk, OS.

Step 2 — Performance Benchmark
  Runs ~8-second CPU (single + multi core) and memory bandwidth tests.
  Scores your machine and assigns a tier: low / mid / high / ultra.

Step 3 — Model Recommendation
  Maps your hardware score + GPU VRAM to:
    • Best Claude API model  (Haiku / Sonnet / Opus)
    • Runnable local models  (via Ollama, if you have a GPU)

Step 4 — Prerequisites Check
  Verifies Python, Node.js (≥18), npm, git, curl.
  Offers to install Node.js automatically if missing.

Step 5 — Install Claude Code
  Installs @anthropic-ai/claude-code via npm with auto-sudo fallback.
  Verifies the installation with `claude --version`.

Step 6 — Configuration
  • Saves your ANTHROPIC_API_KEY to your shell profile
  • Writes ~/.claude/settings.json with your recommended model
  • Creates a CLAUDE.md template in your current project directory
  • Optionally installs Ollama and pulls your top local model
```

---

## Model Recommendation Logic

| Strategy | Condition | API Model | Local Models |
|---|---|---|---|
| `api_only` | No GPU / VRAM < 6 GB | Sonnet (primary), Haiku (alt) | None |
| `local_capable` | 6–16 GB VRAM | Sonnet | qwen2.5-coder:7b, llama3.1:8b |
| `local_preferred` | > 16 GB VRAM | Sonnet | llama3.1:70b, deepseek-coder-v2:16b, … |

**Apple Silicon note:** Unified memory is treated as the GPU VRAM pool (70 % of system RAM), so a 32 GB M-series Mac is classified as `local_preferred`.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| pip | any |
| Node.js *(auto-installed)* | ≥ 18 |
| npm *(bundled with Node)* | ≥ 9 |

Python packages (auto-installed by `install.sh`):

```
rich>=13.7.0
psutil>=5.9.0
requests>=2.31.0
questionary>=2.0.1
```

---

## Project Structure

```
claude-code-setup/
├── main.py                      Entry point & CLI
├── install.sh                   macOS / Linux bootstrap (auto-installs deps)
├── install.ps1                  Windows PowerShell bootstrap
├── requirements.txt             Python dependencies
├── src/
│   ├── hardware/
│   │   ├── detector.py          CPU, RAM, GPU, disk, OS detection
│   │   └── benchmark.py         CPU + memory benchmarks, scoring
│   ├── models/
│   │   ├── database.py          Model data loader (reads data/models.json)
│   │   └── recommender.py       Maps hardware → model recommendations
│   ├── setup/
│   │   ├── prerequisites.py     Checks Python, Node, npm, git, curl
│   │   ├── node_installer.py    Installs Node.js via nvm / brew / apt / winget
│   │   ├── claude_installer.py  Installs @anthropic-ai/claude-code via npm
│   │   └── configurator.py      API key, settings.json, CLAUDE.md, Ollama
│   └── ui/
│       ├── banner.py            ASCII art banner & log helpers
│       ├── components.py        Rich tables, panels, progress bars
│       └── wizard.py            Interactive step-by-step setup wizard
└── data/
    └── models.json              Claude API + Ollama model database
```

---

## Supported Platforms

| Platform | Status | Notes |
|---|---|---|
| macOS (Apple Silicon) | Fully supported | Metal GPU, unified memory detection |
| macOS (Intel) | Fully supported | NVIDIA/AMD GPU via nvidia-smi/lspci |
| Ubuntu / Debian | Fully supported | apt-based Node.js install |
| Fedora / RHEL | Fully supported | dnf-based Node.js install |
| Arch Linux | Fully supported | pacman-based Node.js install |
| Windows 10/11 | Supported | winget / choco Node.js install |
| WSL2 | Fully supported | Treated as Linux |

---

## Contributing

PRs welcome! Ideas for future features:

- [ ] Network speed benchmark
- [ ] Docker-based isolated install mode
- [ ] GitHub Actions CI integration
- [ ] Auto-update checker
- [ ] More local model providers (LM Studio, llama.cpp)

---

## License

MIT — see [LICENSE](LICENSE).
