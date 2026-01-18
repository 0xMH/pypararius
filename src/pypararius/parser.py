"""Parser utilities for Pararius HTML responses."""

import json
import re
from typing import Optional

from .listing import Listing


def parse_search_response(data: dict, city: str) -> list[Listing]:
    """Parse the JSON response from search endpoint into list of Listings."""
    results_html = data.get("components", {}).get("results", "")
    return _parse_listings_from_html(results_html, city)


def _parse_listings_from_html(html: str, city: str) -> list[Listing]:
    """Extract listings from search results HTML."""
    listings = []

    # Split by section starts
    sections = re.split(r'<section\s+class="listing-search-item[^>]*>', html)

    for section in sections[1:]:  # Skip first split
        end_idx = section.find("</section>")
        if end_idx <= 0:
            continue

        block = section[:end_idx]
        listing = _parse_listing_block(block, city)
        if listing:
            listings.append(listing)

    return listings


def _parse_listing_block(block: str, city: str) -> Optional[Listing]:
    """Parse a single listing block from search HTML."""
    # URL and ID
    url_match = re.search(r'href="(/apartment-for-rent/[^/]+/([^/]+)/([^"]+))"', block)
    if not url_match:
        return None

    listing_id = url_match.group(2)
    street = url_match.group(3).replace("-", " ").title()
    url = f"https://www.pararius.com{url_match.group(1)}"

    # Title from analytics data (more accurate street name)
    title_match = re.search(r'element_text&quot;:&quot;([^&]+)&quot;', block)
    if title_match:
        title = title_match.group(1)
        # Extract street from title like "Flat Ridderspoorweg"
        if " " in title:
            street = " ".join(title.split()[1:])

    # Price
    price = None
    price_formatted = None
    price_match = re.search(r'listing-search-item__price-main">([^<]+)</span>', block)
    if price_match:
        price_formatted = price_match.group(1).strip()
        # Extract numeric price
        price_nums = re.sub(r'[^\d]', '', price_formatted)
        if price_nums:
            price = int(price_nums)

    # Neighborhood
    neighbourhood = None
    sub_match = re.search(r'listing-search-item__sub-title"[^>]*>\s*([^<]+)<', block)
    if sub_match:
        neighbourhood = sub_match.group(1).strip()

    # Area
    living_area = None
    area_match = re.search(r'title="(\d+)\s*m[²2]"', block)
    if area_match:
        living_area = int(area_match.group(1))

    # Rooms
    rooms = None
    rooms_match = re.search(r'title="(\d+)\s*room', block)
    if rooms_match:
        rooms = int(rooms_match.group(1))

    # Image
    photo_url = None
    img_match = re.search(r'data-src="([^"]+)"', block)
    if img_match:
        photo_url = img_match.group(1).replace("&amp;", "&")

    listing_data = {
        "title": street,
        "city": city.title(),
        "neighbourhood": neighbourhood,
        "price": price,
        "price_formatted": price_formatted,
        "living_area": living_area,
        "rooms": rooms,
        "url": url,
        "photos": [photo_url] if photo_url else [],
        "photo_urls": [photo_url] if photo_url else [],
    }

    return Listing(listing_id=listing_id, data=listing_data)


def parse_listing_details(html: str, url: str) -> Listing:
    """Parse full listing details from detail page HTML."""
    listing_id = url.split("/")[-2] if "/" in url else ""

    # Extract JSON-LD
    jsonld = _extract_jsonld(html)

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

    # Features from HTML
    features = _extract_features(html)

    # All images
    images = _extract_images(html)
    if main_image and main_image not in images:
        images.insert(0, main_image)

    # Agent/Broker
    broker = _extract_agent(html)

    # Coordinates
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
    price_formatted = f"€{price:,} per month" if price else None

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


def _extract_jsonld(html: str) -> dict:
    """Extract JSON-LD structured data from HTML."""
    matches = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    for match in matches:
        try:
            data = json.loads(match)
            type_val = data.get("@type", "")
            if "House" in str(type_val) or "Product" in str(type_val):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def _extract_features(html: str) -> dict[str, str]:
    """Extract features from listing HTML."""
    features = {}

    # Pattern 1: <dd class="listing-features__term">Term</dd> <dd ...><span>Value</span>
    pattern1 = (
        r'<dd class="listing-features__term">([^<]+)</dd>\s*'
        r'<dd class="listing-features__description[^"]*">\s*'
        r'(?:<span class="listing-features__main-description">)?([^<]+)'
    )
    for term, value in re.findall(pattern1, html):
        features[term.strip()] = value.strip().replace("&nbsp;", " ")

    # Pattern 2: <dt ...>Term</dt> <dd ...><span>Value</span> (for some features)
    pattern2 = (
        r'<dt class="listing-features__term[^"]*">([^<]+)</dt>\s*'
        r'<dd class="listing-features__description[^"]*">\s*'
        r'(?:\s*<span class="listing-features__main-description">)?([^<]+)'
    )
    for term, value in re.findall(pattern2, html):
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
    """Extract map coordinates from HTML."""
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
