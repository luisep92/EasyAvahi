import time
import socket
from threading import Event
from typing import Dict, List, Optional
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceStateChange
from Interface import MdnsService


class ZeroconfBackend:
    """
    Zeroconf backend for mDNS service discovery and publication.

    This backend uses the zeroconf library (pure Python implementation).
    Works on any platform but runs its own mDNS stack (doesn't use system Avahi/Bonjour).
    """

    def __init__(self):
        """Initialize the zeroconf backend."""
        self.zeroconf: Optional[Zeroconf] = None
        self.published_services: Dict[tuple, ServiceInfo] = {}
        self.discovered_services: List[MdnsService] = []
        self.browser: Optional[ServiceBrowser] = None
        self.browse_complete: Event = Event()
        self.start()

    def start(self) -> None:
        """Start the zeroconf client."""
        if self.zeroconf is None:
            self.zeroconf = Zeroconf()
            self.log("Zeroconf client started")

    def stop(self) -> None:
        """Stop the zeroconf client and clean up resources."""
        for service_key in list(self.published_services.keys()):
            name, service_type = service_key
            service = MdnsService(
                name=name,
                service_type=service_type,
                port=0,
                txt_record={}
            )
            self.unpublish(service)

        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
            self.log("Zeroconf client stopped")

    def publish(self, service: MdnsService) -> bool:
        """Publish an mDNS service."""
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return False

        try:
            hostname = socket.gethostname()
            if service.host:
                hostname = service.host

            addresses = self._get_network_addresses()

            properties = {}
            for key, value in service.txt_record.items():
                properties[key] = value.encode('utf-8') if isinstance(value, str) else value

            full_service_type = service.service_type
            if not full_service_type.endswith('.'):
                full_service_type += f".{service.domain}."

            service_info = ServiceInfo(
                full_service_type,
                f"{service.name}.{full_service_type}",
                port=service.port,
                properties=properties,
                addresses=addresses,
                server=f"{hostname}.{service.domain}."
            )

            self.zeroconf.register_service(service_info)

            service_key = (service.name, service.service_type)
            self.published_services[service_key] = service_info

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
        """Remove a published mDNS service."""
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return False

        try:
            service_key = (service.name, service.service_type)

            if service_key not in self.published_services:
                self.log(f"Service '{service.name}' not found in published services")
                return False

            service_info = self.published_services[service_key]
            self.zeroconf.unregister_service(service_info)

            del self.published_services[service_key]

            self.log(f"Service '{service.name}' unpublished successfully")
            self.log(f"  └─ Type: {service.service_type}")
            self.log(f"  └─ Removed from network")
            return True

        except Exception as e:
            self.log(f"Error unpublishing service: {e}")
            return False

    def browse(self, service_type: str) -> list[MdnsService]:
        """Discover and resolve all services of the specified type."""
        if not self.zeroconf:
            self.log("Error: Zeroconf not initialized")
            return []

        self.discovered_services = []
        self.browse_complete.clear()

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
            if state_change is ServiceStateChange.Added:
                self.log(f"  └─ Found service, resolving: {name}")
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    self._process_service_info(info, service_type)
                else:
                    self.log(f"  └─ Warning: Could not resolve service {name}")

        try:
            browser = ServiceBrowser(
                self.zeroconf,
                full_service_type,
                handlers=[on_service_state_change]
            )

            time.sleep(3)
            browser.cancel()

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
            name = info.name
            if name.endswith('.' + service_type):
                name = name[:-len('.' + service_type)]

            txt_record = {}
            if info.properties:
                for key, value in info.properties.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    txt_record[key_str] = value_str

            stype = service_type
            if stype.endswith('.local.'):
                stype = stype[:-7]

            server = info.server if info.server else ""
            if server.endswith('.local.'):
                domain = "local"
                host = server[:-7]
            else:
                domain = "local"
                host = server

            mdns_service = MdnsService(
                name=name,
                service_type=stype,
                port=info.port,
                txt_record=txt_record,
                domain=domain,
                host=host
            )

            self.discovered_services.append(mdns_service)

            self.log(f"✓ Resolved service: {name}")
            self.log(f"    ├─ Type: {stype}")
            self.log(f"    ├─ Port: {info.port}")
            self.log(f"    ├─ Host: {host}.{domain}.")

            if info.addresses:
                addr_strs = [socket.inet_ntoa(addr) for addr in info.addresses]
                self.log(f"    ├─ Address(es): {', '.join(addr_strs)}")

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

    def _get_network_addresses(self) -> list:
        """Get real network IP addresses (not localhost)."""
        addresses = []

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            if local_ip and not local_ip.startswith("127."):
                addresses.append(socket.inet_aton(local_ip))
                self.log(f"  └─ Detected network IP: {local_ip}")
        except Exception as e:
            self.log(f"  └─ Could not detect default route IP: {e}")

        try:
            hostname = socket.gethostname()
            for addr_info in socket.getaddrinfo(hostname, None):
                if addr_info[0] == socket.AF_INET:
                    ip = addr_info[4][0]
                    if not ip.startswith("127."):
                        ip_bytes = socket.inet_aton(ip)
                        if ip_bytes not in addresses:
                            addresses.append(ip_bytes)
                            self.log(f"  └─ Found interface IP: {ip}")
        except Exception as e:
            self.log(f"  └─ Could not enumerate interfaces: {e}")

        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get('addr')
                        if ip and not ip.startswith("127."):
                            ip_bytes = socket.inet_aton(ip)
                            if ip_bytes not in addresses:
                                addresses.append(ip_bytes)
                                self.log(f"  └─ Found interface IP (netifaces): {ip}")
        except ImportError:
            pass
        except Exception as e:
            self.log(f"  └─ Error using netifaces: {e}")

        if not addresses:
            self.log("  └─ Warning: No network interfaces found, using localhost")
            addresses.append(socket.inet_aton("127.0.0.1"))

        return addresses

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[ZeroconfBackend] {message}")
