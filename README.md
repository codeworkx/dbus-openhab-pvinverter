# dbus-openhab-pvinverter
Get inverter data from Openhab and feed into [Victron Energy Venus OS](https://github.com/victronenergy/venus) DBus to make same available on CCGX and VRM portal

## Inspiration
Based on https://github.com/fabian-lauer/dbus-solax-x1-pvinverter

### Details / Process
- Running as a service
- Connecting to DBus of the Venus OS `com.victronenergy.pvinverter.pv_[SERIAL-OF-INVERTER]`
- After successful DBus connection Openhab item states are getting requested
- Paths are added to the DBus with default value 0 - including some settings like name, etc
- After that a "loop" is started which pulls data every xxx seconds from Openhab and updates the values in the DBus

## Install & Configuration
### Get the code
- Get copy of the main branch.
- Modify config.ini.
- Copy everything to `/data/dbus-openhab-pvinverter`.
- Call the install.sh script.

### config.ini
| Section  | Config item | Explanation |
| ------------- | ------------- | ------------- |
|DEFAULT|ProductName|Desired name of your inverter|
|DEFAULT|SignOfLifeLog|Time in minutes how often a status is added to the log-file current.log with log-level INFO|
|DEFAULT|UpdateInterval|Time in seconds between data requests from Openhab|
|OPENHAB|ServerIP|IP of your Openhab server|
|OPENHAB|ServerPort|Port for web access (Default: 8080)|
|INVERTER|Position|Refer to Victron documentation - 0=AC input 1; 1=AC output; 2=AC input 2|
|INVERTER|MaxPower|Inverter max AC power in watts|
|INVERTER|Phase|Phase your inverter is connected to|
|ITEMS|InverterSerial|Itemname for inverter serial|
|ITEMS|InverterStatus|Itemname for inverter status|
|ITEMS|InverterPowerLimit|Itemname for inverter power limit|
|ITEMS|AcVoltage|Itemname for ac voltage|
|ITEMS|AcCurrent|Itemname for ac current|
|ITEMS|AcPower|Itemname for ac power|
|ITEMS|EnergyForward|Itemname for energy forwarded today|