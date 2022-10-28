#!/bin/sh
#  SPDX-License-Identifier: BSD-2-Clause
#
#  Copyright (c) 2022 Valve Software
#  Author: Vicki Pfau <vi@endrift.com>
NODE="/sys/$1/inhibited"

if [ ! -e /sys/$1/mouse* ]; then
	exit
fi

chmod g+w $NODE
