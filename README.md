# EasyAvahi

Cross-platform Python library for mDNS service discovery and publication.

## The Problem

**Avahi and zeroconf cannot coexist** - both listen on port 5353. This means:
- Using `zeroconf` on Linux where `avahi-daemon` runs → tools don't see each other
- `avahi-browse` won't see services published by `zeroconf`
- Python scripts can't see services published by Avahi

## The Solution

**Hybrid backend architecture** - automatically selects the best implementation:

- **Linux with Avahi**: Uses D-Bus → compatible with `avahi-browse`
- **Windows/WSL/Fallback**: Uses zeroconf → cross-platform

Same code, works everywhere.

## Installation

```bash
# Minimum (cross-platform)
pip install zeroconf

# Linux with Avahi support (optional, for avahi-browse compatibility)
sudo apt-get install python3-dbus python3-gi avahi-daemon
# Note: Must use system Python, not pyenv/venv
```

## Usage

```python
from AvahiClient import AvahiClient
from Interface import MdnsService

# Create client (auto-selects backend)
client = AvahiClient()

# Publish service
service = MdnsService(
    name="my-service",
    service_type="_http._tcp",
    port=8080,
    txt_record={"version": "1.0"},
    domain="local",
    host=""
)
client.publish(service)

# Discover services
services = client.browse("_http._tcp")
for s in services:
    print(f"{s.name} at {s.host}:{s.port}")

# Cleanup
client.unpublish(service)
client.stop()
```

## Testing

### Run the integration test:
```bash
python3 Test.py
```

### Verify services on the network:

**Option 1 - With mdns_browse.py (recommended for WSL/testing):**
```bash
# Terminal 1 - Run browser
python3 mdns_browse.py _http._tcp

# Terminal 2 - Run your code or test
python3 Test.py
```

Services will appear (+) and disappear (-) in real-time.

**Option 2 - With native tools (Linux with Avahi D-Bus only):**
```bash
# Terminal 1
avahi-browse -ar

# Terminal 2
python3 Test.py
```

**Option 3 - With native tools (Windows with Bonjour):**
```bash
# Terminal 1
dns-sd -B _http._tcp

# Terminal 2
python3 Test.py
```

## Architecture

```
EasyAvahi/
├── Interface.py              # Abstract interface
├── AvahiClient.py           # Main client with auto backend selection
├── AvahiDBusBackend.py      # Linux/Avahi via D-Bus
├── ZeroconfBackend.py       # Cross-platform zeroconf
├── Test.py                  # Integration test
└── mdns_browse.py           # Independent browser tool
```

## Why mdns_browse.py?

`mdns_browse.py` is an **independent** tool (like `avahi-browse`) that:
- Only **listens** for services (doesn't publish)
- Works in WSL where `avahi-browse` can't see zeroconf services
- Perfect for testing: browser in one terminal, publisher in another
- Cross-platform, pure Python

## WSL Considerations

WSL has limitations with D-Bus/systemd. **Recommended approach:**
- Use zeroconf backend (works perfectly)
- Use `mdns_browse.py` instead of `avahi-browse`
- Don't worry about D-Bus in WSL

## Requirements

### Cross-platform (minimum)
- Python 3.7+
- zeroconf

### Linux with Avahi D-Bus support
- Python 3.7+ (system Python, not pyenv)
- python3-dbus
- python3-gi
- avahi-daemon (running)
- zeroconf (fallback)

## License

MIT License
