# EasyAvahi

A cross-platform Python library for mDNS service discovery and publication that works seamlessly on both Linux (with Avahi) and Windows (with Bonjour/zeroconf).

## The Problem

mDNS services can be discovered and published using different implementations:
- **Linux**: Avahi daemon (native)
- **Windows**: Bonjour service (Apple)
- **Cross-platform**: python-zeroconf library

However, **Avahi and zeroconf cannot coexist** on the same machine because they both try to listen on the same multicast port (5353). This means:
- If you use `zeroconf` library on Linux where `avahi-daemon` is running, they won't see each other
- Tools like `avahi-browse` won't see services published by `zeroconf`
- Your Python script won't see services published by Avahi

## The Solution

EasyAvahi automatically selects the best backend for your platform:

### Linux (with Avahi installed)
- **Uses**: Avahi D-Bus backend
- **Communicates with**: Native `avahi-daemon` via D-Bus
- **Compatible with**: `avahi-browse`, `avahi-publish`, and all Avahi-based tools
- **Sees**: All mDNS services on the network (published by any implementation)

### Windows / Other platforms
- **Uses**: Zeroconf backend
- **Independent**: Pure Python implementation
- **Compatible with**: `dns-sd`, Bonjour Browser, and other mDNS clients
- **Sees**: All mDNS services on the network (published by any implementation)

## Installation

### Basic Installation (cross-platform)

```bash
pip install zeroconf
```

### Linux with Avahi Support

```bash
# Install system packages
sudo apt-get install python3-dbus python3-gi avahi-daemon

# Install zeroconf as fallback
pip install zeroconf
```

### Windows

```bash
# Only zeroconf needed
pip install zeroconf

# Optionally install Bonjour Print Services for dns-sd tool
# Download from: https://support.apple.com/kb/DL999
```

## Usage

```python
from AvahiClient import AvahiClient
from Interface import MdnsService

# Create client (automatically selects best backend)
client = AvahiClient()

# Publish a service
service = MdnsService(
    name="my-service",
    service_type="_http._tcp",
    port=8080,
    txt_record={"version": "1.0", "path": "/api"},
    domain="local",
    host=""
)

client.publish(service)

# Discover services
services = client.browse("_http._tcp")
for s in services:
    print(f"Found: {s.name} at {s.host}:{s.port}")

# Cleanup
client.unpublish(service)
client.stop()
```

## Verifying with Native Tools

### Linux - Using avahi-browse

When using the Avahi D-Bus backend on Linux, your services will be visible to `avahi-browse`:

```bash
# Browse all services
avahi-browse -ar

# Browse specific service type
avahi-browse _http._tcp -r

# You should see services published by your Python script
```

### Windows - Using dns-sd

With Bonjour installed, you can use `dns-sd`:

```bash
# Browse all services
dns-sd -B _services._dns-sd._udp

# Browse specific service type
dns-sd -B _http._tcp

# Resolve a specific service
dns-sd -L "my-service" _http._tcp
```

## How It Works

### Backend Selection

```
┌─────────────────┐
│  AvahiClient    │
└────────┬────────┘
         │
         ├─ Linux? ───┐
         │            │
         │            ├─ Try Avahi D-Bus
         │            │  ├─ Success → AvahiDBusBackend
         │            │  └─ Fail → ZeroconfBackend
         │            │
         └─ Windows/Other → ZeroconfBackend
```

### Network Communication

Both backends use standard mDNS protocol (RFC 6762):
- Multicast group: `224.0.0.251` (IPv4) or `ff02::fb` (IPv6)
- Port: `5353`
- All implementations can see each other on the network

### Why This Matters

**Wrong approach (doesn't work):**
```python
# On Linux with avahi-daemon running
from zeroconf import Zeroconf

zc = Zeroconf()  # Opens its own socket on port 5353
# Problem: avahi-daemon already has port 5353
# Result: They don't see each other's services
```

**Correct approach (EasyAvahi):**
```python
from AvahiClient import AvahiClient

client = AvahiClient()  # On Linux: uses D-Bus to talk to avahi-daemon
                       # On Windows: uses zeroconf
# Result: Compatible with native tools on each platform
```

## Architecture

```
EasyAvahi/
├── Interface.py              # Abstract interface definition
├── AvahiClient.py           # Main client with backend selection
├── AvahiDBusBackend.py      # Linux/Avahi implementation via D-Bus
├── ZeroconfBackend.py       # Cross-platform implementation
├── Test.py                  # Integration tests
└── run_test.py              # Test runner
```

## Requirements

### Minimum (Cross-platform)
- Python 3.7+
- zeroconf

### Linux with Avahi support
- Python 3.7+
- python3-dbus
- python3-gi
- avahi-daemon (running)
- zeroconf (fallback)

### Windows
- Python 3.7+
- zeroconf
- Bonjour Service (optional, for dns-sd tool)

## Testing

```bash
# Run the integration test
python3 run_test.py

# The test will:
# 1. Publish a test service
# 2. Discover it
# 3. Verify TXT records
# 4. Unpublish it
# 5. Verify it's gone

# You can verify in parallel with native tools:
# Linux:   avahi-browse _http._tcp -r
# Windows: dns-sd -B _http._tcp
```

## Troubleshooting

### Linux: "Avahi D-Bus not available"

This is normal if D-Bus bindings aren't installed. The client will automatically fall back to zeroconf.

To use native Avahi:
```bash
sudo apt-get install python3-dbus python3-gi avahi-daemon
```

### Services not visible to avahi-browse

If using zeroconf backend on Linux, services won't be visible to `avahi-browse` because both try to use the same port.

Solution: Install D-Bus bindings to use native Avahi backend (see above).

### Windows: "dns-sd not found"

Install Bonjour Print Services or iTunes (includes Bonjour).

### No network interface found

The client detects network interfaces automatically. If it can't find any, it falls back to localhost (127.0.0.1), which means services won't be visible on the network.

Check your network connection and firewall settings.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure:
- Code works on both Linux and Windows
- Tests pass on both platforms
- Native tool compatibility is maintained (avahi-browse, dns-sd)
