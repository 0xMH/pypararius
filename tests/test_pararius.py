import json

from pypararius import Pararius


SEARCH_HTML = """
<html>
  <head>
    <script data-test="fixture" type="application/ld+json">
      {
        "@graph": [
          {
            "@type": "WebPage",
            "mainEntity": {
              "@type": "ItemList",
              "itemListElement": [
                {
                  "@type": "ListItem",
                  "item": {
                    "@type": ["Apartment", "Product"],
                    "url": "https://www.pararius.com/apartment-for-rent/amsterdam/d1342a43/distelweg",
                    "name": "Distelweg",
                    "offers": {
                      "price": 1900,
                      "priceCurrency": "EUR"
                    },
                    "image": "https://example.com/photo.jpg",
                    "geo": {
                      "latitude": 52.394753106,
                      "longitude": 4.899563342
                    }
                  }
                }
              ]
            }
          }
        ]
      }
    </script>
  </head>
</html>
"""


class FakeResponse:
    status_code = 200
    url = "https://www.pararius.com/apartments/amsterdam"

    def __init__(self, text: str):
        self.text = text


class FakeSession:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.response_text)


def test_search_listing_parses_ajax_response():
    session = FakeSession(json.dumps({"components": {"results": SEARCH_HTML}}))
    pararius = Pararius()
    pararius._session = session

    results = pararius.search_listing("amsterdam")

    assert len(results) == 1
    assert results[0]["title"] == "Distelweg"
    assert results[0]["price"] == 1900
    assert results[0]["coordinates"] == (52.394753106, 4.899563342)

    _, request_kwargs = session.calls[0]
    assert request_kwargs["headers"]["X-Requested-With"] == "XMLHttpRequest"
    assert "application/json" in request_kwargs["headers"]["Accept"]


def test_search_listing_still_parses_html_response():
    session = FakeSession(SEARCH_HTML)
    pararius = Pararius()
    pararius._session = session

    results = pararius.search_listing("amsterdam")

    assert len(results) == 1
    assert results[0]["url"] == "https://www.pararius.com/apartment-for-rent/amsterdam/d1342a43/distelweg"
