# pypararius

Python API for Pararius.com - the Netherlands' largest rental property platform.

> If you find this useful, consider giving it a star — it helps others discover the project.

[![Star History Chart](https://api.star-history.com/svg?repos=0xMH/pypararius&type=Date)](https://star-history.com/#0xMH/pypararius&Date)

## Installation

```bash
pip install pypararius
# or with uv
uv add pypararius
```

## Quick Start

```python
from pypararius import Pararius

p = Pararius()

# Search for listings
results = p.search_listing('amsterdam', price_max=2000)
for r in results[:3]:
    print(r['title'], r['price'])

# Get full listing details
listing = p.get_listing(results[0]['url'])
print(listing['title'], listing['city'])
print(listing.summary())
```

## How It Works

This library uses  Pararius.com's internal endpoints.  Pararius only has a website, so we use their frontend's AJAX endpoints.

### Discovery Process

The API was discovered by analyzing network traffic from the Pararius website:

1. Observed that search pages make XHR requests that return JSON instead of HTML
2. Identified the `X-Requested-With: XMLHttpRequest` header as the trigger for JSON responses
3. Mapped URL path segments to filter parameters
4. Found JSON-LD structured data embedded in listing detail pages

### API Architecture

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/apartments/{city}/{filters}` | GET | Search listings (returns JSON with XHR header) |
| `/apartment-for-rent/{city}/{id}/{street}` | GET | Listing details (HTML with JSON-LD) |
| `/api/suggest` | GET | Location autocomplete |

### Search Response

When the search endpoint receives the XHR header, it returns:

```json
{
  "components": {
    "results": "<html>...</html>"
  },
  "search_query": {
    "filters": {...},
    "view_options": {...}
  },
  "_meta": {
    "canonical_url": "..."
  }
}
```

The `components.results` contains pre-rendered HTML listing cards that are parsed to extract listing data.

### Listing Details

Detail pages return full HTML with embedded JSON-LD:

```html
<script type="application/ld+json">
{
  "@type": "Apartment",
  "name": "Apartment Ridderspoorweg",
  "address": {...},
  "geo": {"latitude": 52.xxx, "longitude": 4.xxx},
  "floorSize": {"value": 75},
  "offers": {"price": 1850}
}
</script>
```

Additional data (bedrooms, deposit, energy rating, etc.) is extracted by parsing the HTML feature tables.

### Authentication

No authentication required. All listing data is publicly accessible.


## API Reference

### Pararius

Main entry point for the API.

```python
from pypararius import Pararius

p = Pararius(timeout=30)
```

#### search_listing(location, ...)

Search for rental listings with filters.

```python
results = p.search_listing(
    location='amsterdam',       # City name
    price_min=1000,             # Minimum rent
    price_max=2000,             # Maximum rent
    area_min=50,                # Minimum living area (m²)
    bedrooms=2,                 # Minimum bedrooms
    interior='furnished',       # 'furnished', 'upholstered', 'shell'
    sort='newest',              # Sort order (see below)
    page=0,                     # Page number (0-indexed)
)
```

**Sort options:**

| Sort Value | Description |
|------------|-------------|
| `newest` | Most recently published first |
| `price_asc` | Lowest price first |
| `price_desc` | Highest price first |
| `area_asc` | Smallest area first |
| `area_desc` | Largest area first |

#### get_listing(url)

Get full details for a listing by URL.

```python
# By full URL
listing = p.get_listing('https://www.pararius.com/apartment-for-rent/amsterdam/abc123/street')

# By partial path
listing = p.get_listing('amsterdam/abc123/street')
```

### Listing

Listing objects support dict-like access with convenient aliases.

**Basic info:**

```python
listing['title']            # Property title/address
listing['city']             # City name
listing['postcode']         # Postal code
listing['neighbourhood']    # Neighbourhood name
```

**Price:**

```python
listing['price']            # Numeric price (monthly rent)
listing['price_formatted']  # Formatted price string
listing['deposit']          # Deposit amount
```

**Property details:**

```python
listing['living_area']      # Living area in m²
listing['rooms']            # Total number of rooms
listing['bedrooms']         # Number of bedrooms
listing['interior']         # Interior type (furnished, etc.)
listing['energy_label']     # Energy rating
listing['description']      # Full description text
```

**Availability:**

```python
listing['available']        # Available date
listing['offered_since']    # When listed
listing['rental_agreement'] # Contract type
```

**Location:**

```python
listing['coordinates']      # (lat, lng) tuple
listing['latitude']         # Latitude
listing['longitude']        # Longitude
```

**Media:**

```python
listing['photos']           # List of photo URLs
listing['photo_urls']       # Same as photos
listing['photo_count']      # Number of photos
```

**Rules:**

```python
listing['smoking_allowed']  # Boolean
listing['pets_allowed']     # Boolean
```

**Broker:**

```python
listing['broker']           # Agent name
listing['broker_url']       # Agent page URL
listing['broker_phone']     # Agent phone
```

**Metadata:**

```python
listing['url']              # Full Pararius URL
listing['characteristics']  # Dict of all features
```

**Key aliases** - these all work:

| Alias | Canonical Key |
|-------|---------------|
| `name`, `address`, `street` | `title` |
| `location`, `locality` | `city` |
| `area`, `size`, `area_m2` | `living_area` |
| `images`, `pictures`, `media` | `photos` |
| `agent`, `realtor`, `makelaar` | `broker` |
| `zip`, `zipcode`, `postal_code` | `postcode` |
| `energy_rating` | `energy_label` |

#### Methods

```python
listing.summary()       # Text summary of the listing
listing.to_dict()       # Convert to plain dictionary
listing.keys()          # List available keys
listing.get('key')      # Get with default (like dict.get)
listing.id              # Get listing ID
```

## Examples

### Find apartments in Amsterdam under €2000/month

```python
from pypararius import Pararius

p = Pararius()
results = p.search_listing('amsterdam', price_max=2000)

for listing in results:
    print(f"{listing['title']}")
    print(f"  Price: €{listing['price']}/month")
    print(f"  Area: {listing.get('living_area', 'N/A')} m²")
    print(f"  Bedrooms: {listing.get('bedrooms', 'N/A')}")
    print()
```

### Get detailed listing information

```python
from pypararius import Pararius

p = Pararius()
results = p.search_listing('rotterdam', price_max=1500)

if results:
    listing = p.get_listing(results[0]['url'])
    print(listing.summary())

    # Access all characteristics
    for key, value in listing['characteristics'].items():
        print(f"{key}: {value}")
```

### Search with filters

```python
from pypararius import Pararius

p = Pararius()
results = p.search_listing(
    'amsterdam',
    price_min=1500,
    price_max=2500,
    bedrooms=2,
    interior='furnished',
    sort='price_asc',
)

print(f"Found {len(results)} listings")
```

### Using context manager

```python
from pypararius import Pararius

with Pararius() as p:
    results = p.search_listing('utrecht', price_max=1800)
    for r in results[:5]:
        print(f"{r['title']}: €{r['price']}")
```

## License

AGPL-3.0
