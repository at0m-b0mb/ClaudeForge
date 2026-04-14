"""
Hardware detection module.
Gathers CPU, RAM, GPU, disk, and OS information cross-platform.
"""

import platform
import subprocess
import os
import re
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CPUInfo:
    model: str
    physical_cores: int
    logical_cores: int
    max_freq_mhz: float
    architecture: str
    is_apple_silicon: bool = False


@dataclass
class GPUInfo:
    name: str
    vram_mb: int
    gpu_type: str  # "nvidia", "amd", "apple", "intel", "unknown"
    cuda_available: bool = False
    metal_available: bool = False
    rocm_available: bool = False


@dataclass
class SystemInfo:
    os_name: str
    os_version: str
    architecture: str
    cpu: CPUInfo
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    gpus: List[GPUInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "cpu": {
                "model": self.cpu.model,
                "physical_cores": self.cpu.physical_cores,
                "logical_cores": self.cpu.logical_cores,
                "max_freq_mhz": self.cpu.max_freq_mhz,
                "architecture": self.cpu.architecture,
                "is_apple_silicon": self.cpu.is_apple_silicon,
            },
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "disk_total_gb": self.disk_total_gb,
            "disk_free_gb": self.disk_free_gb,
            "gpus": [
                {
                    "name": g.name,
                    "vram_mb": g.vram_mb,
                    "gpu_type": g.gpu_type,
                    "cuda_available": g.cuda_available,
                    "metal_available": g.metal_available,
                    "rocm_available": g.rocm_available,
                }
                for g in self.gpus
            ],
        }


def _run(cmd: list, timeout: int = 5) -> Optional[str]:
    """Run a subprocess command, return stdout or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


class HardwareDetector:
    """Detects hardware specs on macOS, Linux, and Windows."""

    def detect(self) -> SystemInfo:
        """Run full hardware detection and return a SystemInfo object."""
        return SystemInfo(
            os_name=self._detect_os_name(),
            os_version=platform.version(),
            architecture=platform.machine(),
            cpu=self._detect_cpu(),
            ram_total_gb=self._detect_ram_total(),
            ram_available_gb=self._detect_ram_available(),
            disk_total_gb=self._detect_disk_total(),
            disk_free_gb=self._detect_disk_free(),
            gpus=self._detect_gpus(),
        )

    # ------------------------------------------------------------------
    # OS
    # ------------------------------------------------------------------

    def _detect_os_name(self) -> str:
        system = platform.system()
        if system == "Darwin":
            try:
                mac_ver = platform.mac_ver()[0]
                return f"macOS {mac_ver}"
            except Exception:
                return "macOS"
        if system == "Linux":
            # Try reading /etc/os-release
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=", 1)[1].strip().strip('"')
            except FileNotFoundError:
                pass
            return f"Linux {platform.release()}"
        if system == "Windows":
            return f"Windows {platform.release()}"
        return system

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------

    def _detect_cpu(self) -> CPUInfo:
        arch = platform.machine()
        model = self._cpu_model_name()
        physical, logical = self._cpu_core_counts()
        freq = self._cpu_max_freq()
        is_apple = self._is_apple_silicon()
        return CPUInfo(
            model=model,
            physical_cores=physical,
            logical_cores=logical,
            max_freq_mhz=freq,
            architecture=arch,
            is_apple_silicon=is_apple,
        )

    def _cpu_model_name(self) -> str:
        system = platform.system()
        if system == "Darwin":
            out = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
            if out:
                return out
            # Apple Silicon reports differently
            out = _run(["sysctl", "-n", "hw.model"])
            return out or "Unknown CPU"
        if system == "Linux":
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":", 1)[1].strip()
            except FileNotFoundError:
                pass
            return _run(["lscpu"]) or "Unknown CPU"
        if system == "Windows":
            out = _run(
                ["powershell", "-Command",
                 "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty Name"]
            )
            return out or platform.processor() or "Unknown CPU"
        return platform.processor() or "Unknown CPU"

    def _cpu_core_counts(self):
        try:
            import psutil
            physical = psutil.cpu_count(logical=False) or 1
            logical = psutil.cpu_count(logical=True) or 1
            return physical, logical
        except ImportError:
            pass
        # Fallback
        logical = os.cpu_count() or 1
        # Estimate physical as half logical (common SMT)
        return max(1, logical // 2), logical

    def _cpu_max_freq(self) -> float:
        try:
            import psutil
            freq = psutil.cpu_freq()
            if freq:
                return freq.max or freq.current or 0.0
        except ImportError:
            pass
        system = platform.system()
        if system == "Darwin":
            out = _run(["sysctl", "-n", "hw.cpufrequency_max"])
            if out:
                try:
                    return float(out) / 1_000_000  # Hz -> MHz
                except ValueError:
                    pass
        if system == "Linux":
            path = "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"
            try:
                with open(path) as f:
                    return float(f.read().strip()) / 1000  # kHz -> MHz
            except (FileNotFoundError, ValueError):
                pass
        return 0.0

    def _is_apple_silicon(self) -> bool:
        if platform.system() != "Darwin":
            return False
        arch = platform.machine().lower()
        return arch in ("arm64", "aarch64")

    # ------------------------------------------------------------------
    # RAM
    # ------------------------------------------------------------------

    def _detect_ram_total(self) -> float:
        try:
            import psutil
            return round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except ImportError:
            pass
        system = platform.system()
        if system == "Darwin":
            out = _run(["sysctl", "-n", "hw.memsize"])
            if out:
                return round(int(out) / (1024 ** 3), 2)
        if system == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return round(kb / (1024 ** 2), 2)
            except FileNotFoundError:
                pass
        return 0.0

    def _detect_ram_available(self) -> float:
        try:
            import psutil
            return round(psutil.virtual_memory().available / (1024 ** 3), 2)
        except ImportError:
            pass
        if platform.system() == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemAvailable:"):
                            kb = int(line.split()[1])
                            return round(kb / (1024 ** 2), 2)
            except FileNotFoundError:
                pass
        return 0.0

    # ------------------------------------------------------------------
    # Disk
    # ------------------------------------------------------------------

    def _detect_disk_total(self) -> float:
        try:
            import psutil
            usage = psutil.disk_usage("/")
            return round(usage.total / (1024 ** 3), 2)
        except ImportError:
            pass
        return 0.0

    def _detect_disk_free(self) -> float:
        try:
            import psutil
            usage = psutil.disk_usage("/")
            return round(usage.free / (1024 ** 3), 2)
        except ImportError:
            pass
        return 0.0

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------

    def _detect_gpus(self) -> List[GPUInfo]:
        gpus = []
        gpus.extend(self._detect_nvidia_gpus())
        gpus.extend(self._detect_amd_gpus())
        gpus.extend(self._detect_apple_gpu())
        gpus.extend(self._detect_intel_gpu())
        return gpus

    def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        out = _run([
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ])
        if not out:
            return []
        gpus = []
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                name = parts[0]
                try:
                    vram_mb = int(parts[1])
                except ValueError:
                    vram_mb = 0
                gpus.append(GPUInfo(
                    name=name,
                    vram_mb=vram_mb,
                    gpu_type="nvidia",
                    cuda_available=True,
                ))
        return gpus

    def _detect_amd_gpus(self) -> List[GPUInfo]:
        # Try rocm-smi
        out = _run(["rocm-smi", "--showmeminfo", "vram", "--json"])
        if out:
            try:
                data = json.loads(out)
                gpus = []
                for card_key, info in data.items():
                    if "card" in card_key.lower():
                        vram_bytes = int(info.get("VRAM Total Memory (B)", 0))
                        gpus.append(GPUInfo(
                            name=info.get("GPU ID", card_key),
                            vram_mb=vram_bytes // (1024 * 1024),
                            gpu_type="amd",
                            rocm_available=True,
                        ))
                if gpus:
                    return gpus
            except (json.JSONDecodeError, ValueError):
                pass
        # Linux: check lspci for AMD/ATI
        out = _run(["lspci"])
        if out:
            gpus = []
            for line in out.splitlines():
                if re.search(r"(AMD|ATI|Radeon)", line, re.IGNORECASE):
                    if "VGA" in line or "3D" in line or "Display" in line:
                        name = re.sub(r"^\S+\s+\S+\s+", "", line).strip()
                        gpus.append(GPUInfo(
                            name=name,
                            vram_mb=0,
                            gpu_type="amd",
                        ))
            if gpus:
                return gpus
        return []

    def _detect_apple_gpu(self) -> List[GPUInfo]:
        if platform.system() != "Darwin":
            return []
        out = _run(["system_profiler", "SPDisplaysDataType", "-json"])
        if not out:
            return []
        try:
            data = json.loads(out)
            displays = data.get("SPDisplaysDataType", [])
            gpus = []
            for d in displays:
                name = d.get("sppci_model", d.get("_name", "Apple GPU"))
                # Unified memory: total RAM is shared, report it as VRAM for Apple Silicon
                vram_raw = d.get("spdisplays_vram", "0 MB")
                vram_mb = self._parse_vram_string(vram_raw)
                if vram_mb == 0 and self._is_apple_silicon():
                    # Unified memory — report system RAM as the VRAM pool
                    vram_mb = int(self._detect_ram_total() * 1024)
                gpus.append(GPUInfo(
                    name=name,
                    vram_mb=vram_mb,
                    gpu_type="apple",
                    metal_available=True,
                ))
            return gpus
        except (json.JSONDecodeError, KeyError):
            return []

    def _detect_intel_gpu(self) -> List[GPUInfo]:
        """Detect Intel integrated graphics (best-effort)."""
        if platform.system() == "Linux":
            out = _run(["lspci"])
            if out:
                for line in out.splitlines():
                    if "Intel" in line and ("VGA" in line or "Display" in line):
                        name = re.sub(r"^\S+\s+\S+\s+", "", line).strip()
                        return [GPUInfo(name=name, vram_mb=0, gpu_type="intel")]
        if platform.system() == "Windows":
            out = _run([
                "powershell", "-Command",
                "Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name"
            ])
            if out:
                for line in out.splitlines():
                    if "Intel" in line:
                        return [GPUInfo(name=line.strip(), vram_mb=0, gpu_type="intel")]
        return []

    @staticmethod
    def _parse_vram_string(s: str) -> int:
        """Parse strings like '8 GB', '4096 MB' into MB."""
        s = s.strip()
        match = re.match(r"(\d+(?:\.\d+)?)\s*(GB|MB|KB)?", s, re.IGNORECASE)
        if not match:
            return 0
        value = float(match.group(1))
        unit = (match.group(2) or "MB").upper()
        if unit == "GB":
            return int(value * 1024)
        if unit == "KB":
            return int(value / 1024)
        return int(value)
