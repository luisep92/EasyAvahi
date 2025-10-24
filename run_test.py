#!/usr/bin/env python3
"""
Script to run the Avahi integration test.
"""

import sys
from AvahiClient import AvahiClient
from Test import test_publish_browse_unpublish

def main():
    """Run the test with a real AvahiClient instance."""
    print("=" * 60)
    print("Starting Avahi Integration Test")
    print("=" * 60)

    # Create an instance of AvahiClient
    avahi_client = AvahiClient()

    try:
        # Run the test
        test_publish_browse_unpublish(avahi_client)

        print("=" * 60)
        print("TEST PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print("=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        return 1

    except Exception as e:
        print("=" * 60)
        print(f"TEST ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up
        print("\nCleaning up...")
        avahi_client.stop()

if __name__ == "__main__":
    sys.exit(main())
