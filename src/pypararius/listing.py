"""Listing class - represents a Pararius property listing."""

from typing import Any


class Listing:
    """A Pararius property listing.

    Data can be accessed as listing['key'] or listing.get('key').

    Example:
        >>> listing = pararius.get_listing('amsterdam/abc123/street')
        >>> listing['title']
        'Ridderspoorweg 10'
        >>> listing['price']
        1850
        >>> listing['city']
        'Amsterdam'
    """

    keys_alias = {
        'name': 'title',
        'address': 'title',
        'location': 'city',
        'locality': 'city',
        'area': 'living_area',
        'size': 'living_area',
        'area_m2': 'living_area',
        'coords': 'coordinates',
        'lat': 'latitude',
        'lng': 'longitude',
        'lon': 'longitude',
        'zip': 'postcode',
        'zipcode': 'postcode',
        'postal_code': 'postcode',
        'type': 'object_type',
        'property_type': 'object_type',
        'images': 'photos',
        'pictures': 'photos',
        'media': 'photos',
        'desc': 'description',
        'text': 'description',
        'agent': 'broker',
        'realtor': 'broker',
        'makelaar': 'broker',
        'energy_rating': 'energy_label',
        'street': 'title',
    }

    def __init__(self, listing_id: str | int | None = None, data: dict | None = None):
        self.listing_id = str(listing_id) if listing_id else None
        self.data: dict[str, Any] = data or {}

    def __repr__(self) -> str:
        title = self.data.get('title', 'Unknown')
        city = self.data.get('city', '')
        return f"<Listing id:{self.listing_id} [{title}, {city}]>"

    def __str__(self) -> str:
        return self.__repr__()

    def __contains__(self, key: str) -> bool:
        return self._normalize_key(key) in self.data

    def __getitem__(self, key: str) -> Any:
        normalized = self._normalize_key(key)
        if normalized not in self.data:
            raise KeyError(key)
        return self.data[normalized]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[self._normalize_key(key)] = value

    def __bool__(self) -> bool:
        return bool(self.listing_id or self.data.get('title'))

    def _normalize_key(self, key: str) -> str:
        """Normalize key using aliases."""
        key = key.lower().replace('-', '_').replace(' ', '_')
        return self.keys_alias.get(key, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value with optional default."""
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> list[str]:
        """Return all available keys."""
        return list(self.data.keys())

    def items(self) -> list[tuple[str, Any]]:
        """Return all key-value pairs."""
        return list(self.data.items())

    def values(self) -> list[Any]:
        """Return all values."""
        return list(self.data.values())

    def to_dict(self) -> dict[str, Any]:
        """Return data as a plain dictionary."""
        return self.data.copy()

    def summary(self) -> str:
        """Return a text summary of the listing."""
        lines = []
        title = self.data.get('title', 'Unknown')
        city = self.data.get('city', '')
        lines.append(f"Listing: {title}, {city}")

        if price := self.data.get('price_formatted'):
            lines.append(f"Price: {price}")
        elif price := self.data.get('price'):
            lines.append(f"Price: €{price:,}")

        if area := self.data.get('living_area'):
            lines.append(f"Living area: {area} m²")

        if bedrooms := self.data.get('bedrooms'):
            lines.append(f"Bedrooms: {bedrooms}")

        if energy := self.data.get('energy_label'):
            lines.append(f"Energy label: {energy}")

        if url := self.data.get('url'):
            lines.append(f"URL: {url}")

        return '\n'.join(lines)

    def getID(self) -> str | None:
        """Return the listing ID."""
        return self.listing_id

    @property
    def id(self) -> str | None:
        """Alias for listing_id."""
        return self.listing_id
