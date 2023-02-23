#!/bin/bash

rm /service/dbus-openhab-pvinverter
kill $(pgrep -f 'supervise dbus-openhab-pvinverter')
chmod a-x /data/dbus-openhab-pvinverter/service/run
./restart.sh
