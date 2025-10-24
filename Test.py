from Interface import AvahiInterface, MdnsService

def test_publish_browse_unpublish(avahi: AvahiInterface):
    """
    Test the complete lifecycle of publishing, discovering, and unpublishing an mDNS service.
    
    This test verifies that:
    - A service can be published successfully
    - The published service can be discovered via browse
    - The TXT record contains the expected data
    - The service can be unpublished successfully
    - The service is no longer discoverable after unpublishing
    """
    
    # Define test service
    test_service = MdnsService(
        name="test-service",
        service_type="_http._tcp",
        port=8080,
        txt_record={"version": "1.0", "path": "/api"},
        domain="local",
        host=""
    )
    
    avahi.log("Starting test: publish_browse_unpublish")
    
    # Publish the service
    avahi.log(f"Publishing service: {test_service.name}")
    publish_result = avahi.publish(test_service)
    assert publish_result is True, "Failed to publish service"
    avahi.log("Service published successfully")
    
    # Browse for the service
    avahi.log(f"Browsing for service type: {test_service.service_type}")
    discovered_services = avahi.browse(test_service.service_type)
    avahi.log(f"Discovered {len(discovered_services)} services")
    
    # Find our service in the discovered list
    found_service = None
    for service in discovered_services:
        if service.name == test_service.name:
            found_service = service
            break
    
    assert found_service is not None, f"Service {test_service.name} not found in browse results"
    avahi.log(f"Service {test_service.name} found in browse results")
    
    # Check TXT record
    avahi.log(f"Checking TXT record: {found_service.txt_record}")
    assert found_service.txt_record == test_service.txt_record, \
        f"TXT record mismatch. Expected: {test_service.txt_record}, Got: {found_service.txt_record}"
    avahi.log("TXT record matches expected values")
    
    # Verify other service properties
    assert found_service.service_type == test_service.service_type, \
        f"Service type mismatch. Expected: {test_service.service_type}, Got: {found_service.service_type}"
    assert found_service.port == test_service.port, \
        f"Port mismatch. Expected: {test_service.port}, Got: {found_service.port}"
    avahi.log("All service properties match")
    
    # Unpublish the service
    avahi.log(f"Unpublishing service: {test_service.name}")
    unpublish_result = avahi.unpublish(test_service)
    assert unpublish_result is True, "Failed to unpublish service"
    avahi.log("Service unpublished successfully")
    
    # Browse again to verify service is gone
    avahi.log(f"Browsing again to verify service is removed")
    discovered_services_after = avahi.browse(test_service.service_type)
    avahi.log(f"Discovered {len(discovered_services_after)} services after unpublish")
    
    # Ensure our service is not in the list
    for service in discovered_services_after:
        assert service.name != test_service.name, \
            f"Service {test_service.name} still found after unpublish"
    
    avahi.log(f"Service {test_service.name} successfully removed from network")
    avahi.log("Test completed successfully")