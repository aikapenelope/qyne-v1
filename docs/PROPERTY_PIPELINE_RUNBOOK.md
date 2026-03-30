# QYNE v1 — Property Pipeline Runbook

## Standard Property JSON Schema

Every property from every source MUST produce this exact JSON structure.
Fields marked REQUIRED must always have a value. Fields marked OPTIONAL
can be null but must exist in the record.

```json
{
  "title": "Apartamento en Alquiler en Manzanares, Caracas",
  "description": "Full description text from the listing...",
  "operation": "alquiler",
  "price": 700,
  "currency": "USD",
  "price_per_m2": 5.6,
  "price_category": "budget",
  "location": "Manzanares, Caracas, Distrito Metropolitano",
  "city": "Caracas",
  "state": "Distrito Metropolitano",
  "neighborhood": "Manzanares",
  "country": "VE",
  "bedrooms": 3,
  "bathrooms": 3,
  "parking": 2,
  "area_m2": 125,
  "property_type": "apartment",
  "operation": "alquiler",
  "images": [
    {"url": "https://cdn.example.com/photo1.jpg", "order": 0, "source": "site_cdn"}
  ],
  "features": ["Planta Electrica", "Vigilancia Privada"],
  "construction_details": {"pisos": "Ceramica", "pisos_totales": 12},
  "realtor_name": "Rosanna Di Rocco",
  "realtor_phone": "584223274689",
  "external_id": "VE 26-17209",
  "url": "https://rentahouse.com.ve/...",
  "source": "rentahouse_ve",
  "status": "active",
  "scraped_at": "2026-03-30T21:57:11Z",
  "last_verified_at": "2026-04-06T03:00:00Z",
  "sold_at": null,
  "days_on_market": null,
  "price_history": [{"price": 750, "date": "2026-03-15"}]
}
```

## Field Definitions

### REQUIRED Fields (must always have a value)

| Field | Type | Rules |
|-------|------|-------|
| `title` | string | Clean title. NO raw HTML, NO line breaks, NO price in title. Format: "{Type} en {Operation} en {Neighborhood}, {City}" |
| `price` | float | Numeric only. No currency symbols. 0 if free. |
| `currency` | string | ISO: "USD", "VES", "COP". Default: "USD" |
| `operation` | string | Exactly: "venta" or "alquiler" |
| `city` | string | City name, capitalized |
| `country` | string | ISO 2-letter: "VE", "CO", "MX" |
| `url` | string | Full URL to the listing page |
| `source` | string | Site identifier: "rentahouse_ve", "mercadolibre_ve" |
| `status` | string | Lifecycle: "scraped", "active", "sold", "removed" |
| `scraped_at` | timestamp | ISO 8601 UTC |
| `images` | json[] | At least 1 image. Each: {url, order, source} |

### OPTIONAL Fields (can be null)

| Field | Type | Rules |
|-------|------|-------|
| `description` | text | Full listing description. Max 5000 chars. |
| `state` | string | State/province name |
| `neighborhood` | string | Urbanization/neighborhood |
| `bedrooms` | integer | null for commercial/land |
| `bathrooms` | integer | TOTAL bathrooms (full + half). Not just half baths. |
| `parking` | integer | Number of parking spots |
| `area_m2` | float | Total area in square meters |
| `property_type` | string | See Property Types table below |
| `features` | json[] | Array of strings. Clean text, no symbols (no #, no ✅) |
| `construction_details` | json | Key-value pairs. Keys in snake_case. |
| `realtor_name` | string | Full name of the listing agent |
| `realtor_phone` | string | Phone number, digits only, with country code |
| `external_id` | string | Site-specific ID (RAH code, MLS number) |
| `price_per_m2` | float | Computed: price / area_m2 |
| `price_category` | string | Computed: see Price Categories |
| `location` | string | Computed: "{neighborhood}, {city}, {state}" |
| `last_verified_at` | timestamp | Last time URL was checked alive |
| `sold_at` | timestamp | When property was detected as sold (404) |
| `days_on_market` | integer | Computed: sold_at - scraped_at (in days) |
| `price_history` | json[] | Array of {price, date} for price changes |

## Property Types

| Value | Matches |
|-------|---------|
| `apartment` | apartamento, apto, penthouse, ph |
| `house` | casa, townhouse, quinta |
| `land` | terreno, lote, parcela, finca |
| `commercial` | comercial, local, oficina, galpon, negocio, industrial |
| `other` | anything not matched above |

## Price Categories

| Category | Range (USD) |
|----------|-------------|
| `budget` | < $50,000 |
| `mid` | $50,000 - $200,000 |
| `premium` | $200,000 - $500,000 |
| `luxury` | > $500,000 |

For rentals:
| Category | Range (USD/month) |
|----------|-------------------|
| `budget` | < $500 |
| `mid` | $500 - $1,500 |
| `premium` | $1,500 - $5,000 |
| `luxury` | > $5,000 |

## Title Cleaning Rules

Raw titles from scraping are often dirty. Clean them:

| Bad | Good |
|-----|------|
| `"Código RAH: VE 26-17209 \n Apartamento en Alquiler..."` | `"Apartamento en Alquiler en Manzanares, Caracas"` |
| `"VENTA - Casa 3 hab - USD 120.000"` | `"Casa en Venta en Alta Florida, Caracas"` |
| `"  Terreno   en   venta  "` | `"Terreno en Venta en Caicaguana, Caracas"` |

Format: `"{PropertyType} en {Operation} en {Neighborhood}, {City}"`

## Feature Cleaning Rules

| Bad | Good |
|-----|------|
| `"✅ Planta Electrica"` | `"Planta Electrica"` |
| `"#Ascensores"` | `"Ascensor"` |
| `"❌ Pozo: No"` | (don't include — only positive features) |
| `"Tiene Cocina?"` | `"Cocina"` |

## Image Schema

```json
{
  "url": "https://cdn.example.com/1280x1024/photo.jpg",
  "order": 0,
  "source": "rentahouse_cdn"
}
```

- `url`: Direct link to image. Prefer 1280x1024 resolution.
- `order`: 0-based index. First image is the cover photo.
- `source`: CDN identifier for tracking.

## Construction Details Schema

```json
{
  "pisos": "Ceramica",
  "pisos_totales": 12,
  "estilo": "1 Nivel",
  "estado_inmueble": "Usado",
  "amoblado": false
}
```

Keys in snake_case Spanish. Values as strings or numbers.

## Pipeline Lifecycle

```
1. SCRAPE    → Fetch listing + detail pages
2. NORMALIZE → Clean data to match this schema
3. VALIDATE  → Reject if missing: price, url, city, at least 1 image
4. DEDUP     → Check URL exists. If yes: update price + last_verified_at
5. ENRICH    → Compute: price_per_m2, price_category, location string
6. STORE     → Write to Directus properties collection
7. ALERT     → If 0 items fetched: create critical alert
```

## Adding a New Site

1. Add config to `SITE_CONFIGS` in `property_pipeline.py`
2. Define CSS selectors for listing page cards
3. If site needs detail page scraping: set `scrape_details: True`
4. Add site-specific parsing in `fetch_detail_page` if HTML structure differs
5. Test with `max_pages=1` and verify JSON matches this schema
6. Verify: title is clean, bathrooms are total, features have no symbols
7. Register deployment in Prefect

## Monitoring

| Check | Frequency | Alert |
|-------|-----------|-------|
| Selector health | Weekly | If 0 items extracted from any site |
| URL freshness | Weekly | Properties with 404 marked as sold |
| Price changes | Every scrape | Logged in price_history |
| Zero results | Every scrape | Critical alert in Directus events |
| Data quality | Monthly | Manual review of sample records |

## Known Issues to Fix

1. **Title not cleaned**: Still contains RAH code and line breaks
2. **Bathrooms**: Only captures half baths, not total
3. **property_type**: "negocios" maps to "other" instead of "commercial"
4. **Features**: Still have # and ? symbols
5. **price_category**: Doesn't distinguish venta vs alquiler ranges
6. **construction_details keys**: Not in snake_case
