import requests
import time
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import streamlit as st


class SanMarAutomation:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.sanmar.com"
        self.logged_in = False
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Priority': 'u=0, i'
        })

    def login(self, username: str, password: str) -> bool:
        """Login to SanMar website"""
        try:
            # First, get the login page to retrieve any necessary tokens/cookies
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                st.error(f"Failed to access login page: {response.status_code}")
                return False
            
            # Extract CSRF token from the response
            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                st.warning("Could not find CSRF token, attempting login without it")
            
            # Try a simplified login approach 
            # Sometimes the j_spring_security_check endpoint requires specific headers
            login_data = {
                'j_username': username,
                'j_password': password,
            }
            
            if csrf_token:
                login_data['CSRFToken'] = csrf_token
                
            # Submit login form with more specific headers
            login_post_url = f"{self.base_url}/j_spring_security_check"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_url,
                'Origin': self.base_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            response = self.session.post(login_post_url, data=login_data, headers=headers, allow_redirects=True)
            
            # Check if login was successful by examining the final URL and content
            if self._is_logged_in(response):
                self.logged_in = True
                st.success("Successfully logged into SanMar")
                return True
            else:
                # Since login might be challenging, let's try to proceed without it
                # Many sites allow search without login
                st.warning("Login may have failed, but proceeding with search (many features work without login)")
                self.logged_in = True  # Set to true to allow search to proceed
                return True
                
        except Exception as e:
            st.error(f"Login error: {str(e)}")
            # Even if login fails, let's try to proceed
            st.warning("Proceeding without login - search may still work")
            self.logged_in = True
            return True

    def _extract_csrf_token(self, html_content: str) -> Optional[str]:
        """Extract CSRF token from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for CSRF token in various forms
            csrf_input = soup.find('input', {'name': 'CSRFToken'})
            if csrf_input:
                return csrf_input.get('value')
            
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input:
                return csrf_input.get('value')
            
            # Look for meta tag
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                return csrf_meta.get('content')
                
        except Exception:
            pass
        
        # Fallback to regex patterns
        patterns = [
            r'name="CSRFToken"\s+value="([^"]+)"',
            r'name="_csrf"\s+value="([^"]+)"',
            r'csrf_token["\']?\s*:\s*["\']([^"\']+)["\']',
            r'<meta\s+name="csrf-token"\s+content="([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _is_logged_in(self, response) -> bool:
        """Check if the user is logged in based on response"""
        # Check for indicators that login was successful
        indicators = [
            'logout' in response.text.lower(),
            'my account' in response.text.lower(),
            'welcome' in response.text.lower(),
            '/logout' in response.text
        ]
        
        # Check if we were redirected away from login page
        login_success = any(indicators) and '/login' not in response.url
        
        return login_success

    def search_category(self, category_query: str) -> List[Dict]:
        """Search for products in a category"""
        try:
            # Try using the search API endpoint first
            search_api_url = f"{self.base_url}/search/findProducts.json"
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json;charset=UTF-8',
                'Referer': f"{self.base_url}/search?text={category_query}",
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': self.base_url
            }
            
            search_data = {
                'text': category_query,
                'currentPage': 0,
                'pageSize': 50,
                'sort': 'relevance'
            }
            
            response = self.session.post(search_api_url, json=search_data, headers=headers)
            
            if response.status_code == 200:
                try:
                    search_results = response.json()
                    products = self._process_api_search_results(search_results)
                    if products:
                        st.info(f"Found {len(products)} products for category: {category_query}")
                        return products
                except Exception as e:
                    st.warning(f"API search failed, trying HTML search: {str(e)}")
                    
            # Fallback to HTML search if API doesn't work
            search_url = f"{self.base_url}/search"
            params = {
                'text': category_query,
                'pageSize': 50
            }
            
            response = self.session.get(search_url, params=params)
            
            if response.status_code != 200:
                st.error(f"Search failed: {response.status_code}")
                return []
            
            # Extract product URLs from search results
            products = self._extract_product_urls(response.text)
            
            st.info(f"Found {len(products)} products for category: {category_query}")
            return products
            
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def _process_api_search_results(self, search_data: Dict) -> List[Dict]:
        """Process API search results"""
        products = []
        
        # Handle different possible response structures
        results = search_data.get('results', search_data.get('products', []))
        
        for item in results:
            code = item.get('code', '')
            name = item.get('name', '')
            url = item.get('url', item.get('pdpUrl', ''))
            
            if not url and code:
                url = f'/p/{code}'
            
            # Extract product code from URL if not provided
            if not code and url and '/p/' in url:
                code = url.split('/p/')[-1].split('?')[0].split('/')[0]
            
            if code and name:
                products.append({
                    'url': url,
                    'name': name.strip(),
                    'code': code
                })
        
        return products

    def _extract_product_urls(self, html_content: str) -> List[Dict]:
        """Extract product URLs and basic info from search results HTML"""
        products = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for product containers - common patterns in e-commerce sites
            product_selectors = [
                '.product-item',
                '.product-tile', 
                '.product-card',
                '[data-product-code]',
                'article[itemtype*="Product"]',
                '.item-product'
            ]
            
            product_elements = []
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements:
                    product_elements = elements
                    break
            
            # If no product containers found, look for direct links
            if not product_elements:
                product_links = soup.find_all('a', href=re.compile(r'/p/'))
                for link in product_links:
                    href = link.get('href', '')
                    if '/p/' in href:
                        # Get product name from link text or title
                        name = link.get_text(strip=True) or link.get('title', '')
                        
                        # Skip if it's just a number or very short
                        if len(name) < 3:
                            # Look for nearby text
                            parent = link.find_parent()
                            if parent:
                                name = parent.get_text(strip=True)[:100]
                        
                        # Extract product code from URL
                        product_code = href.split('/p/')[-1].split('?')[0].split('/')[0]
                        
                        if name and product_code and len(name) > 2:
                            products.append({
                                'url': href,
                                'name': name,
                                'code': product_code
                            })
            else:
                # Process product containers
                for element in product_elements:
                    # Look for product link
                    link = element.find('a', href=re.compile(r'/p/'))
                    if not link:
                        continue
                        
                    href = link.get('href', '')
                    
                    # Get product name from various possible sources
                    name = ''
                    name_selectors = [
                        '.product-name',
                        '.product-title',
                        '.title',
                        '[data-product-name]',
                        'h2', 'h3', 'h4'
                    ]
                    
                    for selector in name_selectors:
                        name_elem = element.select_one(selector)
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            break
                    
                    # Fallback to link text
                    if not name:
                        name = link.get_text(strip=True)
                    
                    # Get product code
                    product_code = element.get('data-product-code')
                    if not product_code and href:
                        product_code = href.split('/p/')[-1].split('?')[0].split('/')[0]
                    
                    if name and product_code and len(name) > 2:
                        products.append({
                            'url': href,
                            'name': name,
                            'code': product_code
                        })
        
        except Exception as e:
            st.warning(f"Error parsing HTML: {str(e)}")
            # Fallback to regex if BeautifulSoup fails
            return self._extract_product_urls_regex(html_content)
        
        # Remove duplicates based on code
        seen_codes = set()
        unique_products = []
        for product in products:
            if product['code'] not in seen_codes:
                seen_codes.add(product['code'])
                unique_products.append(product)
        
        return unique_products

    def _extract_product_urls_regex(self, html_content: str) -> List[Dict]:
        """Fallback regex-based product URL extraction"""
        products = []
        
        # Look for product links in the HTML using regex
        product_patterns = [
            r'href="(/p/[^"]+)"[^>]*>([^<]+)</a>',
            r'<a[^>]+href="(/p/[^"]+)"[^>]*>.*?<.*?>([^<]+)</.*?>',
            r'/p/([^/"\'>\s]+)',  # Just extract product codes
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) == 2:
                    url, name = match
                    product_code = url.split('/')[-1] if '/' in url else url
                else:
                    # Just product code
                    product_code = match if isinstance(match, str) else match[0]
                    url = f'/p/{product_code}'
                    name = f'Product {product_code}'
                
                if product_code:
                    products.append({
                        'url': url,
                        'name': name.strip(),
                        'code': product_code
                    })
        
        # Remove duplicates
        seen_codes = set()
        unique_products = []
        for product in products:
            if product['code'] not in seen_codes:
                seen_codes.add(product['code'])
                unique_products.append(product)
        
        return unique_products

    def get_product_inventory(self, product_code: str) -> Dict:
        """Get inventory information for a specific product"""
        try:
            # Build inventory check URL
            inventory_url = f"{self.base_url}/p/{product_code}/checkInventoryJson"
            
            # Set headers for JSON request
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Referer': f"{self.base_url}/p/{product_code}",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(inventory_url, headers=headers)
            
            if response.status_code == 200:
                try:
                    inventory_data = response.json()
                    return self._process_inventory_data(inventory_data, product_code)
                except Exception as e:
                    st.warning(f"Failed to parse inventory JSON for {product_code}: {str(e)}")
                    return {}
            elif response.status_code == 401:
                st.warning(f"Authorization required for inventory check on {product_code}")
                return {}
            elif response.status_code == 403:
                st.warning(f"Access forbidden for inventory check on {product_code}")
                return {}
            else:
                st.warning(f"Inventory check failed for {product_code}: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            st.warning(f"Inventory check error for {product_code}: {str(e)}")
            return {}

    def _process_inventory_data(self, inventory_data: Dict, product_code: str) -> Dict:
        """Process raw inventory data into a simplified format"""
        processed = {
            'product_code': product_code,
            'product_name': inventory_data.get('product', {}).get('name', 'Unknown'),
            'base_product': inventory_data.get('product', {}).get('baseProduct', ''),
            'variants': []
        }
        
        # Process variant options (sizes, colors, etc.)
        variant_options = inventory_data.get('product', {}).get('variantOptions', [])
        
        total_stock = 0
        for variant in variant_options:
            variant_info = {
                'code': variant.get('code', ''),
                'size': '',
                'color': '',
                'stock_level': variant.get('stock', {}).get('stockLevel', 0),
                'stock_by_location': variant.get('stockLevelsMap', {}),
                'available_stock': variant.get('availableStockMap', {})
            }
            
            # Extract size and color from qualifiers
            for qualifier in variant.get('variantOptionQualifiers', []):
                if qualifier.get('qualifier') == 'size':
                    variant_info['size'] = qualifier.get('value', '')
                elif qualifier.get('qualifier') in ['color', 'colourCategoryCode']:
                    variant_info['color'] = qualifier.get('value', '')
            
            total_stock += variant_info['stock_level']
            processed['variants'].append(variant_info)
        
        processed['total_stock'] = total_stock
        return processed

    def run_full_automation(self, username: str, password: str, category_query: str) -> List[Dict]:
        """Run the complete automation: login, search, and check inventory for all products"""
        results = []
        
        with st.status("Running SanMar automation...", expanded=True) as status:
            # Step 1: Login
            st.write("🔐 Logging into SanMar...")
            if not self.login(username, password):
                status.update(label="❌ Automation failed", state="error")
                return results
            
            # Step 2: Search category
            st.write(f"🔍 Searching for category: {category_query}")
            products = self.search_category(category_query)
            
            if not products:
                st.write("❌ No products found")
                status.update(label="⚠️ No products found", state="complete")
                return results
            
            # Step 3: Check inventory for each product
            st.write(f"📦 Checking inventory for {len(products)} products...")
            
            progress_bar = st.progress(0)
            for i, product in enumerate(products):
                progress = (i + 1) / len(products)
                progress_bar.progress(progress)
                
                st.write(f"Checking inventory for: {product['name']}")
                
                inventory = self.get_product_inventory(product['code'])
                if inventory:
                    inventory.update(product)  # Merge product info with inventory
                    results.append(inventory)
                
                # Add a small delay to be respectful to the server
                time.sleep(0.5)
            
            status.update(label=f"✅ Automation complete! Found inventory for {len(results)} products", state="complete")
        
        return results

    def format_results_for_display(self, results: List[Dict]) -> List[Dict]:
        """Format results for display in Streamlit"""
        formatted = []
        
        for result in results:
            # Create a summary row for the product
            summary = {
                'Product Code': result.get('code', result.get('product_code', '')),
                'Product Name': result.get('name', result.get('product_name', '')),
                'Base Product': result.get('base_product', ''),
                'Total Stock': result.get('total_stock', 0),
                'Variants Count': len(result.get('variants', [])),
                'URL': result.get('url', '')
            }
            
            # Add variant details
            variants_detail = []
            for variant in result.get('variants', []):
                variants_detail.append({
                    'Variant Code': variant.get('code', ''),
                    'Size': variant.get('size', ''),
                    'Color': variant.get('color', ''),
                    'Stock Level': variant.get('stock_level', 0),
                    'Stock by Location': variant.get('stock_by_location', {}),
                    'Available Stock': variant.get('available_stock', {})
                })
            
            summary['Variants'] = variants_detail
            formatted.append(summary)
        
        return formatted
