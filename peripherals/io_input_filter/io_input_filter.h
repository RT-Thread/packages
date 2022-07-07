/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2022-07-04     lizd       the first version
 */
#ifndef _IO_INPUT_FILTER_H_
#define _IO_INPUT_FILTER_H_

#include <rtthread.h>
#include <rtdevice.h>
#include <drv_common.h>

/* Input Filter Times */
#ifndef IIF_TIMES
#define IIF_TIMES     10
#endif

/* Input Filter Period */
#ifndef IIF_PERIOD
#define IIF_PERIOD    5
#endif


struct io_input_filter
{
    uint8_t pin_id;
    uint8_t pin_status;
    uint8_t filter_counts;
    struct io_input_filter *next;
};
typedef struct io_input_filter *io_input_filter_t;


io_input_filter_t iif_register(rt_base_t pin);
rt_err_t iif_init(io_input_filter_t iif, rt_base_t pin);
uint8_t iif_read(struct io_input_filter *iif);

#endif /* PACKAGES_IO_INPUT_FILTER_H_ */
