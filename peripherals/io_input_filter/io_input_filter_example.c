/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2022-07-05     lizd       the first version
 */

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


