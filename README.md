# SanMar Product Query -> Inventory Export

Fetch styles from a CompanyCasuals category/search page or from a list of style codes, query SanMar inventory (PromoStandards or SanMar Standard SOAP), and export results to CSV/XLSX.

This project avoids hard dependencies on API credentials until you have them. You can run discovery in dry-run mode now; when your boss provides credentials, drop them into `.env` and run full inventory pulls.

## Features
- Extract style codes from a CompanyCasuals category/search page URL (best-effort; gracefully falls back if blocked).
- Accept styles directly via `--styles` or from a file via `--styles-file`.
- Query SanMar inventory via:
  - PromoStandards Inventory v2.0.0 `getInventoryLevels` (username/password).
  - SanMar Standard Inventory `getInventoryQtyForStyleColorSize` (customer number + username/password).
- Export to `.xlsx` or `.csv`.

## Install
```
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set environment variables in `.env` when you have access:
- SANMAR_USERNAME, SANMAR_PASSWORD (required for both backends)
- SANMAR_CUSTOMER_NUMBER (required for Standard backend)
- SANMAR_USE_TEST=true (recommended until prod access)
- SANMAR_BACKEND=promostandards | standard

## Usage
Dry-run discovery (no API calls):
```
python -m app.cli --url "https://catalog.companycasuals.com/Polos-Knits/c/polosknits" --dry-run
# If the site blocks scripted requests, provide styles directly:
python -m app.cli --styles "K420 PC61 L223" --dry-run
```

Fetch inventory with PromoStandards backend (default):
```
# .env: SANMAR_USERNAME, SANMAR_PASSWORD, SANMAR_USE_TEST=true
python -m app.cli --styles "K420 PC61 L223" --output polos.xlsx
```

Fetch inventory with SanMar Standard backend:
```
# .env: SANMAR_CUSTOMER_NUMBER, SANMAR_USERNAME, SANMAR_PASSWORD
python -m app.cli --backend standard --styles "K420 PC61 L223" --output polos.csv --format csv
```

You can also pass a text file containing styles (one per line or separated by spaces/commas):
```
python -m app.cli --styles-file styles.txt --output out.xlsx
```

## Output Columns
- style
- partId (PromoStandards only)
- color
- size
- description (PromoStandards only)
- warehouseId
- warehouse
- qty
- totalAvailable (PromoStandards only)

## Implementation Notes
- PromoStandards Inventory v2.0.0 WSDL:
  - Test: https://test-ws.sanmar.com:8080/promostandards/InventoryServiceBindingV2final?WSDL
  - Prod: https://ws.sanmar.com:8080/promostandards/InventoryServiceBindingV2final?WSDL
  - We post to the binding endpoint (base URL without `?WSDL`). Request follows the guide’s `GetInventoryLevelsRequest`.
- SanMar Standard Inventory WSDL:
  - Test: https://test-ws.sanmar.com:8080/SanMarWebService/SanMarWebServicePort?wsdl
  - Prod: https://ws.sanmar.com:8080/SanMarWebService/SanMarWebServicePort?wsdl
  - Uses `getInventoryQtyForStyleColorSize` by style (or style/color/size if provided later).
- Scraper (`app/scraper.py`) is best-effort; CompanyCasuals may block scripted requests. Provide `--styles` as fallback.

## Development
- Main code:
  - `app/cli.py` – CLI orchestrator
  - `app/scraper.py` – Style extraction
  - `app/inventory.py` – SOAP clients + XML parsing
  - `app/exporter.py` – DataFrame + files
  - `app/config.py` – Settings and endpoints

## Next Steps
- Add optional partId lookups (batch by partIdArray for faster cart checks).
- Add category-to-styles mapping via SanMar data files (sanmar_dip.txt/EPDD) when FTP/API access is granted.
"# SanMar Product Search

A simple Streamlit web application for searching SanMar products using their search API.

## Features
- Live product search using SanMar's search endpoint
- Upload and parse JSON search results
- Display search results in a clean table format
- Optional cookie/header configuration for authentication

## Install
```
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Run the Streamlit app:
```
streamlit run streamlit_app.py
```

### Search Options
1. **Live Search**: Enter search terms (e.g., "blue nike polos") and click "Run Search"
2. **Upload JSON**: Upload a JSON file containing search results from findProducts.json

### Authentication (Optional)
If search requests are blocked, you can provide authentication:
1. Open sanmar.com in your browser and log in
2. Open DevTools → Network tab
3. Perform a product search
4. Find the findProducts.json request
5. Copy the Cookie header and paste it in the sidebar
6. Optionally copy other headers as JSON format

## Output
The app displays search results with:
- Product code
- Product name  
- Product slug
- Price information

## Implementation Notes
- Uses SanMar's search endpoint: `https://www.sanmar.com/search/findProducts.json`
- Search results are persisted in session state
- Clean, responsive UI optimized for various screen sizes" 
