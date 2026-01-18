"""Main Pararius API class."""

import re
from urllib.parse import urljoin

import httpx

from pypararius.listing import Listing
from pypararius.parser import parse_listing_details, parse_search_response


# Base URL
BASE_URL = "https://www.pararius.com"

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
}


class Pararius:
    """Main interface to Pararius API.

    Example:
        >>> from pypararius import Pararius
        >>> p = Pararius()
        >>> listing = p.get_listing('amsterdam/abc123/street')
        >>> print(listing['title'], listing['city'])
        Ridderspoorweg 10 Amsterdam
        >>> results = p.search_listing('amsterdam', price_max=2000)
        >>> for r in results[:3]:
        ...     print(r['title'], r['price'])
    """

    ID_PATTERN = re.compile(r"/([a-f0-9]{8})/")

    def __init__(self, timeout: int = 30):
        """Initialize Pararius API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazily create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers=HEADERS,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "Pararius":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # Listing methods
    # -------------------------------------------------------------------------

    def get_listing(self, listing_id: str) -> Listing:
        """Get a listing by ID or URL.

        Args:
            listing_id: Listing ID (e.g., 'abc123de') or full/partial URL

        Returns:
            Listing object with property data

        Example:
            >>> p.get_listing('eecd88d9')
            >>> p.get_listing('amsterdam/eecd88d9/ridderspoorweg')
            >>> p.get_listing('https://www.pararius.com/apartment-for-rent/amsterdam/eecd88d9/ridderspoorweg')
        """
        # If it's a full URL, use it directly
        if listing_id.startswith("http"):
            url = listing_id
        # If it contains slashes, it's a partial path
        elif "/" in listing_id:
            # Could be 'amsterdam/abc123/street' or '/apartment-for-rent/amsterdam/abc123/street'
            if listing_id.startswith("/"):
                url = urljoin(BASE_URL, listing_id)
            else:
                url = f"{BASE_URL}/apartment-for-rent/{listing_id}"
        else:
            # Just an ID - we need to search for it
            raise ValueError(
                f"Cannot fetch listing by ID alone. Please provide a URL or path like 'amsterdam/{listing_id}/street'"
            )

        response = self.client.get(url)

        if response.status_code == 404:
            raise LookupError(f"Listing {listing_id} not found")

        response.raise_for_status()
        return parse_listing_details(response.text, str(response.url))

    def search_listing(
        self,
        location: str | list[str] | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        area_min: int | None = None,
        bedrooms: int | None = None,
        interior: str | None = None,
        sort: str | None = None,
        page: int = 0,
    ) -> list[Listing]:
        """Search for listings.

        Args:
            location: City name to search in (e.g., 'amsterdam')
            price_min: Minimum rent price
            price_max: Maximum rent price
            area_min: Minimum living area in m²
            bedrooms: Minimum number of bedrooms
            interior: Interior type ('furnished', 'upholstered', 'shell')
            sort: Sort order - 'newest', 'price_asc', 'price_desc',
                  'area_asc', 'area_desc', or None
            page: Page number (0-indexed, ~30 results per page)

        Returns:
            List of Listing objects

        Example:
            >>> p.search_listing('amsterdam', price_max=2000)
            >>> p.search_listing('rotterdam', bedrooms=2, interior='furnished')
        """
        # Normalize location
        if isinstance(location, list):
            city = location[0] if location else "amsterdam"
        else:
            city = location or "amsterdam"

        city = city.lower().replace(" ", "-")

        # Build URL
        url = self._build_search_url(
            city=city,
            price_min=price_min,
            price_max=price_max,
            area_min=area_min,
            bedrooms=bedrooms,
            interior=interior,
            sort=sort,
            page=page + 1,  # Pararius uses 1-indexed pages
        )

        # Add XHR header to get JSON response
        headers = {"X-Requested-With": "XMLHttpRequest"}

        response = self.client.get(url, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(f"Search failed (status {response.status_code})")

        data = response.json()
        return parse_search_response(data, city)

    # -------------------------------------------------------------------------
    # URL building
    # -------------------------------------------------------------------------

    def _build_search_url(
        self,
        city: str,
        price_min: int | None = None,
        price_max: int | None = None,
        area_min: int | None = None,
        bedrooms: int | None = None,
        interior: str | None = None,
        sort: str | None = None,
        page: int = 1,
    ) -> str:
        """Build the search URL with filters."""
        parts = [f"{BASE_URL}/apartments/{city}"]

        # Price filter
        if price_min is not None or price_max is not None:
            p_min = price_min or 0
            p_max = price_max or 0
            if p_min > 0 or p_max > 0:
                parts.append(f"{p_min}-{p_max}")

        # Bedrooms filter
        if bedrooms is not None and bedrooms > 0:
            parts.append(f"{bedrooms}-bedrooms")

        # Area filter
        if area_min is not None and area_min > 0:
            parts.append(f"{area_min}m2")

        # Interior filter
        if interior is not None:
            interior_map = {
                "furnished": "furnished",
                "upholstered": "upholstered",
                "shell": "shell",
            }
            if interior.lower() in interior_map:
                parts.append(interior_map[interior.lower()])

        # Page (must come before sort in URL)
        if page > 1:
            parts.append(f"page-{page}")

        # Sort order
        if sort is not None:
            sort_map = {
                "newest": "",  # Default
                "price_asc": "sort-price-low",
                "price_desc": "sort-price-high",
                "area_asc": "sort-floor-low",
                "area_desc": "sort-floor-high",
            }
            sort_val = sort_map.get(sort, "")
            if sort_val:
                parts.append(sort_val)

        return "/".join(parts)


# Convenience alias
ParariusAPI = Pararius
