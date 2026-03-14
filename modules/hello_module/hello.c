// SPDX-License-Identifier: GPL-2.0
/*
 * hello_module - minimal example kernel module
 * Demonstrates module_param, proc filesystem entry, and basic lifecycle.
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/moduleparam.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("smart-honda");
MODULE_DESCRIPTION("Hello world kernel module example");
MODULE_VERSION("0.1");

static char *whom = "World";
static int  repeat = 1;

module_param(whom, charp, 0644);
MODULE_PARM_DESC(whom, "Whom to greet (default: World)");

module_param(repeat, int, 0644);
MODULE_PARM_DESC(repeat, "How many times to greet (default: 1)");

static struct proc_dir_entry *proc_entry;

static int hello_show(struct seq_file *m, void *v)
{
    int i;
    for (i = 0; i < repeat; i++)
        seq_printf(m, "Hello, %s!\n", whom);
    return 0;
}

static int hello_open(struct inode *inode, struct file *file)
{
    return single_open(file, hello_show, NULL);
}

static const struct proc_ops hello_fops = {
    .proc_open    = hello_open,
    .proc_read    = seq_read,
    .proc_lseek   = seq_lseek,
    .proc_release = single_release,
};

static int __init hello_init(void)
{
    int i;
    for (i = 0; i < repeat; i++)
        pr_info("hello_module: Hello, %s!\n", whom);

    proc_entry = proc_create("hello_module", 0444, NULL, &hello_fops);
    if (!proc_entry) {
        pr_err("hello_module: failed to create /proc/hello_module\n");
        return -ENOMEM;
    }

    pr_info("hello_module: loaded. Read /proc/hello_module\n");
    return 0;
}

static void __exit hello_exit(void)
{
    proc_remove(proc_entry);
    pr_info("hello_module: unloaded. Goodbye, %s!\n", whom);
}

module_init(hello_init);
module_exit(hello_exit);
