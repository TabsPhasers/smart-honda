// SPDX-License-Identifier: GPL-2.0
/*
 * debug_trace - kernel module demonstrating debugging techniques:
 *   - kprobes for function tracing
 *   - debugfs interface
 *   - kernel timer
 *   - printk rate limiting
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kprobes.h>
#include <linux/debugfs.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/version.h>

/* del_timer_sync() was renamed to timer_delete_sync() in Linux 6.16 */
#if LINUX_VERSION_CODE < KERNEL_VERSION(6, 16, 0)
#define timer_delete_sync(t) del_timer_sync(t)
#endif

MODULE_LICENSE("GPL");
MODULE_AUTHOR("smart-honda");
MODULE_DESCRIPTION("Kernel debugging trace module");
MODULE_VERSION("0.1");

/* ---------- kprobe: trace do_sys_open ---------- */

static char probe_func[64] = "do_sys_openat2";
module_param_string(probe_func, probe_func, sizeof(probe_func), 0444);
MODULE_PARM_DESC(probe_func, "Kernel function to probe (default: do_sys_openat2)");

static unsigned long probe_hit_count;

static int handler_pre(struct kprobe *p, struct pt_regs *regs)
{
    probe_hit_count++;
    pr_info_ratelimited("debug_trace: kprobe hit on %s (total=%lu)\n",
                        p->symbol_name, probe_hit_count);
    return 0;
}

static struct kprobe kp = {
    .pre_handler = handler_pre,
};

/* ---------- debugfs ---------- */

static struct dentry *debugfs_dir;
static u32 debug_val = 0;

/* ---------- timer ---------- */

static struct timer_list heartbeat_timer;
static unsigned int heartbeat_interval_ms = 5000;
module_param(heartbeat_interval_ms, uint, 0644);
MODULE_PARM_DESC(heartbeat_interval_ms, "Heartbeat interval in ms (default: 5000)");

static void heartbeat_cb(struct timer_list *t)
{
    pr_info("debug_trace: heartbeat — probe_hits=%lu debug_val=%u\n",
            probe_hit_count, debug_val);
    mod_timer(&heartbeat_timer,
              jiffies + msecs_to_jiffies(heartbeat_interval_ms));
}

/* ---------- init / exit ---------- */

static int __init debug_trace_init(void)
{
    int ret;

    /* kprobe */
    kp.symbol_name = probe_func;
    ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_warn("debug_trace: register_kprobe failed for '%s' (%d). "
                "Continuing without probe.\n", probe_func, ret);
    } else {
        pr_info("debug_trace: kprobe registered on %s\n", probe_func);
    }

    /* debugfs */
    debugfs_dir = debugfs_create_dir("debug_trace", NULL);
    if (!IS_ERR(debugfs_dir)) {
        debugfs_create_u32("debug_val", 0644, debugfs_dir, &debug_val);
        debugfs_create_ulong("probe_hits", 0444, debugfs_dir, &probe_hit_count);
        pr_info("debug_trace: debugfs at /sys/kernel/debug/debug_trace/\n");
    }

    /* heartbeat timer */
    timer_setup(&heartbeat_timer, heartbeat_cb, 0);
    mod_timer(&heartbeat_timer,
              jiffies + msecs_to_jiffies(heartbeat_interval_ms));

    pr_info("debug_trace: module loaded\n");
    return 0;
}

static void __exit debug_trace_exit(void)
{
    timer_delete_sync(&heartbeat_timer);
    debugfs_remove_recursive(debugfs_dir);
    unregister_kprobe(&kp);
    pr_info("debug_trace: module unloaded (total probe hits: %lu)\n",
            probe_hit_count);
}

module_init(debug_trace_init);
module_exit(debug_trace_exit);
