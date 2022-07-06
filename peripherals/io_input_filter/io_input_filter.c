/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2022-07-04     lizd       the first version
 */

#include "io_input_filter.h"

#define DBG_TAG "iif"
#define DBG_LVL DBG_INFO
#include <rtdbg.h>

static struct io_input_filter *s_iif_head = RT_NULL;
static rt_timer_t s_iif_timer = RT_NULL;

static rt_err_t _iif_initialize(io_input_filter_t iif, rt_base_t pin);
static void _iif_period_task(void *parameter);


#ifdef RT_USING_HEAP
io_input_filter_t iif_register(rt_base_t pin)
{
    io_input_filter_t iif;

    iif = rt_malloc(sizeof(struct io_input_filter));
    if (iif == RT_NULL)
    {
        LOG_E("iif_register() failed: no free memory was found!");
        return RT_NULL;
    }

    if(_iif_initialize(iif, pin) != RT_EOK)
    {
        return RT_NULL;
    }

    return iif;
}
#endif /* #endif RT_USING_HEAP */

rt_err_t iif_init(io_input_filter_t iif, rt_base_t pin)
{
    return _iif_initialize(iif, pin);
}

static rt_err_t _iif_initialize(io_input_filter_t iif, rt_base_t pin)
{
    // Initialize iif structure, Must be initialized before appending list,
    // Otherwise, May cause scheduled tasks to execute uninitialized parameters
    iif->next = RT_NULL;
    iif->pin_status = PIN_LOW;
    iif->filter_counts = 0;
    iif->pin_id = pin;
    rt_pin_mode(pin, PIN_MODE_INPUT);

    // Append to iif list
    if(s_iif_head == RT_NULL)
    {
        s_iif_head = iif;
        LOG_I("list head: 0x%08X", s_iif_head);
    }
    else
    {
        struct io_input_filter *list = s_iif_head;
        while(1)
        {
            if(list->next == RT_NULL)
            {
                list->next = iif;
                LOG_I("iif list:  0x%08X -> 0x%08X", list, list->next);
                break;
            }
            list = list->next;
        }
    }

    // Create A Timer Task
    if(s_iif_timer == RT_NULL)
    {
        s_iif_timer = rt_timer_create("iif task", _iif_period_task,
                            RT_NULL, IIF_PERIOD, RT_TIMER_FLAG_PERIODIC);
        if(s_iif_timer != RT_NULL)
        {
            rt_timer_start(s_iif_timer);
            LOG_I("iif task start.");
        }
        else
        {
            LOG_E("iif task timer create failed!");
            return RT_ERROR;
        }
    }

    return RT_EOK;
}

uint8_t iif_read(struct io_input_filter *iif)
{
    RT_ASSERT(iif != RT_NULL);

    return iif->pin_status;
}

static void io_input_filter_poll(void)
{
    struct io_input_filter *list = RT_NULL;

    for(list = s_iif_head; list != NULL; list = list->next)
    {
        // IO处于低电平状态
        if(rt_pin_read(list->pin_id) == PIN_LOW)
        {
            if(list->pin_status == PIN_HIGH)
            {
                if(list->filter_counts > 0)
                {
                    list->filter_counts--;
                }
                else
                {
                    list->pin_status = PIN_LOW;
                    LOG_I("iif 0x%08X, pin status changed: %d", list, list->pin_status);
                }
            }
            else
            {
                list->filter_counts = 0;
            }
        }
        else
        {
            if(list->pin_status == PIN_LOW)
            {
                if(list->filter_counts < IIF_TIMES)
                {
                    list->filter_counts++;
                }
                else
                {
                    list->pin_status = PIN_HIGH;
                    LOG_I("iif 0x%08X, pin status changed: %d", list, list->pin_status);
                }
            }
            else
            {
                list->filter_counts = IIF_TIMES;
            }
        }

        LOG_D("iif 0x%08X, filter_counts %d, pin_status %d", list, list->filter_counts, list->pin_status);
    }
}

static void _iif_period_task(void *parameter)
{
    io_input_filter_poll();
}

