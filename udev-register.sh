#!/bin/sh
NODE="/sys/$1/inhibited"

if [ ! -e /sys/$1/mouse* ]; then
	exit
fi

chmod g+w $NODE
chgrp input $NODE
