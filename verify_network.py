#!/usr/bin/env python3
"""
Cross-verification script for mDNS services.

This script helps verify that services published by AvahiClient are
actually visible on the network using a separate zeroconf instance.

This is useful for:
- Testing in WSL where Avahi D-Bus may not work
- Verifying network visibility without native tools
- Cross-platform testing
"""

import sys
import time
import threading
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
from AvahiClient import AvahiClient
from Interface import MdnsService


class ServiceListener:
    """Listener for service discovery events."""

    def __init__(self):
        self.services = {}
        self.found_event = threading.Event()

    def update_service(self, zc: Zeroconf, type_: str, name: str):
        """Called when service information is updated."""
        info = zc.get_service_info(type_, name)
        if info:
            self.services[name] = info
            print(f"✓ Service discovered: {name}")
            print(f"  Port: {info.port}")
            if info.properties:
                print(f"  TXT records: {info.properties}")
            self.found_event.set()

    def add_service(self, zc: Zeroconf, type_: str, name: str):
        """Called when a service is added."""
        print(f"  → Found service: {name}")
        self.update_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str):
        """Called when a service is removed."""
        print(f"  ← Service removed: {name}")
        if name in self.services:
            del self.services[name]


def main():
    print("=" * 70)
    print("mDNS Cross-Verification Test")
    print("=" * 70)
    print()
    print("This test publishes a service with AvahiClient and verifies it")
    print("can be discovered by an independent zeroconf instance.")
    print()

    # Create test service
    test_service = MdnsService(
        name="cross-verify-test",
        service_type="_http._tcp",
        port=9999,
        txt_record={"test": "cross-verification", "version": "1.0"},
        domain="local",
        host=""
    )

    # Step 1: Publish with AvahiClient
    print("-" * 70)
    print("Step 1: Publishing service with AvahiClient")
    print("-" * 70)

    client = AvahiClient()
    success = client.publish(test_service)

    if not success:
        print("✗ Failed to publish service")
        return 1

    print()

    # Step 2: Try to discover with independent zeroconf
    print("-" * 70)
    print("Step 2: Discovering with independent zeroconf instance")
    print("-" * 70)
    print("(This simulates what avahi-browse would do)")
    print()

    listener = ServiceListener()
    zc = Zeroconf()

    try:
        browser = ServiceBrowser(
            zc,
            "_http._tcp.local.",
            listener
        )

        # Wait for discovery
        print("Waiting for service discovery (5 seconds)...")
        listener.found_event.wait(timeout=5.0)

        # Check results
        print()
        print("-" * 70)
        print("Results:")
        print("-" * 70)

        service_name = f"{test_service.name}._http._tcp.local."

        if service_name in listener.services:
            print("✓ SUCCESS: Service is visible on the network!")
            print()
            print(f"  Service: {test_service.name}")
            print(f"  Type: {test_service.service_type}")
            info = listener.services[service_name]
            print(f"  Port: {info.port}")
            if info.addresses:
                import socket
                addrs = [socket.inet_ntoa(a) for a in info.addresses]
                print(f"  Addresses: {', '.join(addrs)}")
            print()
            print("This means:")
            print("  - Your service IS being published correctly")
            print("  - It IS visible on the network")
            print("  - Other mDNS clients CAN discover it")
            print("  - avahi-browse SHOULD see it (if Avahi D-Bus works)")
            result = 0
        else:
            print("✗ FAILURE: Service not discovered")
            print()
            print("Found services:")
            if listener.services:
                for name in listener.services:
                    print(f"  - {name}")
            else:
                print("  (none)")
            print()
            print("This could mean:")
            print("  - Network interface detection issue")
            print("  - Firewall blocking multicast")
            print("  - zeroconf and avahi-daemon port conflict")
            result = 1

        browser.cancel()

    finally:
        # Cleanup
        print()
        print("-" * 70)
        print("Cleanup")
        print("-" * 70)

        client.unpublish(test_service)
        client.stop()
        zc.close()

        print("Done.")

    return result


if __name__ == "__main__":
    sys.exit(main())
