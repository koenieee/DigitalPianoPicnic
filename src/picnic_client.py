"""
Picnic API client for direct product additions.

Uses python-picnic-api2 library to add products directly to cart
without going through Home Assistant.
"""

import logging
from typing import Optional
from dataclasses import dataclass

try:
    from python_picnic_api2 import PicnicAPI
except ImportError:
    raise ImportError("python-picnic-api2 required. Install with: pip install python-picnic-api2")

logger = logging.getLogger(__name__)


@dataclass
class ProductAddResult:
    """Result of adding a product to cart."""
    success: bool
    error_message: Optional[str] = None


class PicnicClient:
    """Direct Picnic API client."""
    
    def __init__(self, username: str, password: str, country_code: str = "NL"):
        """
        Initialize Picnic client.
        
        Args:
            username: Picnic account email/phone
            password: Picnic account password
            country_code: Country code (NL, DE, etc.)
        """
        self.username = username
        self.password = password
        self.country_code = country_code
        self.api: Optional[PicnicAPI] = None
        self.authenticated = False
    
    async def connect(self) -> bool:
        """
        Connect and authenticate with Picnic API.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Picnic API for user: {self.username}")
            
            # Create API instance
            self.api = PicnicAPI(
                username=self.username,
                password=self.password,
                country_code=self.country_code
            )
            
            # Test authentication by getting cart
            self.api.get_cart()
            
            self.authenticated = True
            logger.info("Successfully connected to Picnic API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Picnic API: {e}")
            self.authenticated = False
            return False
    
    def add_product(self, product_id: str, amount: int = 1) -> ProductAddResult:
        """
        Add a product to the Picnic cart.
        
        Args:
            product_id: Picnic product ID (e.g., 's1018231')
            amount: Quantity to add
            
        Returns:
            ProductAddResult
        """
        if not self.authenticated or not self.api:
            return ProductAddResult(
                success=False,
                error_message="Not authenticated with Picnic API"
            )
        
        try:
            logger.info(f"Adding product to Picnic cart: {product_id} x{amount}")
            
            # Add product to cart
            self.api.add_product(product_id, amount)
            
            logger.info(f"Successfully added {product_id} x{amount} to cart")
            return ProductAddResult(success=True)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to add product {product_id}: {error_msg}")
            return ProductAddResult(success=False, error_message=error_msg)
    
    def get_cart(self):
        """
        Get current cart contents.
        
        Returns:
            Cart data dictionary
        """
        if not self.authenticated or not self.api:
            raise RuntimeError("Not authenticated with Picnic API")
        
        return self.api.get_cart()
