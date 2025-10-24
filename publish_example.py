#!/usr/bin/env python3
"""
Example service publisher.

This script publishes a test mDNS service and keeps it running.
Use this with mdns_browse.py to see how services appear/disappear.

Usage:
    # In terminal 1
    python3 mdns_browse.py _http._tcp

    # In terminal 2
    python3 publish_example.py
"""

import time
from AvahiClient import AvahiClient
from Interface import MdnsService


def main():
    print("=" * 70)
    print("Example Service Publisher")
    print("=" * 70)
    print()

    # Create client
    client = AvahiClient()

    # Create example service
    service = MdnsService(
        name="example-service",
        service_type="_http._tcp",
        port=8080,
        txt_record={
            "version": "1.0",
            "path": "/api",
            "description": "Example mDNS service"
        },
        domain="local",
        host=""
    )

    # Publish it
    print("Publishing service...")
    success = client.publish(service)

    if not success:
        print("Failed to publish service")
        return 1

    print()
    print("Service is now published!")
    print()
    print("In another terminal, run:")
    print("  python3 mdns_browse.py _http._tcp")
    print()
    print("You should see this service appear.")
    print()
    print("Press Ctrl+C to unpublish and exit.")
    print("=" * 70)

    try:
        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        print("Unpublishing service...")
        print("=" * 70)
        client.unpublish(service)
        client.stop()
        print("Done.")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
