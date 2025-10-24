import time
import socket
from threading import Event
from typing import Dict, List, Optional
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceStateChange
from Interface import AvahiInterface, MdnsService


class AvahiClient(AvahiInterface):
    """
    Real implementation of AvahiInterface using python-zeroconf.

    This implementation uses the zeroconf library (pure Python implementation of mDNS/DNS-SD)
    to publish and discover services on the network.
    """

    def __init__(self):
        """Initialize the Avahi client."""
        self.zeroconf: Optional[Zeroconf] = None
        self.published_services: Dict[tuple, ServiceInfo] = {}
        self.discovered_services: List[MdnsService] = []
        self.browser: Optional[ServiceBrowser] = None
        self.browse_complete: Event = Event()

        # Start the client automatically
        self.start()

    def start(self) -> None:
        """Start the Avahi client."""
        if self.zeroconf is None:
            self.zeroconf = Zeroconf()
            self.log("Zeroconf client started")

    def stop(self) -> None:
        """Stop the Avahi client and clean up resources."""
        # Unpublish all services
        for service_key in list(self.published_services.keys()):
            name, service_type = service_key
            service = MdnsService(
                name=name,
                service_type=service_type,
                port=0,
                txt_record={}
            )
            self.unpublish(service)

        # Close zeroconf
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
            self.log("Zeroconf client stopped")

    def publish(self, service: MdnsService) -> bool:
        """
        Publish an mDNS service on the network.

        Args:
            service: The MdnsService instance to publish

        Returns:
            True if the service was successfully published, False otherwise
        """
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return False

        try:
            # Get local IP address
            hostname = socket.gethostname()
            if service.host:
                hostname = service.host

            # Get local IP addresses
            try:
                local_ip = socket.gethostbyname(hostname)
                addresses = [socket.inet_aton(local_ip)]
            except Exception:
                # Fallback to getting all local IPs
                addresses = []
                for addr_info in socket.getaddrinfo(socket.gethostname(), None):
                    if addr_info[0] == socket.AF_INET:  # IPv4 only for now
                        addresses.append(socket.inet_aton(addr_info[4][0]))
                if not addresses:
                    addresses = [socket.inet_aton("127.0.0.1")]

            # Convert TXT record to bytes
            properties = {}
            for key, value in service.txt_record.items():
                properties[key] = value.encode('utf-8') if isinstance(value, str) else value

            # Create the full service name
            full_service_type = service.service_type
            if not full_service_type.endswith('.'):
                full_service_type += f".{service.domain}."

            # Create ServiceInfo
            service_info = ServiceInfo(
                full_service_type,
                f"{service.name}.{full_service_type}",
                port=service.port,
                properties=properties,
                addresses=addresses,
                server=f"{hostname}.{service.domain}."
            )

            # Register the service
            self.zeroconf.register_service(service_info)

            # Store the service info for later unpublishing
            service_key = (service.name, service.service_type)
            self.published_services[service_key] = service_info

            # Log detailed information
            addr_strs = [socket.inet_ntoa(addr) for addr in addresses]
            self.log(f"Service '{service.name}' published successfully")
            self.log(f"  └─ Type: {service.service_type}")
            self.log(f"  └─ Port: {service.port}")
            self.log(f"  └─ Host: {hostname}.{service.domain}.")
            self.log(f"  └─ Address(es): {', '.join(addr_strs)}")
            if service.txt_record:
                self.log(f"  └─ TXT records: {service.txt_record}")

            return True

        except Exception as e:
            self.log(f"Error publishing service: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unpublish(self, service: MdnsService) -> bool:
        """
        Remove a published mDNS service from the network.

        Args:
            service: The MdnsService instance to unpublish

        Returns:
            True if the service was successfully unpublished, False otherwise
        """
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return False

        try:
            service_key = (service.name, service.service_type)

            if service_key not in self.published_services:
                self.log(f"Service '{service.name}' not found in published services")
                return False

            # Get the service info and unregister it
            service_info = self.published_services[service_key]
            self.zeroconf.unregister_service(service_info)

            # Remove from our tracking dictionary
            del self.published_services[service_key]

            self.log(f"Service '{service.name}' unpublished successfully")
            self.log(f"  └─ Type: {service.service_type}")
            self.log(f"  └─ Removed from network")
            return True

        except Exception as e:
            self.log(f"Error unpublishing service: {e}")
            return False

    def browse(self, service_type: str) -> list[MdnsService]:
        """
        Discover and resolve all services of the specified type on the network.

        Args:
            service_type: The service type to browse for (e.g., '_http._tcp')

        Returns:
            A list of fully resolved MdnsService instances found on the network
        """
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return []

        # Clear previous discoveries
        self.discovered_services = []
        self.browse_complete.clear()

        # Ensure service type ends with .local.
        full_service_type = service_type
        if not full_service_type.endswith('.'):
            full_service_type += ".local."

        self.log(f"Starting browse for service type: {full_service_type}")
        self.log("  └─ Scanning network for services...")

        def on_service_state_change(
            zeroconf: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange
        ) -> None:
            """Callback for service state changes."""
            if state_change is ServiceStateChange.Added:
                self.log(f"  └─ Found service, resolving: {name}")
                # Get service info
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    self._process_service_info(info, service_type)
                else:
                    self.log(f"  └─ Warning: Could not resolve service {name}")

        try:
            # Create a service browser
            browser = ServiceBrowser(
                self.zeroconf,
                full_service_type,
                handlers=[on_service_state_change]
            )

            # Wait for services to be discovered
            # Give it 3 seconds to find services
            time.sleep(3)

            # Stop the browser
            browser.cancel()

            # Log summary
            self.log(f"Browse completed: found {len(self.discovered_services)} service(s)")

            return self.discovered_services

        except Exception as e:
            self.log(f"Error browsing services: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _process_service_info(self, info: ServiceInfo, service_type: str) -> None:
        """Process a discovered service and add it to the list."""
        try:
            # Extract service name (remove service type suffix)
            name = info.name
            if name.endswith('.' + service_type):
                name = name[:-len('.' + service_type)]

            # Extract TXT record
            txt_record = {}
            if info.properties:
                for key, value in info.properties.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    txt_record[key_str] = value_str

            # Extract service type without .local.
            stype = service_type
            if stype.endswith('.local.'):
                stype = stype[:-7]

            # Extract domain and host
            server = info.server if info.server else ""
            if server.endswith('.local.'):
                domain = "local"
                host = server[:-7]
            else:
                domain = "local"
                host = server

            # Create MdnsService instance
            mdns_service = MdnsService(
                name=name,
                service_type=stype,
                port=info.port,
                txt_record=txt_record,
                domain=domain,
                host=host
            )

            self.discovered_services.append(mdns_service)

            # Log detailed service information
            self.log(f"✓ Resolved service: {name}")
            self.log(f"    ├─ Type: {stype}")
            self.log(f"    ├─ Port: {info.port}")
            self.log(f"    ├─ Host: {host}.{domain}.")

            # Log addresses
            if info.addresses:
                addr_strs = [socket.inet_ntoa(addr) for addr in info.addresses]
                self.log(f"    ├─ Address(es): {', '.join(addr_strs)}")

            # Log TXT records
            if txt_record:
                self.log(f"    └─ TXT records:")
                for key, value in txt_record.items():
                    self.log(f"        └─ {key} = {value}")
            else:
                self.log(f"    └─ TXT records: (none)")

        except Exception as e:
            self.log(f"Error processing service info: {e}")

    def clear_cache(self) -> None:
        """Clear any cached service discovery data."""
        self.discovered_services = []

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[AvahiClient] {message}")
