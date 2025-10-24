from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class MdnsService:
    """
    Represents an mDNS service with its configuration parameters.
    
    Attributes:
        name: The service instance name
        service_type: The service type (e.g., '_http._tcp')
        port: The port number where the service is available
        txt_record: Dictionary containing TXT record key-value pairs
        domain: The domain for the service, defaults to 'local'
        host: The hostname, empty string uses system hostname
    """
    name: str
    service_type: str
    port: int
    txt_record: dict
    domain: str = "local"
    host: str = ""
    
    
class AvahiInterface(ABC):
    """
    Abstract interface for mDNS service discovery and publication using Avahi.
    
    All methods in this interface are synchronous, though implementations
    may use asynchronous operations internally.
    
    The interface is started automatically upon initialization. Use stop()
    only when you need to cleanly shut down the service, and start() if you
    need to restart it afterwards.
    """
    
    @abstractmethod
    def browse(self, service_type: str) -> list[MdnsService]:
        """
        Discover and resolve all services of the specified type on the network.
        
        This method performs a complete browse and resolve operation, which may
        take several seconds to complete as it waits for all services to be
        fully resolved.
        
        Args:
            service_type: The service type to browse for (e.g., '_http._tcp')
            
        Returns:
            A list of fully resolved MdnsService instances found on the network
        """
        pass
    
    @abstractmethod
    def publish(self, service: MdnsService) -> bool:
        """
        Publish an mDNS service on the network.
        
        Args:
            service: The MdnsService instance to publish
            
        Returns:
            True if the service was successfully published, False otherwise
        """
        pass
    
    @abstractmethod
    def unpublish(self, service: MdnsService) -> bool:
        """
        Remove a published mDNS service from the network.
        
        The service is matched by name and service_type to determine which
        service to unpublish.
        
        Args:
            service: The MdnsService instance to unpublish
            
        Returns:
            True if the service was successfully unpublished, False otherwise
        """
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """
        Clear any cached service discovery data.
        
        This forces the next browse operation to perform a fresh network scan.
        """
        pass
    
    @abstractmethod
    def start(self) -> None:
        """
        Start the Avahi client.
        
        This method is called automatically during initialization and typically
        does not need to be called manually unless stop() was previously called.
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """
        Stop the Avahi client and clean up resources.
        
        This should be called when the interface is no longer needed to ensure
        proper cleanup of network resources and background tasks.
        """
        pass
    
    @abstractmethod
    def log(self, message: str) -> None:
        pass