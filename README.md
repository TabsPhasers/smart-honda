# smart-honda

Linux 内核调试辅助工具 —— 集内核编译管理、内核模块开发、运行时调试于一体的命令行工具。

## 功能特性

- **内核编译** — 配置（menuconfig / defconfig / olddefconfig）、构建、清理、查询版本和 make 目标
- **`.config` 管理** — 读取、设置、禁用、按关键字搜索配置项
- **内核模块全生命周期** — 生成模块骨架、编译、加载、卸载、modinfo 查看
- **dmesg 分析** — 按日志级别过滤、正则搜索、按模块名过滤
- **崩溃 / oops 分析** — 从内核崩溃日志中解析 RIP、调用栈、taint 标志

## 环境要求

- Python 3.9+
- Linux（已在内核 6.8 / 6.17 上测试）
- `gcc`、`make`、内核头文件（`linux-headers-$(uname -r)`）用于模块编译

## 安装

```bash
pip install smart-honda
```

或从源码安装：

```bash
git clone https://github.com/TabsPhasers/smart-honda.git
cd smart-honda
pip install -e .
```

## 使用方法

### 内核编译

```bash
# 构建内核（自动检测源码目录）
smart-honda kernel build --source /usr/src/linux -j8

# 构建指定目标
smart-honda kernel build --source /usr/src/linux --target bzImage

# 查看版本
smart-honda kernel version
smart-honda kernel version --source /usr/src/linux
```

### 内核配置

```bash
# 读取配置项
smart-honda kernel config-get DEBUG_INFO

# 设置配置项
smart-honda kernel config-set BPF_SYSCALL y

# 按关键字搜索
smart-honda kernel config-search bpf
```

### 内核模块

```bash
# 创建新模块骨架
smart-honda module new mydriver --author "Your Name" --desc "我的驱动"

# 针对当前运行内核编译模块
smart-honda module build ./mydriver

# 加载 / 卸载（需要 root）
sudo smart-honda module load ./mydriver param=value
sudo smart-honda module unload mydriver

# 列出已加载模块
smart-honda module list

# 查看模块信息
smart-honda module info ./mydriver
```

### 调试

```bash
# 查看最近内核消息
smart-honda debug dmesg --tail 100

# 按日志级别过滤
smart-honda debug dmesg --level ERR

# 正则搜索
smart-honda debug dmesg --grep "unable to handle"

# 按模块名过滤
smart-honda debug dmesg --module mydriver

# 查找内核 oops / BUG
smart-honda debug oops

# 分析保存的崩溃日志文件
smart-honda debug analyze /var/log/kernel-oops.txt
```

## 示例模块

`modules/` 目录包含可直接编译的示例模块：

| 模块 | 说明 |
|------|------|
| `hello_module` | 最简模块，含 `module_param` 和 `/proc` 接口 |
| `debug_module` | 进阶模块：kprobe 追踪、debugfs 接口、心跳定时器 |

编译并加载示例：

```bash
cd modules/hello_module
make
sudo insmod hello.ko whom="Linux" repeat=3
dmesg | tail -5
sudo rmmod hello
```

## 环境搭建

一键安装所有内核构建依赖：

```bash
sudo bash scripts/setup_env.sh
```

下载并编译指定内核版本：

```bash
bash scripts/build_kernel.sh 6.6 8    # 版本=6.6，并行数=8
```

## 项目结构

```
smart-honda/
├── smart_honda/
│   ├── cli.py              # CLI 入口（Click）
│   ├── kernel/
│   │   ├── compiler.py     # 内核构建辅助
│   │   ├── config.py       # .config 读写
│   │   └── module.py       # 模块编译/加载/查看
│   ├── debug/
│   │   ├── dmesg.py        # dmesg 解析与过滤
│   │   └── analyzer.py     # oops/崩溃日志分析
│   └── utils/helpers.py
├── modules/
│   ├── hello_module/       # 示例：proc + module_param
│   └── debug_module/       # 示例：kprobe + debugfs + 定时器
└── scripts/
    ├── setup_env.sh        # 依赖安装脚本
    └── build_kernel.sh     # 内核下载与构建脚本
```

## 许可证

GPL-2.0
