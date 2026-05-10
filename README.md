# EasyAvahi

A small Python library wrapping mDNS service discovery and publication behind a clean abstract interface. Built to understand mDNS properly and end up with a class you can use to publish, browse, and test against in a few lines.

## What it does

mDNS (multicast DNS) is the protocol behind zero-config service discovery on local networks — printers advertising themselves, AirPlay and Chromecast pairing, IoT devices and gateways finding each other. Python has two common routes for it: the `zeroconf` library (pure Python, cross-platform) and Avahi via D-Bus (native on Linux). EasyAvahi wraps both behind one interface so callers don't have to care which one is in use.

## Installation

```bash
# Cross-platform minimum
pip install zeroconf

# Linux with Avahi support (optional, gives you avahi-browse compatibility)
sudo apt-get install python3-dbus python3-gi avahi-daemon
# Note: the Avahi backend needs system Python, not pyenv/venv.
```

## Usage

```python
from AvahiClient import AvahiClient
from Interface import MdnsService

# Backend is auto-selected: Avahi D-Bus on Linux if available, zeroconf otherwise.
client = AvahiClient()

# Publish a service
service = MdnsService(
    name="my-service",
    service_type="_http._tcp",
    port=8080,
    txt_record={"version": "1.0"},
    domain="local",
    host="",
)
client.publish(service)

# Discover services of a given type
for s in client.browse("_http._tcp"):
    print(f"{s.name} at {s.host}:{s.port}")

# Cleanup
client.unpublish(service)
client.stop()
```

## Testing

`Test.py` runs a real-network integration test: publishes a service, browses for it, asserts the discovered service matches (name, type, port, TXT record), unpublishes, browses again, asserts it's gone. No mocks — it talks to the actual mDNS stack.

```bash
python3 Test.py
```

To watch services from outside the test process, `mdns_browse.py` is a standalone listener (think `avahi-browse -ar`, but pure Python and cross-platform):

```bash
# Terminal 1
python3 mdns_browse.py _http._tcp
# Terminal 2
python3 Test.py
```

Services appear (`+`) and disappear (`-`) in real time. Useful in WSL or anywhere `avahi-browse` doesn't see services published via `zeroconf`.

## Architecture

`AvahiInterface` is the abstract base. `AvahiClient` is the only class that implements it directly — it acts as a facade that auto-selects between two backends and delegates every call:

- **`AvahiDBusBackend`** — Linux only. Talks to the running `avahi-daemon` via D-Bus. Compatible with `avahi-browse` and other native Avahi tools.
- **`ZeroconfBackend`** — Cross-platform. Uses the pure-Python `zeroconf` library, which brings its own mDNS stack.

The two backends are duck-typed (same methods, not subclasses of `AvahiInterface`) — they're strategies behind the facade, not implementations of the interface itself.

File layout:

- `Interface.py` — `AvahiInterface` ABC + `MdnsService` dataclass.
- `AvahiClient.py` — Facade implementing `AvahiInterface`.
- `AvahiDBusBackend.py` / `ZeroconfBackend.py` — The two backends.
- `Test.py` — Integration test (runs against whichever backend gets selected).
- `mdns_browse.py` — Standalone listener tool, independent of the rest.

## Notes

**Avahi and the `zeroconf` library don't interoperate cleanly on the same Linux host.** Both want UDP port 5353; when `avahi-daemon` is running, services published via `zeroconf` won't show up to `avahi-browse`, and vice versa. That's why `AvahiClient` prefers the D-Bus backend on Linux when Avahi is present — it goes through the daemon instead of competing with it. An obstacle hit during development, not the design goal, but the reason the hybrid selector exists.

**WSL:** D-Bus / systemd are limited, so the D-Bus backend usually won't work there. `AvahiClient` falls back to `ZeroconfBackend` automatically. Use `mdns_browse.py` instead of `avahi-browse`.

## License

MIT — see [`LICENSE`](LICENSE).
