"""Parser utilities for Pararius responses - extracts structured JSON-LD data."""

import json
import re
from typing import Optional

from .listing import Listing


def parse_search_response(response_text: str, city: str) -> list[Listing]:
    """Parse search results from either Pararius AJAX JSON or full HTML."""
    html = response_text

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        components = data.get("components", {})
        if isinstance(components, dict):
            results = components.get("results")
            if isinstance(results, str):
                html = results

    return parse_search_jsonld(html, city)


def parse_search_jsonld(html: str, city: str) -> list[Listing]:
    """Parse search results from JSON-LD structured data embedded in the page."""
    jsonld = _extract_jsonld_graph(html)

    # Find the WebPage/Product node with mainEntity ItemList
    for node in jsonld:
        types = node.get("@type", [])
        if isinstance(types, str):
            types = [types]
        main_entity = node.get("mainEntity", {})
        if main_entity.get("@type") == "ItemList":
            return _parse_itemlist(main_entity, city)

    return []


def _parse_itemlist(itemlist: dict, city: str) -> list[Listing]:
    """Parse an ItemList from JSON-LD into Listing objects."""
    listings = []
    for entry in itemlist.get("itemListElement", []):
        item = entry.get("item", {})
        if not item:
            continue

        url = item.get("url", "")
        # Extract listing ID from URL: .../amsterdam/2a62d10b/street
        listing_id = ""
        if url:
            parts = url.rstrip("/").split("/")
            if len(parts) >= 2:
                listing_id = parts[-2]

        # Price
        price = None
        currency = "EUR"
        offers = item.get("offers", {})
        if offers:
            price_val = offers.get("price")
            if price_val is not None:
                price = int(float(price_val))
            currency = offers.get("priceCurrency", "EUR")

        price_formatted = f"\u20ac{price:,} per month" if price else None

        # Coordinates
        geo = item.get("geo", {})
        latitude = geo.get("latitude")
        longitude = geo.get("longitude")

        # Image
        image = item.get("image")

        listing_data = {
            "title": item.get("name", ""),
            "city": city.title(),
            "price": price,
            "price_formatted": price_formatted,
            "currency": currency,
            "url": url,
            "photos": [image] if image else [],
            "photo_urls": [image] if image else [],
        }

        if latitude is not None and longitude is not None:
            listing_data["latitude"] = latitude
            listing_data["longitude"] = longitude
            listing_data["coordinates"] = (latitude, longitude)

        listings.append(Listing(listing_id=listing_id, data=listing_data))

    return listings


def parse_listing_details(html: str, url: str) -> Listing:
    """Parse full listing details from detail page JSON-LD + HTML features."""
    listing_id = url.rstrip("/").split("/")[-2] if "/" in url else ""

    # Extract JSON-LD (detail pages use a flat object, not @graph)
    jsonld = _extract_jsonld_detail(html)

    # Basic info from JSON-LD
    name = jsonld.get("name", "")
    description = jsonld.get("description")
    main_image = jsonld.get("image")

    # Address
    addr_data = jsonld.get("address", {})
    street = addr_data.get("streetAddress", "")
    city = addr_data.get("addressLocality", "")
    postcode = addr_data.get("postalCode")
    neighbourhood = addr_data.get("addressRegion")

    # Rooms and area from JSON-LD
    rooms = None
    rooms_data = jsonld.get("numberOfRooms", [])
    if rooms_data and isinstance(rooms_data, list) and len(rooms_data) > 0:
        rooms = rooms_data[0].get("value")

    living_area = None
    floor_data = jsonld.get("floorSize", {})
    if floor_data:
        living_area = floor_data.get("value")

    # Price
    price = None
    currency = "EUR"
    offer = jsonld.get("offers", {})
    if offer:
        price_str = offer.get("price")
        if price_str:
            price = int(float(price_str))
        currency = offer.get("priceCurrency", "EUR")

    # Features from HTML (not available in JSON-LD)
    features = _extract_features(html)

    # All images
    images = _extract_images(html)
    if main_image and main_image not in images:
        images.insert(0, main_image)

    # Agent/Broker
    broker = _extract_agent(html)

    # Coordinates from JSON-LD geo
    coords = None
    geo = jsonld.get("geo", {})
    if geo:
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is not None and lon is not None:
            coords = (float(lat), float(lon))

    # Fall back to HTML extraction if no geo in JSON-LD
    if not coords:
        coords = _extract_coordinates(html)

    # Extract specific features
    deposit = features.get("Deposit")
    interior = features.get("Interior")
    available = features.get("Available")
    offered_since = features.get("Offered since")
    rental_agreement = features.get("Rental agreement")
    energy_label = features.get("Energy rating")

    # Boolean features
    smoking_allowed = None
    pets_allowed = None
    if "Smoking allowed" in features:
        smoking_allowed = features["Smoking allowed"].lower() in ("yes", "ja", "allowed")
    if "Pets allowed" in features:
        pets_allowed = features["Pets allowed"].lower() in ("yes", "ja", "allowed", "in consultation")

    # Bedrooms
    bedrooms = None
    if "Number of bedrooms" in features:
        try:
            bedrooms = int(features["Number of bedrooms"])
        except ValueError:
            pass

    # Price formatted
    price_formatted = f"\u20ac{price:,} per month" if price else None

    listing_data = {
        "title": name or street,
        "city": city,
        "postcode": postcode,
        "neighbourhood": neighbourhood,
        "price": price,
        "price_formatted": price_formatted,
        "currency": currency,
        "living_area": living_area,
        "rooms": rooms,
        "bedrooms": bedrooms,
        "description": description,
        "url": url,
        "photos": images,
        "photo_urls": images,
        "photo_count": len(images),
        "energy_label": energy_label,
        "offered_since": offered_since,
        "characteristics": features,
        # Rental-specific
        "deposit": deposit,
        "interior": interior,
        "available": available,
        "rental_agreement": rental_agreement,
        "smoking_allowed": smoking_allowed,
        "pets_allowed": pets_allowed,
        "offering_type": "rent",
        "object_type": "apartment",
    }

    # Coordinates
    if coords:
        listing_data["latitude"] = coords[0]
        listing_data["longitude"] = coords[1]
        listing_data["coordinates"] = coords

    # Broker
    if broker:
        listing_data["broker"] = broker.get("name")
        listing_data["broker_url"] = broker.get("url")
        listing_data["broker_phone"] = broker.get("phone")

    return Listing(listing_id=listing_id, data=listing_data)


def _extract_jsonld_graph(html: str) -> list[dict]:
    """Extract @graph array from JSON-LD (used on search pages)."""
    matches = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        re.DOTALL,
    )
    for match in matches:
        try:
            data = json.loads(match)
            if "@graph" in data:
                return data["@graph"]
        except json.JSONDecodeError:
            continue
    return []


def _extract_jsonld_detail(html: str) -> dict:
    """Extract JSON-LD structured data from detail page HTML."""
    matches = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        re.DOTALL,
    )
    for match in matches:
        try:
            data = json.loads(match)
            type_val = data.get("@type", "")
            if "House" in str(type_val) or "Apartment" in str(type_val):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def _extract_features(html: str) -> dict[str, str]:
    """Extract features from listing HTML."""
    features = {}

    # Pattern: <dt class="listing-features__term">Term</dt> <dd ...><span>Value</span>
    pattern = (
        r'<dt class="listing-features__term[^"]*">([^<]+)</dt>\s*'
        r'<dd class="listing-features__description[^"]*">\s*'
        r'(?:\s*<span class="listing-features__main-description">)?([^<]+)'
    )
    for term, value in re.findall(pattern, html):
        features[term.strip()] = value.strip().replace("&nbsp;", " ")

    return features


def _extract_images(html: str) -> list[str]:
    """Extract all listing images from HTML."""
    images = set()
    pattern = r'(https://casco-media-prod[^"&\s]+\.(?:jpg|png|webp))'
    for img in re.findall(pattern, html):
        # Prefer full-size images
        if "width=600" in img or "width=" not in img:
            clean_url = img.replace("&amp;", "&")
            images.add(clean_url)
    return list(images)[:20]  # Limit to 20 images


def _extract_agent(html: str) -> Optional[dict]:
    """Extract agent information from HTML."""
    agent_url = None
    agent_name = None
    agent_phone = None

    url_match = re.search(r'href="(/real-estate-agent[^"]+)"', html)
    if url_match:
        agent_url = f"https://www.pararius.com{url_match.group(1)}"

    # Agent name is inside: <a class="agent-summary__title-link" ...>Name</a>
    name_match = re.search(r'agent-summary__title-link"[^>]*>([^<]+)', html)
    if name_match:
        agent_name = name_match.group(1).strip()

    phone_match = re.search(r'tel:([^"]+)', html)
    if phone_match:
        agent_phone = phone_match.group(1)

    if agent_url or agent_name:
        return {"name": agent_name, "url": agent_url, "phone": agent_phone}
    return None


def _extract_coordinates(html: str) -> Optional[tuple[float, float]]:
    """Extract map coordinates from HTML (fallback when JSON-LD has no geo)."""
    # Try data-latitude/data-longitude attributes
    match = re.search(r'data-latitude="([^"]+)"[^>]*data-longitude="([^"]+)"', html)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    # Try data-lat/data-lon attributes (fallback)
    match = re.search(r'data-lat="([^"]+)"[^>]*data-lon="([^"]+)"', html)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    # Try JSON in script
    match = re.search(r'"lat":\s*([\d.]+).*?"lon":\s*([\d.]+)', html)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    return None
