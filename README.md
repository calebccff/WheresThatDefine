# Where's That Define

WTD is a python tool for replacing values with the C preprocessor macro which defined them. An example of this is when trying to understand a driver by dumping every read() and write(), you end up with a big list of values like the following:

```
[  162.326260] qcom,qpnp-smb2: smblib_read(addr = 0x1307, val=0x01)
[  162.326289] qcom,qpnp-smb2: smblib_read(addr = 0x1308, val=0x08)
[  162.326373] qcom,qpnp-smb2: smblib_read(addr = 0x1307, val=0x01)
[  162.326539] qcom,qpnp-smb2: smblib_read(addr = 0x1070, val=0x79)
[  162.326582] qcom,qpnp-smb2: smblib_read(addr = 0x1061, val=0x4e)
[  162.326623] qcom,qpnp-smb2: smblib_read(addr = 0x1607, val=0x13)
[  162.326666] qcom,qpnp-smb2: smblib_read(addr = 0x1007, val=0x80)
[  162.326702] qcom,qpnp-smb2: smblib_read(addr = 0x1365, val=0xf7)
```

Wouldn't it be so much better if it could look like this instead?
```
[ 7291.659328] qcom,qpnp-smb2: smblib_read(addr = APSD_STATUS_REG, val = APSD_DTC_STATUS_DONE_BIT)
[ 7291.659358] qcom,qpnp-smb2: smblib_read(addr = APSD_RESULT_STATUS_REG, val = DCP_CHARGER_BIT|APSD_RESULT_STATUS_MASK=0x8)
[ 7291.659457] qcom,qpnp-smb2: smblib_read(addr = APSD_STATUS_REG, val = APSD_DTC_STATUS_DONE_BIT)
[ 7291.659610] qcom,qpnp-smb2: smblib_read(addr = FLOAT_VOLTAGE_CFG_REG, val = FLOAT_VOLTAGE_SETTING_MASK=0x79)
[ 7291.659652] qcom,qpnp-smb2: smblib_read(addr = FAST_CHARGE_CURRENT_CFG_REG, val = FAST_CHARGE_CURRENT_SETTING_MASK=0x4e)
[ 7291.659694] qcom,qpnp-smb2: smblib_read(addr = ICL_STATUS_REG, val = INPUT_CURRENT_LIMIT_MASK=0x13)
[ 7291.659739] qcom,qpnp-smb2: smblib_read(addr = BATTERY_CHARGER_STATUS_2_REG, val = 0x00)
[ 7291.659776] qcom,qpnp-smb2: smblib_read(addr = USBIN_LOAD_CFG_REG, val = USBIN_OV_CH_LOAD_OPTION_BIT|ICL_OVERRIDE_AFTER_APSD_BIT)
[ 7291.659807] qcom,qpnp-smb2: smblib_read(addr = USBIN_CURRENT_LIMIT_CFG_REG, val = USBIN_CURRENT_LIMIT_MASK=0x3c)
[ 7291.661133] qcom,qpnp-smb2: smblib_read(addr = USB_INT_RT_STS, val = USBIN_PLUGIN_RT_STS_BIT)
```

Well with the power of WTD and Regex, it can!

Yes that's right, this is a header file parser using regex.

## Usage

Before using WTD, some manual processing of `#define`s is required, WTD can parse macros in the following formats:

```c
// The literal 3735941133 in hex
#define SOME_MACRO 0xdeadf00d
```
```c
// The literal 1234
#define SOME_MACRO 1234
```
```c
// Bit 2
#define SOME_MACRO BIT(2)
```
```c
// Bitmask from bit 2 to bit 0
#define SOME_MACRO GENMASK(2, 0)
```

The header parser uses context to relate a bunch of bit / mask macros to a particular register, as such the ordering matters. The symbol tree will attribute all BIT() and GENMASK() macros to whatever the last literal value register was.
For example:
```h
#define BATTERY_CHARGER_STATUS_5_REG			0x100B
#define VALID_INPUT_POWER_SOURCE_BIT			BIT(7)
#define DISABLE_CHARGING_BIT				BIT(6)
#define FORCE_ZERO_CHARGE_CURRENT_BIT			BIT(5)
#define CHARGING_ENABLE_BIT				BIT(4)
#define TAPER_BIT					BIT(3)
#define ENABLE_CHG_SENSORS_BIT				BIT(2)
#define ENABLE_TAPER_SENSOR_BIT				BIT(1)
#define TAPER_REGION_BIT				BIT(0)
```
produces the following tree:

```py
BATTERY_CHARGER_STATUS_5_REG: {
    'value': 4107,
    'bits':
    [
        {'name': 'VALID_INPUT_POWER_SOURCE_BIT', 'bit': 7},
        {'name': 'DISABLE_CHARGING_BIT', 'bit': 6},
        {'name': 'FORCE_ZERO_CHARGE_CURRENT_BIT', 'bit': 5},
        {'name': 'CHARGING_ENABLE_BIT', 'bit': 4},
        {'name': 'TAPER_BIT', 'bit': 3},
        {'name': 'ENABLE_CHG_SENSORS_BIT', 'bit': 2},
        {'name': 'ENABLE_TAPER_SENSOR_BIT', 'bit': 1},
        {'name': 'TAPER_REGION_BIT', 'bit': 0}
    ],
    'masks': []}
```

Some semi-manual preprocessing may be required before using this tool, personally I've found the multi-cursor feature in vscode to be very useful, as well as regex-based find and replace. You could also do this with sed / grep or whatever your preferred method is.

The logfile must log register read/writes in the format
```c
addr = 0x123, val = 0x123
```
Alternatively hack your format into `process_logs()`.