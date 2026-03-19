# PAD Romania - Home Assistant Integration

[![HACS Validation](https://github.com/emanuelbesliu/homeassistant-pad/actions/workflows/validate.yml/badge.svg)](https://github.com/emanuelbesliu/homeassistant-pad/actions/workflows/validate.yml)
[![Release](https://github.com/emanuelbesliu/homeassistant-pad/actions/workflows/release-please.yml/badge.svg)](https://github.com/emanuelbesliu/homeassistant-pad/releases)

Custom Home Assistant integration for verifying **PAD** (Polița de Asigurare a Locuinței) mandatory home insurance policies in Romania, using the public verification API on [padrom.ro](https://www.padrom.ro).

## Features

- Verify PAD policy status (Active / Expired / Not Found)
- Policy expiry date sensor
- Days until expiry sensor (countdown)
- Binary sensor for policy validity (ON when valid)
- Detailed attributes: insurer, address, coverage amount, premium
- Support for all policy series (RA-002 through RX3740)
- Automatic daily refresh (configurable 1 hour to 7 days)
- Full Romanian and English translations

## Sensors

| Sensor | Type | Description |
|--------|------|-------------|
| Policy Status | sensor | Policy state: Active, Expired, Not Found |
| Policy Expiry | sensor | Expiry date of the policy |
| Days Until Expiry | sensor | Days remaining until expiry |
| Policy Valid | binary_sensor | ON when policy is active and valid |

All sensors share a device representing the PAD policy, with attributes including insurer, insured address, coverage amount, and premium.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click **Integrations**
3. Click the 3-dot menu > **Custom repositories**
4. Add: `https://github.com/emanuelbesliu/homeassistant-pad`
5. Category: **Integration**
6. Search for "PAD Romania" and install

### Manual

```bash
cd /config/custom_components
git clone https://github.com/emanuelbesliu/homeassistant-pad.git pad_tmp
mv pad_tmp/custom_components/pad .
rm -rf pad_tmp
```

## Configuration

1. Restart Home Assistant
2. Go to **Settings > Devices & Services > Add Integration**
3. Search for **PAD Romania**
4. Enter:
   - **Policy series** — select from dropdown (e.g. RA-065)
   - **Policy number** — digits only
   - **CNP / CUI** — personal ID or company registration number
   - **Policy name** — optional friendly name
   - **Update interval** — how often to check (default: 24 hours)
5. Click Submit

### Options

After setup, you can adjust the update interval from the integration's options.

## Example Automation

```yaml
alias: "PAD Policy Expiring Soon"
description: "Notify when PAD policy expires in less than 30 days"
triggers:
  - trigger: numeric_state
    entity_id: sensor.pad_ra_065_00243241690_days_until_expiry
    below: 30
actions:
  - action: notify.mobile_app
    data:
      title: "PAD Policy Expiring"
      message: >-
        Your PAD policy expires in
        {{ states('sensor.pad_ra_065_00243241690_days_until_expiry') }} days.
        Renew at padrom.ro.
```

## Requirements

- Home Assistant 2024.1.0 or newer
- Network access to padrom.ro

## Notes

- The integration queries the public padrom.ro verification form
- Data is fetched via POST requests to the XF-framework AJAX endpoint
- "Not found" does not necessarily mean invalid — the policy might use a different series/number format
- Response HTML parsing uses multiple strategies (tables, dt/dd, labeled spans, regex fallback) and may need refinement for edge cases

## Support

- [Report an issue](https://github.com/emanuelbesliu/homeassistant-pad/issues)
- [HACS info page](info.md)

## License

MIT
