import time
import socket
import platform
from threading import Event
from typing import Dict, List, Optional
from Interface import AvahiInterface, MdnsService


class AvahiClient(AvahiInterface):
    """
    Real implementation of AvahiInterface with automatic backend selection.

    This implementation automatically chooses the best backend:
    - Linux with Avahi: Uses D-Bus to communicate with avahi-daemon
    - Windows/Others: Uses zeroconf library

    This ensures compatibility with native tools like avahi-browse on Linux
    and dns-sd/Bonjour on Windows.
    """

    def __init__(self):
        """Initialize the Avahi client with automatic backend selection."""
        self.backend = None
        self._select_backend()

    def _select_backend(self):
        """Select the appropriate backend based on the platform."""
        # Try Avahi D-Bus first (Linux)
        if platform.system() == "Linux":
            try:
                from AvahiDBusBackend import AvahiDBusBackend
                self.backend = AvahiDBusBackend()
                self.log("Using Avahi D-Bus backend (native Linux)")
                return
            except Exception as e:
                self.log(f"Avahi D-Bus not available: {e}")

        # Fallback to zeroconf
        try:
            from ZeroconfBackend import ZeroconfBackend
            self.backend = ZeroconfBackend()
            self.log("Using zeroconf backend (cross-platform)")
        except Exception as e:
            raise RuntimeError(f"No suitable backend available: {e}")

    def start(self) -> None:
        """Start the Avahi client."""
        self.backend.start()

    def stop(self) -> None:
        """Stop the Avahi client and clean up resources."""
        self.backend.stop()

    def publish(self, service: MdnsService) -> bool:
        """Publish an mDNS service on the network."""
        return self.backend.publish(service)

    def unpublish(self, service: MdnsService) -> bool:
        """Remove a published mDNS service from the network."""
        return self.backend.unpublish(service)

    def browse(self, service_type: str) -> list[MdnsService]:
        """Discover and resolve all services of the specified type on the network."""
        return self.backend.browse(service_type)

    def clear_cache(self) -> None:
        """Clear any cached service discovery data."""
        self.backend.clear_cache()

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[AvahiClient] {message}")
