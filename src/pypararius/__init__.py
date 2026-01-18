"""
Pararius - Python API for Pararius.com real estate listings.

Example usage:
    >>> from pypararius import Pararius
    >>> p = Pararius()
    >>> listing = p.get_listing('amsterdam/abc123/street')
    >>> print(listing['title'], listing['price'])
    Ridderspoorweg 10 1850

    >>> results = p.search_listing('amsterdam', price_max=2000)
    >>> for r in results[:3]:
    ...     print(r['title'], r['city'])
"""

from pypararius.pararius import Pararius, ParariusAPI
from pypararius.listing import Listing

__version__ = "2.0.0"
__all__ = ["Pararius", "ParariusAPI", "Listing"]
