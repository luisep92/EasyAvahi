#!/usr/bin/env python3
"""
Standalone mDNS Service Browser

This is an INDEPENDENT tool that monitors mDNS services on your network,
similar to 'avahi-browse -ar'. It uses zeroconf to listen for services.

WHY THIS EXISTS:
- In WSL/environments where avahi-browse doesn't work with zeroconf services
- For testing: Run this in one terminal, your service publisher in another
- Cross-platform alternative to avahi-browse that uses pure Python

USE CASE:
  Terminal 1: python3 mdns_browse.py _http._tcp
  Terminal 2: python3 Test.py (or your service publisher)

  The browser will show services as they appear (+) and disappear (-).

USAGE:
    # Browse all common service types
    python3 mdns_browse.py

    # Browse specific service type (recommended for testing)
    python3 mdns_browse.py _http._tcp

    # Browse multiple service types
    python3 mdns_browse.py _http._tcp _ssh._tcp

IMPORTANT:
- This script is INDEPENDENT from AvahiClient
- It only LISTENS, it does NOT publish
- Use it to verify services published by your code
"""

import sys
import time
import socket
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange


class ServiceListener:
    """Listener that reports service changes like avahi-browse."""

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.services = {}

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service is discovered."""
        print(f"+ {service_type} {name}")

        # Resolve service details
        info = zeroconf.get_service_info(service_type, name)
        if info and self.verbose:
            # Parse service name (remove type suffix)
            short_name = name
            if name.endswith('.' + service_type):
                short_name = name[:-len('.' + service_type)]

            print(f"   hostname = [{info.server}]")

            # Show all addresses
            if info.addresses:
                for addr in info.addresses:
                    addr_str = socket.inet_ntoa(addr)
                    print(f"   address = [{addr_str}]")

            print(f"   port = [{info.port}]")

            # Show TXT records
            if info.properties:
                for key, value in info.properties.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    print(f"   txt = [\"{key_str}={value_str}\"]")

            self.services[name] = info

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service disappears."""
        print(f"- {service_type} {name}")
        if name in self.services:
            del self.services[name]

    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when service info is updated."""
        # Just treat as re-add
        pass


def main():
    """Main entry point."""

    # Default common service types (like avahi-browse -ar)
    default_types = [
        "_http._tcp.local.",
        "_https._tcp.local.",
        "_ssh._tcp.local.",
        "_ftp._tcp.local.",
        "_smb._tcp.local.",
        "_afpovertcp._tcp.local.",
        "_workstation._tcp.local.",
        "_printer._tcp.local.",
        "_ipp._tcp.local.",
    ]

    # Parse command line arguments
    if len(sys.argv) > 1:
        # User specified service types
        service_types = []
        for arg in sys.argv[1:]:
            if arg.endswith('.local.'):
                service_types.append(arg)
            elif '.' in arg:
                service_types.append(arg + '.local.')
            else:
                service_types.append(arg + '.local.')
    else:
        service_types = default_types

    print("=" * 70)
    print("mDNS Service Browser (zeroconf)")
    print("=" * 70)
    print(f"Browsing for service types:")
    for st in service_types:
        print(f"  - {st}")
    print()
    print("Services will appear below as they are discovered.")
    print("Press Ctrl+C to stop.")
    print("=" * 70)
    print()

    # Create zeroconf instance
    zeroconf = Zeroconf()
    listener = ServiceListener()

    # Create browsers for each service type
    browsers = []
    for service_type in service_types:
        browser = ServiceBrowser(
            zeroconf,
            service_type,
            listener
        )
        browsers.append(browser)

    try:
        # Keep running until interrupted
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("Stopping...")
        print("=" * 70)

    finally:
        # Cleanup
        for browser in browsers:
            browser.cancel()
        zeroconf.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
