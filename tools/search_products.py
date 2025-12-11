#!/usr/bin/env python3
"""
Picnic Product Search Tool

Search for products in the Picnic catalog to find their product IDs.
This tool helps you populate your mapping.yaml file.

Usage:
    python3 tools/search_products.py "coca cola zero"
    python3 tools/search_products.py --interactive
"""

import sys
import os
import argparse
from typing import Optional

try:
    from python_picnic_api2 import PicnicAPI
except ImportError:
    print("ERROR: python_picnic_api2 is not installed")
    print("Install with: pip install python-picnic-api")
    sys.exit(1)


def search_product(picnic: PicnicAPI, query: str) -> None:
    """Search for a product and display results."""
    print(f"\n🔍 Searching for: '{query}'")
    print("=" * 60)
    
    try:
        results = picnic.search(query)
        
        if not results:
            print("❌ No products found")
            return
        
        print(f"✓ Found {len(results)} result(s):\n")
        
        for i, item in enumerate(results[:10], 1):  # Limit to 10 results
            product_id = item.get('id', 'N/A')
            name = item.get('name', 'Unknown')
            price = item.get('price', 0) / 100  # Convert cents to euros
            unit = item.get('unit_quantity', '')
            
            print(f"{i}. {name}")
            print(f"   Product ID: {product_id}")
            print(f"   Price: €{price:.2f} {unit}")
            
            # Generate YAML snippet
            print(f"   \033[90m# Add to mapping.yaml:\033[0m")
            print(f"   \033[90m{60}:")
            print(f"     product_id: {product_id}")
            print(f"     product_name: \"{name}\"")
            print(f"     amount: 1\033[0m")
            print()
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more results (showing first 10)")
    
    except Exception as e:
        print(f"❌ Error searching: {e}")


def interactive_mode(picnic: PicnicAPI) -> None:
    """Run in interactive mode."""
    print("\n" + "=" * 60)
    print("🛒 Picnic Product Search (Interactive Mode)")
    print("=" * 60)
    print("Enter product names to search for their IDs.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            query = input("Search for: ").strip()
            
            if query.lower() in ('quit', 'exit', 'q'):
                print("\n👋 Goodbye!")
                break
            
            if not query:
                continue
            
            search_product(picnic, query)
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Search Picnic products to find their IDs for mapping.yaml',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for a product:
  python3 tools/search_products.py "coca cola zero"
  
  # Interactive mode:
  python3 tools/search_products.py --interactive
  
  # Use with environment variables:
  export PICNIC_USERNAME="your@email.com"
  export PICNIC_PASSWORD="yourpassword"
  python3 tools/search_products.py "bananas"
        """
    )
    
    parser.add_argument(
        'query',
        nargs='?',
        help='Product name to search for'
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '-u', '--username',
        default=os.getenv('PICNIC_USERNAME'),
        help='Picnic email (or set PICNIC_USERNAME env var)'
    )
    parser.add_argument(
        '-p', '--password',
        default=os.getenv('PICNIC_PASSWORD'),
        help='Picnic password (or set PICNIC_PASSWORD env var)'
    )
    parser.add_argument(
        '-c', '--country',
        default=os.getenv('PICNIC_COUNTRY', 'NL'),
        help='Country code (default: NL)'
    )
    
    args = parser.parse_args()
    
    # Validate credentials
    if not args.username or not args.password:
        print("❌ ERROR: Picnic credentials required")
        print("\nProvide credentials via:")
        print("  1. Command line: --username YOUR_EMAIL --password YOUR_PASSWORD")
        print("  2. Environment variables:")
        print("       export PICNIC_USERNAME='your@email.com'")
        print("       export PICNIC_PASSWORD='yourpassword'")
        print("\nFor security, using environment variables is recommended!")
        sys.exit(1)
    
    # Initialize Picnic API
    print("🔐 Connecting to Picnic API...")
    try:
        picnic = PicnicAPI(
            username=args.username,
            password=args.password,
            country_code=args.country
        )
        print("✓ Connected successfully!\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)
    
    # Run in appropriate mode
    if args.interactive:
        interactive_mode(picnic)
    elif args.query:
        search_product(picnic, args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
