# smart-honda

A Linux kernel debugging assistant — CLI tool for kernel compilation management, kernel module development, and runtime debugging.

## Features

- **Kernel compilation** — configure (menuconfig / defconfig / olddefconfig), build, clean, query version and make targets
- **`.config` management** — get, set, disable, search options by keyword
- **Kernel module lifecycle** — scaffold new modules, build, load, unload, inspect with `modinfo`
- **dmesg analysis** — filter by log level, regex search, module-specific messages
- **Crash / oops analysis** — parse RIP, call trace, taint flags from kernel crash logs

## Requirements

- Python 3.9+
- Linux (tested on kernel 6.8 / 6.17)
- `gcc`, `make`, kernel headers (`linux-headers-$(uname -r)`) for module compilation

## Installation

```bash
pip install smart-honda
```

Or from source:

```bash
git clone https://github.com/TabsPhasers/smart-honda.git
cd smart-honda
pip install -e .
```

## Usage

### Kernel compilation

```bash
# Build the kernel (auto-detect source)
smart-honda kernel build --source /usr/src/linux -j8

# Build a specific target
smart-honda kernel build --source /usr/src/linux --target bzImage

# Print version
smart-honda kernel version
smart-honda kernel version --source /usr/src/linux
```

### Kernel config

```bash
# Read an option
smart-honda kernel config-get DEBUG_INFO

# Set an option
smart-honda kernel config-set BPF_SYSCALL y

# Search by keyword
smart-honda kernel config-search bpf
```

### Kernel modules

```bash
# Create a new module skeleton
smart-honda module new mydriver --author "Your Name" --desc "My driver"

# Build module against running kernel
smart-honda module build ./mydriver

# Load / unload (requires root)
sudo smart-honda module load ./mydriver param=value
sudo smart-honda module unload mydriver

# List loaded modules
smart-honda module list

# Show modinfo
smart-honda module info ./mydriver
```

### Debugging

```bash
# Show recent kernel messages
smart-honda debug dmesg --tail 100

# Filter by log level
smart-honda debug dmesg --level ERR

# Grep for pattern
smart-honda debug dmesg --grep "unable to handle"

# Filter by module name
smart-honda debug dmesg --module mydriver

# Find kernel oops / BUG entries
smart-honda debug oops

# Analyze a saved crash log file
smart-honda debug analyze /var/log/kernel-oops.txt
```

## Example modules

The `modules/` directory contains ready-to-build example modules:

| Module | Description |
|--------|-------------|
| `hello_module` | Minimal module with `module_param` and `/proc` entry |
| `debug_module` | Advanced: kprobe tracing, debugfs interface, heartbeat timer |

Build an example:

```bash
cd modules/hello_module
make
sudo insmod hello.ko whom="Linux" repeat=3
dmesg | tail -5
sudo rmmod hello
```

## Environment setup

Install all kernel build dependencies in one step:

```bash
sudo bash scripts/setup_env.sh
```

Download and build a specific kernel version:

```bash
bash scripts/build_kernel.sh 6.6 8    # version=6.6, jobs=8
```

## Project structure

```
smart-honda/
├── smart_honda/
│   ├── cli.py              # CLI entry point (Click)
│   ├── kernel/
│   │   ├── compiler.py     # Kernel build helpers
│   │   ├── config.py       # .config read/write
│   │   └── module.py       # Module build/load/inspect
│   ├── debug/
│   │   ├── dmesg.py        # dmesg parsing & filtering
│   │   └── analyzer.py     # Oops/crash log analysis
│   └── utils/helpers.py
├── modules/
│   ├── hello_module/       # Example: proc + module_param
│   └── debug_module/       # Example: kprobe + debugfs + timer
└── scripts/
    ├── setup_env.sh        # Dependency installer
    └── build_kernel.sh     # Kernel download & build
```

## License

GPL-2.0
