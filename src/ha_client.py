"""
Home Assistant WebSocket client for service calls.

Responsibilities:
- Connect to Home Assistant WebSocket API
- Authenticate with long-lived access token
- Send call_service messages (picnic.add_product, assist_satellite.announce)
- Handle reconnection with exponential backoff
- Parse and log service call results
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    raise ImportError("websockets library required. Install with: pip install websockets")

logger = logging.getLogger(__name__)


@dataclass
class ServiceCallResult:
    """Result of a Home Assistant service call."""
    success: bool
    context: Optional[Dict[str, Any]] = None
    response: Optional[Any] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class HAClient:
    """Home Assistant WebSocket client."""
    
    def __init__(self, url: str, token: str, reconnect_backoff_ms: List[int] = None):
        """
        Initialize HA client.
        
        Args:
            url: WebSocket URL (e.g., ws://homeassistant.local:8123/api/websocket)
            token: Long-lived access token
            reconnect_backoff_ms: Exponential backoff sequence for reconnection
        """
        self.url = url
        self.token = token
        self.reconnect_backoff_ms = reconnect_backoff_ms or [500, 1000, 2000, 5000]
        
        self.ws: Optional[WebSocketClientProtocol] = None
        self.message_id = 0
        self.connected = False
        self.authenticated = False
    
    async def connect(self) -> bool:
        """
        Connect and authenticate to Home Assistant.
        
        Returns:
            True if connected and authenticated successfully
        """
        try:
            logger.info(f"Connecting to Home Assistant at {self.url}")
            self.ws = await websockets.connect(self.url)
            self.connected = True
            
            # Receive auth_required message
            auth_required = await self.ws.recv()
            auth_msg = json.loads(auth_required)
            
            if auth_msg.get('type') != 'auth_required':
                logger.error(f"Expected auth_required, got: {auth_msg.get('type')}")
                return False
            
            logger.debug(f"HA version: {auth_msg.get('ha_version')}")
            
            # Send auth message
            await self.ws.send(json.dumps({
                'type': 'auth',
                'access_token': self.token
            }))
            
            # Receive auth response
            auth_response = await self.ws.recv()
            auth_result = json.loads(auth_response)
            
            if auth_result.get('type') == 'auth_ok':
                self.authenticated = True
                logger.info("Successfully authenticated to Home Assistant")
                return True
            elif auth_result.get('type') == 'auth_invalid':
                logger.error(f"Authentication failed: {auth_result.get('message')}")
                return False
            else:
                logger.error(f"Unexpected auth response: {auth_result}")
                return False
        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            self.authenticated = False
            return False
    
    async def disconnect(self):
        """Disconnect from Home Assistant."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.authenticated = False
            logger.info("Disconnected from Home Assistant")
    
    def _next_id(self) -> int:
        """Get next message ID."""
        self.message_id += 1
        return self.message_id
    
    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None,
        target: Optional[Dict[str, Any]] = None,
        return_response: bool = False
    ) -> ServiceCallResult:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'picnic', 'assist_satellite')
            service: Service name (e.g., 'add_product', 'announce')
            service_data: Service data payload
            target: Target entities/devices/areas
            return_response: Whether service returns response data
            
        Returns:
            ServiceCallResult with success status and details
        """
        if not self.authenticated:
            return ServiceCallResult(
                success=False,
                error_code='not_authenticated',
                error_message='Not connected to Home Assistant'
            )
        
        msg_id = self._next_id()
        message = {
            'id': msg_id,
            'type': 'call_service',
            'domain': domain,
            'service': service
        }
        
        if service_data:
            message['service_data'] = service_data
        
        if target:
            message['target'] = target
        
        if return_response:
            message['return_response'] = True
        
        try:
            # Send service call
            await self.ws.send(json.dumps(message))
            logger.debug(f"Sent service call: {domain}.{service} (id={msg_id})")
            
            # Wait for result
            while True:
                response_str = await self.ws.recv()
                response = json.loads(response_str)
                
                # Match response to our message ID
                if response.get('id') == msg_id:
                    if response.get('type') == 'result':
                        if response.get('success'):
                            result_data = response.get('result', {})
                            logger.info(
                                f"Service call succeeded: {domain}.{service} "
                                f"context_id={result_data.get('context', {}).get('id', 'unknown')}"
                            )
                            return ServiceCallResult(
                                success=True,
                                context=result_data.get('context'),
                                response=result_data.get('response')
                            )
                        else:
                            error = response.get('error', {})
                            logger.error(
                                f"Service call failed: {domain}.{service} "
                                f"error={error.get('code')}: {error.get('message')}"
                            )
                            return ServiceCallResult(
                                success=False,
                                error_code=error.get('code'),
                                error_message=error.get('message')
                            )
                    else:
                        logger.warning(f"Unexpected response type: {response.get('type')}")
                        return ServiceCallResult(
                            success=False,
                            error_code='unexpected_response',
                            error_message=f"Unexpected response type: {response.get('type')}"
                        )
        
        except Exception as e:
            logger.error(f"Service call exception: {e}")
            return ServiceCallResult(
                success=False,
                error_code='exception',
                error_message=str(e)
            )
    
    async def add_product(
        self,
        product_id: str,
        amount: int = 1,
        config_entry_id: Optional[str] = None
    ) -> ServiceCallResult:
        """
        Add a product to Picnic cart.
        
        Args:
            product_id: Picnic product ID (e.g., 's1018231')
            amount: Quantity to add
            config_entry_id: Optional config entry for multi-account setups
            
        Returns:
            ServiceCallResult
        """
        service_data = {
            'product_id': product_id,
            'amount': amount
        }
        
        if config_entry_id:
            service_data['config_entry_id'] = config_entry_id
        
        logger.info(f"Adding product: {product_id} x{amount}")
        
        # Try to reconnect if not authenticated
        if not self.authenticated:
            logger.warning("Not authenticated, attempting to reconnect...")
            if not await self.connect():
                return ServiceCallResult(
                    success=False,
                    error_code='connection_failed',
                    error_message='Failed to reconnect to Home Assistant'
                )
        
        result = await self.call_service('picnic', 'add_product', service_data)
        
        # If call failed due to connection issue, try to reconnect
        if not result.success and result.error_code == 'exception':
            logger.warning("Service call failed with exception, attempting to reconnect...")
            if await self.connect():
                # Retry once after reconnection
                result = await self.call_service('picnic', 'add_product', service_data)
        
        return result
    
    async def announce(
        self,
        message: str,
        device_id: str,
        preannounce: bool = False
    ) -> ServiceCallResult:
        """
        Announce a message on an Assist Satellite device.
        
        Args:
            message: Message to announce
            device_id: Target device ID
            preannounce: Whether to play chime before message
            
        Returns:
            ServiceCallResult
        """
        service_data = {
            'message': message,
            'preannounce': preannounce
        }
        
        target = {
            'device_id': device_id
        }
        
        logger.info(f"Announcing: '{message}' to device {device_id}")
        
        # Try to reconnect if not authenticated
        if not self.authenticated:
            logger.warning("Not authenticated, attempting to reconnect...")
            if not await self.connect():
                return ServiceCallResult(
                    success=False,
                    error_code='connection_failed',
                    error_message='Failed to reconnect to Home Assistant'
                )
        
        result = await self.call_service('assist_satellite', 'announce', service_data, target)
        
        # If call failed due to connection issue, try to reconnect
        if not result.success and result.error_code == 'exception':
            logger.warning("Service call failed with exception, attempting to reconnect...")
            if await self.connect():
                # Retry once after reconnection
                result = await self.call_service('assist_satellite', 'announce', service_data, target)
        
        return result
    
    async def reconnect_loop(self, max_attempts: int = 0) -> bool:
        """
        Attempt reconnection with exponential backoff.
        
        Args:
            max_attempts: Maximum reconnection attempts (0 = infinite)
            
        Returns:
            True if reconnected successfully
        """
        attempt = 0
        
        while max_attempts == 0 or attempt < max_attempts:
            attempt += 1
            backoff_idx = min(attempt - 1, len(self.reconnect_backoff_ms) - 1)
            backoff_ms = self.reconnect_backoff_ms[backoff_idx]
            
            logger.info(f"Reconnection attempt {attempt}, waiting {backoff_ms}ms...")
            await asyncio.sleep(backoff_ms / 1000.0)
            
            if await self.connect():
                logger.info("Reconnected successfully")
                return True
        
        logger.error(f"Failed to reconnect after {attempt} attempts")
        return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


async def test_ha_client():
    """Test the HA client."""
    import os
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # Get credentials from environment
    url = os.getenv('HA_URL', 'ws://homeassistant.local:8123/api/websocket')
    token = os.getenv('HA_TOKEN')
    
    if not token:
        print("Error: Set HA_TOKEN environment variable")
        return
    
    print(f"Connecting to {url}...")
    
    async with HAClient(url, token) as client:
        if client.authenticated:
            print("✓ Connected and authenticated")
            
            # Test product add (will fail if product doesn't exist, but tests the call)
            print("\nTesting picnic.add_product...")
            result = await client.add_product('s1018231', amount=1)
            print(f"  Result: {'✓ Success' if result.success else '✗ Failed'}")
            if not result.success:
                print(f"  Error: {result.error_code} - {result.error_message}")
            
            # Test announcement (will fail if device doesn't exist)
            print("\nTesting assist_satellite.announce...")
            result = await client.announce(
                "Test message from MIDI bridge",
                device_id="4f17bb6b7102f82e8a91bf663bcb76f9"
            )
            print(f"  Result: {'✓ Success' if result.success else '✗ Failed'}")
            if not result.success:
                print(f"  Error: {result.error_code} - {result.error_message}")
        else:
            print("✗ Authentication failed")


if __name__ == "__main__":
    asyncio.run(test_ha_client())
