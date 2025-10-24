import time
import dbus
from gi.repository import GLib
from threading import Thread, Event
from typing import Dict, List
from Interface import MdnsService


# Avahi constants
DBUS_NAME = "org.freedesktop.Avahi"
DBUS_INTERFACE_SERVER = DBUS_NAME + ".Server"
DBUS_PATH_SERVER = "/"
DBUS_INTERFACE_ENTRY_GROUP = DBUS_NAME + ".EntryGroup"
DBUS_INTERFACE_SERVICE_BROWSER = DBUS_NAME + ".ServiceBrowser"
DBUS_INTERFACE_SERVICE_RESOLVER = DBUS_NAME + ".ServiceResolver"

IF_UNSPEC = -1
PROTO_UNSPEC = -1
PROTO_INET = 0
PROTO_INET6 = 1
LOOKUP_RESULT_LOCAL = 8


class AvahiDBusBackend:
    """
    Avahi D-Bus backend for mDNS service discovery and publication.

    This backend communicates with the native Avahi daemon via D-Bus.
    Only works on Linux with Avahi installed, but ensures compatibility
    with avahi-browse and other Avahi-based tools.
    """

    def __init__(self):
        """Initialize the Avahi D-Bus backend."""
        self.bus = dbus.SystemBus()
        self.server = dbus.Interface(
            self.bus.get_object(DBUS_NAME, DBUS_PATH_SERVER),
            DBUS_INTERFACE_SERVER
        )

        self.published_services: Dict[tuple, dbus.Interface] = {}
        self.discovered_services: List[MdnsService] = []

        self.loop = None
        self.loop_thread = None
        self.running = False

        self.start()

    def start(self) -> None:
        """Start the Avahi D-Bus client and event loop."""
        if not self.running:
            self.running = True
            self.loop = GLib.MainLoop()
            self.loop_thread = Thread(target=self._run_loop, daemon=True)
            self.loop_thread.start()
            self.log("Avahi D-Bus client started")

    def _run_loop(self):
        """Run the GLib main loop in a separate thread."""
        context = self.loop.get_context()
        while self.running:
            context.iteration(True)

    def stop(self) -> None:
        """Stop the Avahi D-Bus client and clean up resources."""
        for service_key in list(self.published_services.keys()):
            name, service_type = service_key
            service = MdnsService(
                name=name,
                service_type=service_type,
                port=0,
                txt_record={}
            )
            self.unpublish(service)

        self.running = False
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=1.0)

        self.log("Avahi D-Bus client stopped")

    def publish(self, service: MdnsService) -> bool:
        """Publish an mDNS service via Avahi D-Bus."""
        try:
            group = dbus.Interface(
                self.bus.get_object(
                    DBUS_NAME,
                    self.server.EntryGroupNew()
                ),
                DBUS_INTERFACE_ENTRY_GROUP
            )

            txt_record = []
            for key, value in service.txt_record.items():
                txt_record.append(f"{key}={value}".encode('utf-8'))

            group.AddService(
                IF_UNSPEC,
                PROTO_UNSPEC,
                dbus.UInt32(0),
                service.name,
                service.service_type,
                service.domain,
                service.host,
                dbus.UInt16(service.port),
                txt_record
            )

            group.Commit()

            service_key = (service.name, service.service_type)
            self.published_services[service_key] = group

            self.log(f"Service '{service.name}' published successfully")
            self.log(f"  └─ Type: {service.service_type}")
            self.log(f"  └─ Port: {service.port}")
            self.log(f"  └─ Domain: {service.domain}")
            if service.txt_record:
                self.log(f"  └─ TXT records: {service.txt_record}")

            return True

        except Exception as e:
            self.log(f"Error publishing service: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unpublish(self, service: MdnsService) -> bool:
        """Remove a published mDNS service via Avahi D-Bus."""
        try:
            service_key = (service.name, service.service_type)

            if service_key not in self.published_services:
                self.log(f"Service '{service.name}' not found in published services")
                return False

            group = self.published_services[service_key]
            group.Reset()

            del self.published_services[service_key]

            self.log(f"Service '{service.name}' unpublished successfully")
            self.log(f"  └─ Type: {service.service_type}")
            self.log(f"  └─ Removed from network")
            return True

        except Exception as e:
            self.log(f"Error unpublishing service: {e}")
            return False

    def browse(self, service_type: str) -> list[MdnsService]:
        """Discover and resolve all services via Avahi D-Bus."""
        self.discovered_services = []
        resolution_complete = Event()
        pending_resolutions = set()

        def service_resolved(interface, protocol, name, stype, domain, host, aprotocol,
                           address, port, txt, flags):
            """Callback when a service is fully resolved."""
            txt_record = {}
            for txt_item in txt:
                try:
                    txt_str = bytes(txt_item).decode('utf-8')
                    if '=' in txt_str:
                        key, value = txt_str.split('=', 1)
                        txt_record[key] = value
                except Exception as e:
                    self.log(f"Error parsing TXT record: {e}")

            mdns_service = MdnsService(
                name=str(name),
                service_type=str(stype),
                port=int(port),
                txt_record=txt_record,
                domain=str(domain),
                host=str(host)
            )

            self.discovered_services.append(mdns_service)

            self.log(f"✓ Resolved service: {name}")
            self.log(f"    ├─ Type: {stype}")
            self.log(f"    ├─ Port: {port}")
            self.log(f"    ├─ Host: {host}.{domain}.")
            self.log(f"    ├─ Address: {address}")

            if txt_record:
                self.log(f"    └─ TXT records:")
                for key, value in txt_record.items():
                    self.log(f"        └─ {key} = {value}")
            else:
                self.log(f"    └─ TXT records: (none)")

            service_key = (interface, protocol, name, stype, domain)
            if service_key in pending_resolutions:
                pending_resolutions.remove(service_key)

            if not pending_resolutions:
                resolution_complete.set()

        def service_found(interface, protocol, name, stype, domain, flags):
            """Callback when a service is found during browsing."""
            service_key = (interface, protocol, name, stype, domain)
            pending_resolutions.add(service_key)

            self.log(f"  └─ Found service, resolving: {name}")

            try:
                self.server.ResolveService(
                    interface, protocol, name, stype, domain,
                    PROTO_UNSPEC, dbus.UInt32(0),
                    reply_handler=service_resolved,
                    error_handler=lambda err: self._resolve_error(
                        err, service_key, pending_resolutions, resolution_complete
                    )
                )
            except Exception as e:
                self.log(f"Error resolving service: {e}")
                pending_resolutions.discard(service_key)
                if not pending_resolutions:
                    resolution_complete.set()

        def browse_error(err):
            """Callback for browse errors."""
            self.log(f"Browse error: {err}")
            resolution_complete.set()

        def all_for_now(interface, protocol):
            """Callback when initial browse is complete."""
            GLib.timeout_add(
                1000,
                lambda: resolution_complete.set() if not pending_resolutions else False
            )

        try:
            full_service_type = service_type
            if not full_service_type.endswith('.'):
                full_service_type += ".local."

            self.log(f"Starting browse for service type: {full_service_type}")
            self.log("  └─ Scanning network for services...")

            browser = dbus.Interface(
                self.bus.get_object(
                    DBUS_NAME,
                    self.server.ServiceBrowserNew(
                        IF_UNSPEC,
                        PROTO_UNSPEC,
                        service_type,
                        'local',
                        dbus.UInt32(0)
                    )
                ),
                DBUS_INTERFACE_SERVICE_BROWSER
            )

            browser.connect_to_signal('ItemNew', service_found)
            browser.connect_to_signal('AllForNow', all_for_now)
            browser.connect_to_signal('Failure', browse_error)

            resolution_complete.wait(timeout=5.0)

            browser.Free()

            self.log(f"Browse completed: found {len(self.discovered_services)} service(s)")

            return self.discovered_services

        except Exception as e:
            self.log(f"Error browsing services: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _resolve_error(self, err, service_key, pending_resolutions, event):
        """Handle resolution errors."""
        self.log(f"Resolve error: {err}")
        pending_resolutions.discard(service_key)
        if not pending_resolutions:
            event.set()

    def clear_cache(self) -> None:
        """Clear any cached service discovery data."""
        self.discovered_services = []

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[AvahiDBusBackend] {message}")
