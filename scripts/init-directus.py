#!/usr/bin/env python3
"""
QYNE v1 — Initialize Directus collections and set static API token.

Run after first `docker compose up` when Directus is healthy.
Usage: python3 scripts/init-directus.py
"""

import json
import os
import sys
import urllib.request
import urllib.error

BASE = os.getenv("DIRECTUS_URL", "http://127.0.0.1:8055")
EMAIL = os.getenv("DIRECTUS_ADMIN_EMAIL", "admin@qyne.dev")
PASSWORD = os.getenv("DIRECTUS_ADMIN_PASSWORD", "")
STATIC_TOKEN = os.getenv("DIRECTUS_TOKEN", "")


def api(token, method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def login():
    body = json.dumps({"email": EMAIL, "password": PASSWORD}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=body)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())["data"]["access_token"]


# Business collections schema
COLLECTIONS = {
    "contacts": [
        "first_name:string", "last_name:string", "email:string", "phone:string",
        "company:string", "product:string", "lead_score:integer",
        "source:string", "status:string", "notes:text",
    ],
    "companies": [
        "name:string", "domain:string", "industry:string",
        "employees:integer", "address:string",
    ],
    "conversations": [
        "channel:string", "direction:string", "raw_message:text",
        "agent_response:text", "intent:string", "sentiment:string",
        "lead_score:integer", "agent_name:string",
    ],
    "tickets": [
        "product:string", "intent:string", "summary:text",
        "resolution:text", "urgency:string", "status:string",
    ],
    "tasks": [
        "title:string", "body:text", "status:string", "assigned_to:string",
    ],
    "payments": [
        "product:string", "amount:float", "method:string",
        "reference:string", "status:string", "approved_by:string",
    ],
    "documents": [
        "title:string", "content:text", "source_file:string", "status:string",
    ],
    "emails": [
        "subject:string", "body:text", "sender:string", "has_attachment:boolean",
    ],
    "scraped_data": [
        "title:string", "url:string", "content:text", "source:string",
    ],
    "events": [
        "type:string", "payload:json",
    ],
    "properties": [
        "title:string", "description:text", "price:float", "currency:string",
        "price_per_m2:float", "price_category:string",
        "location:string", "city:string", "country:string",
        "latitude:float", "longitude:float",
        "bedrooms:integer", "bathrooms:integer", "area_m2:float",
        "property_type:string", "images:json", "features:json",
        "url:string", "source:string", "status:string", "scraped_at:timestamp",
    ],
}


def main():
    if not PASSWORD:
        print("Set DIRECTUS_ADMIN_PASSWORD env var")
        sys.exit(1)

    print(f"Connecting to {BASE}...")
    token = login()
    print(f"Authenticated as {EMAIL}")

    # Create collections
    for name, fields in COLLECTIONS.items():
        code, _ = api(token, "POST", "/collections", {
            "collection": name, "meta": {}, "schema": {},
        })
        status = "created" if code in (200, 204) else "exists"
        print(f"  {name}: {status}")

        for f in fields:
            fname, ftype = f.split(":")
            api(token, "POST", f"/fields/{name}", {
                "field": fname, "type": ftype, "meta": {}, "schema": {},
            })

        # Add system tracking fields (date_created, date_updated, user_created, user_updated)
        system_fields = [
            {"field": "date_created", "type": "timestamp", "meta": {"special": ["date-created"], "interface": "datetime", "readonly": True, "hidden": True, "width": "half"}, "schema": {}},
            {"field": "date_updated", "type": "timestamp", "meta": {"special": ["date-updated"], "interface": "datetime", "readonly": True, "hidden": True, "width": "half"}, "schema": {}},
            {"field": "user_created", "type": "uuid", "meta": {"special": ["user-created"], "interface": "select-dropdown-m2o", "readonly": True, "hidden": True, "width": "half"}, "schema": {}},
            {"field": "user_updated", "type": "uuid", "meta": {"special": ["user-updated"], "interface": "select-dropdown-m2o", "readonly": True, "hidden": True, "width": "half"}, "schema": {}},
        ]
        for sf in system_fields:
            api(token, "POST", f"/fields/{name}", sf)

    # Set static token for API access
    if STATIC_TOKEN:
        code, data = api(token, "GET", "/users/me")
        if code == 200:
            user_id = data["data"]["id"]
            api(token, "PATCH", f"/users/{user_id}", {"token": STATIC_TOKEN})
            print(f"\nStatic API token set for admin user")

    print("\nDone! Directus is ready.")
    print(f"  Admin UI: {BASE}")
    print(f"  API: {BASE}/items/contacts")


if __name__ == "__main__":
    main()
