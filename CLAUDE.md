# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the CC_ISIS project - a MobiFlight custom firmware device that implements an A320-style ISIS (Integrated Standby Instrument System) display for flight simulation. The device uses an ESP32-S3 microcontroller with a 4-inch LCD to show attitude (pitch/bank), airspeed, altitude, pressure setting, glide slope, and CDI data.

## Architecture

### Hardware Platform
- **Primary MCU**: ESP32-S3 DevKitC-1 with PSRAM
- **Display**: 4-inch LCD with LovyanGFX graphics library
- **Communication**: Serial/USB to PC (no rotary encoder — ISIS is display-only)

### Core Components

#### Main Classes
- **CC_ISIS**: Primary display controller (`CC_ISIS/CC_ISIS.h|.cpp`) - handles all display rendering, flight data processing, and graphics updates
- **MFCustomDevice**: MobiFlight integration layer (`CC_ISIS/MFCustomDevice.h|.cpp`) - manages device lifecycle and message handling
- **CC_ISIS_Base**: Shared base class (`CC_ISIS/ISISCommon.h|.cpp`) - provides `setCommon()` for message IDs 0-14, brightness/power management, and settings persistence

#### Display System
- Uses LovyanGFX library for high-performance graphics
- Multiple sprite layers for the instrument:
  - Attitude background (sky/ground horizon with pitch ladder)
  - Roll arc and roll/slip pointer overlay
  - Airspeed tape
  - Altitude tape
  - Pressure/kohlsman setting
  - Mach number display
  - ILS/LS deviation indicators (in development)

## Build System

### PlatformIO Configuration
- **Primary config**: `platformio.ini` - includes core MobiFlight dependencies
- **Custom config**: `CC_ISIS/CC_ISIS_platformio.ini` - device-specific environment

### Build Commands
```bash
# Build all environments
pio run

# Build CC_ISIS environment
pio run -e ccrawford_cc_isis_esp32s3

# Clean build
pio run -t clean

# Upload firmware
pio run -t upload
```

### Build Scripts
- `get_version.py`: Sets firmware version from environment variables
- `get_CoreFiles.py`: Downloads MobiFlight core firmware source
- `copy_fw_files.py`: Packages firmware files and creates distribution ZIP

### Dependencies
- **LovyanGFX**: High-performance graphics library for ESP32
- **MobiFlight Core**: Base firmware framework (version controlled via `custom_core_firmware_version`)
- **ESP32 Arduino Core**: Platform framework

## Development Workflow

### Message Handling
The device receives flight data via MobiFlight's message system.

**Common message IDs** (handled by `CC_ISIS_Base::setCommon()`):
- 0: AP Heading Bug
- 1: Approach Type (GPS approach type enum)
- 2: CDI Lateral Deviation
- 3: CDI Needle Valid
- 4: CDI To/From Flag
- 5: Glide Slope Deviation
- 6: Glide Slope Needle Valid
- 7: Ground Speed
- 8: Ground Track (Magnetic)
- 9: Heading (Magnetic)
- 10: Nav Source (1=GPS, 0=NAV)
- 12: Screen Brightness
- 13: Power On/Off
- 14: Power Control mode

**ISIS-specific message IDs** (handled by `CC_ISIS::set()`):
- 60: Airspeed (knots)
- 71: Ball/Slip-Skid position
- 72: Bank Angle (degrees)
- 77: Indicated Altitude (feet)
- 80: Pitch Angle (degrees)
- 100: Pressure in mb (Kohlsman)
- 101: ISIS Baro Mode (1=STD, 0=normal)
- 102: Mach number

### Display Draw Functions
- `drawAttitude()`: Horizon, pitch ladder, bank indicator
- `drawSpeedTape()`: Airspeed tape with pointer
- `drawAltTape()`: Altitude tape with pointer
- `drawPressure()`: Kohlsman/mb pressure setting
- `drawMach()`: Mach number (shows when >= 0.45)
- `drawLS()`: ILS/localizer deviation (in development)

## Key File Locations

### Source Code
- `CC_ISIS/CC_ISIS.h|.cpp`: Main ISIS device implementation
- `CC_ISIS/ISISCommon.h|.cpp`: Shared base class, state structs, power management
- `CC_ISIS/MFCustomDevice.h|.cpp`: MobiFlight integration

### Configuration
- `CC_ISIS/4inchLCDConfig.h`: Display configuration (Waveshare)
- `CC_ISIS/4inchLCDConfig_Guition.h`: Display configuration (Guition)
- `CC_ISIS/MFCustomDevicesConfig.h`: Flash config string
- `CC_ISIS/MFCustomDeviceTypes.h`: Message ID routing constants

### Assets
- `CC_ISIS/Sprites/`: Compiled sprite image headers (attitude bg, roll arc, etc.)
- `CC_ISIS/Images/isisFont.h`: A320-style ISIS font
- `CC_ISIS/Images/PrimaSansMid32.h`: Font used for battery/power display
- `CC_ISIS/Community/`: MobiFlight connector configuration files

### Scripts
- `CC_ISIS/Scripts/`: Python image conversion utilities

## Common Development Tasks

### Adding New Flight Data
1. Add message ID case in `CC_ISIS::set()` (or `CC_ISIS_Base::setCommon()` if truly common)
2. Add corresponding field to `ISISState` in `ISISCommon.h`
3. Update appropriate draw function in `CC_ISIS.cpp`
4. Add message ID to `CC_ISIS/Community/devices/CC_ISIS.device.json`

### Display Modifications
1. Modify draw functions in `CC_ISIS.cpp`
2. Update sprite definitions in `CC_ISIS/Sprites/` if new images are needed
3. Run image conversion scripts in `CC_ISIS/Scripts/` to regenerate `.h` files

### Settings Changes
When modifying `CC_ISIS_Settings` struct layout, **always increment `SETTINGS_VERSION`** in `ISISCommon.h` so stale EEPROM data is detected and reset to defaults.
