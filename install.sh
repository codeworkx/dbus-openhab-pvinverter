#!/bin/bash

# set permissions for script files
chmod a+x /data/dbus-openhab-pvinverter/restart.sh
chmod 744 /data/dbus-openhab-pvinverter/restart.sh

chmod a+x /data/dbus-openhab-pvinverter/uninstall.sh
chmod 744 /data/dbus-openhab-pvinverter/uninstall.sh

chmod a+x /data/dbus-openhab-pvinverter/service/run
chmod 755 /data/dbus-openhab-pvinverter/service/run

# create sym-link to run script in deamon
ln -s /data/dbus-openhab-pvinverter/service /service/dbus-openhab-pvinverter

# add install-script to rc.local to be ready for firmware update
filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi

grep -qxF '/data/dbus-openhab-pvinverter/install.sh' $filename || echo '/data/dbus-openhab-pvinverter/install.sh' >> $filename
