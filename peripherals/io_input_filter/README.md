# io_input_filter IO输入滤波软件包

## 1 介绍

**io_input_filter** 软件包提供一个有效的输入滤波功能，它会检测引脚电平的稳定状态，直到检测到持续稳定后才会触发状态改变，软件包提供简单易用的接口函数，用户可通过调整`IIF_TIMES`和`IIF_PERIOD`两个宏来改变滤波条件。

## 2 使用方法

### 2.1 配置宏
	IIF_TIMES   // 滤波次数，连续 IIF_TIMES 次引脚电平持续为高/低的次数
	IIF_PERIOD  // 滤波周期，每隔 IIF_PERIOD 毫秒读取一次引脚电平

### 2.2 接口说明

#### 2.2.1 数据结构:
```
struct io_input_filter
{
    uint8_t pin_id;           // 引脚id，可以由 GET_PIN() 获取
    uint8_t pin_status;       // 滤波后的引脚状态，高/低
    uint8_t filter_counts;    // 当前引脚电平已经持续稳定的次数
    struct io_input_filter *next;    // 单向链表 next
};
typedef struct io_input_filter *io_input_filter_t;
```
#### 2.2.2 函数说明：
1. `io_input_filter_t iif_register(rt_base_t pin);`
在堆中申请一段内存注册滤波器，并初始化数据内容。

2. `rt_err_t iif_init(io_input_filter_t iif, rt_base_t pin);`
初始化一个静态滤波器。

3. `uint8_t iif_read(struct io_input_filter *iif);`
读取引脚状态。

## 3 例程
```
#include "io_input_filter.h"

io_input_filter_t g_input_1 = RT_NULL;
io_input_filter_t g_input_2 = RT_NULL;
io_input_filter_t g_input_3 = RT_NULL;

struct io_input_filter g_input_4;
struct io_input_filter g_input_5;

void iif_example(void *para)
{
    // Created in the heap
    g_input_1 = iif_register(GET_PIN(B, 0));
    g_input_2 = iif_register(GET_PIN(B, 1));
    g_input_3 = iif_register(GET_PIN(B, 2));

    // Created using static variables
    iif_init(&g_input_4, GET_PIN(D, 10));
    iif_init(&g_input_5, GET_PIN(D, 11));

    while(1)
    {
        if(iif_read(g_input_1) == 1)
        {
            rt_kprintf("input_1 status: High\n");
        }

        if(iif_read(g_input_2) == 1)
        {
            rt_kprintf("input_2 status: High\n");
        }

        if(iif_read(g_input_3) == 1)
        {
            rt_kprintf("input_3 status: High\n");
        }

        if(iif_read(&g_input_4) == 1)
        {
            rt_kprintf("input_4 status: High\n");
        }

        if(iif_read(&g_input_5) == 1)
        {
            rt_kprintf("input_5 status: High\n");
        }

        rt_kprintf("\n");
        rt_thread_mdelay(100);
    }
}

MSH_CMD_EXPORT(iif_example, io input filter example);

```

## 4 注意事项
软件包需要使能软件定时器`RT_USING_TIMER_SOFT`和PIN设备驱动`RT_USING_PIN`。

## 5 联系方式
https://github.com/lizdDong/io_input_filter








