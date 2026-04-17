import requests
import json
import time
from urllib.parse import urljoin
from datetime import datetime, timezone


SITES = [
    {
        "name":     "IMUSA Colombia",
        "country":  "Colombia",
        "base_url": "https://www.imusa.com.co",
        "filename": "imusa_co_products.json"
    },
    {
        "name":     "T-Fal México",
        "country":  "México",
        "base_url": "https://www.t-fal.com.mx",
        "filename": "tfal_mx_products.json"
    },
    {
        "name":     "Krups México",
        "country":  "México",
        "base_url": "https://www.krups.com.mx",
        "filename": "krups_mx_products.json"
    },
    {
        "name":     "Rowenta México",
        "country":  "México",
        "base_url": "https://www.rowenta.com.mx",
        "filename": "rowenta_mx_products.json"
    },
    {
        "name":     "Tefal Store Chile",
        "country":  "Chile",
        "base_url": "https://www.tefalstore.cl",
        "filename": "tefal_cl_products.json"
    }
]

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
}

# ── FUNCIÓN: construir URL correcta ───────────────────────────
def build_url(base_url, link):
    """
    Evita duplicar el base_url.
    Ejemplos:
      link = "/producto/p"             → https://base/producto/p
      link = "https://base/producto/p" → https://base/producto/p  (sin duplicar)
      link = "https://otro/producto/p" → lo deja tal cual
    """
    if not link:
        return base_url
    if link.startswith("http"):
        return link  # ya es URL completa
    return base_url.rstrip("/") + "/" + link.lstrip("/")


# ── FUNCIÓN: extraer precio ────────────────────────────────────
def extract_price(product):
    """
    En VTEX el precio viene en items > sellers > commertialOffer
    """
    try:
        items = product.get("items", [])
        if not items:
            return None

        for item in items:
            sellers = item.get("sellers", [])
            for seller in sellers:
                offer = seller.get("commertialOffer", {})
                price = offer.get("Price", 0)
                list_price = offer.get("ListPrice", 0)
                if price and price > 0:
                    return {
                        "price":      price,
                        "list_price": list_price,
                        "on_sale":    list_price > price
                    }
    except Exception:
        pass
    return {"price": None, "list_price": None, "on_sale": False}


# ── FUNCIÓN PRINCIPAL ──────────────────────────────────────────
def scrape_site(site):
    print(f"\n{'='*55}")
    print(f"🌐 {site['name']} ({site['country']})")
    print(f"{'='*55}")

    all_products = []
    page         = 0
    page_size    = 49
    base_url     = site["base_url"]

    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Referer": base_url,
        "Origin":  base_url
    })

    print("🔄 Iniciando sesión...")
    try:
        session.get(base_url, timeout=15)
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Error en visita inicial: {e}")

    while True:
        _from = page * page_size
        _to   = _from + page_size - 1

        url    = f"{base_url}/api/catalog_system/pub/products/search"
        params = {"_from": _from, "_to": _to, "O": "OrderByTopSaleDESC"}

        print(f"📦 Página {page + 1} (productos {_from}–{_to})...")

        try:
            response = session.get(url, params=params, timeout=15)
            print(f"   → Status: {response.status_code}")

            if response.status_code in [200, 206]:
                try:
                    products = response.json()
                except Exception:
                    print("   ⚠️ Respuesta no es JSON válido")
                    break

                if not products:
                    print("   ✅ Sin más productos")
                    break

                for p in products:
                    try:
                        items = p.get("items", [])
                        image = ""
                        skus  = []

                        if items:
                            images = items[0].get("images", [])
                            image  = images[0].get("imageUrl", "") if images else ""
                            skus   = [
                                {
                                    "sku_id":   s.get("itemId", ""),
                                    "sku_name": s.get("name", ""),
                                    "image":    s["images"][0]["imageUrl"] if s.get("images") else ""
                                }
                                for s in items
                            ]

                        # ✅ URL corregida
                        raw_link = p.get("link", "") or p.get("linkText", "")
                        if raw_link and not raw_link.startswith("http"):
                            product_url = build_url(base_url, raw_link)
                        elif raw_link.startswith("http"):
                            product_url = raw_link
                        else:
                            product_url = base_url

                        # ✅ Categoría limpia
                        raw_cats = p.get("categories", [])
                        if raw_cats:
                            # Toma la categoría más específica (última)
                            category = [c for c in raw_cats[0].split("/") if c]
                            category = category[-1] if category else "General"
                        else:
                            category = "General"

                        # ✅ Precio
                        pricing = extract_price(p)

                        all_products.append({
                            "name":        p.get("productName", "Sin nombre"),
                            "reference":   p.get("productReference", "N/A"),
                            "brand":       p.get("brand", site["name"]),
                            "category":    category,
                            "description": p.get("description", ""),
                            "url":         product_url,
                            "image":       image,
                            "skus":        skus,
                            "site":        site["name"],
                            "country":     site["country"],
                            "price":       pricing["price"],
                            "list_price":  pricing["list_price"],
                            "on_sale":     pricing["on_sale"]
                        })

                    except Exception as e:
                        print(f"   ⚠️ Error en producto: {e}")
                        continue

                print(f"   ✅ {len(products)} productos procesados")
                page += 1
                time.sleep(1)

            elif response.status_code == 404:
                print("   ✅ Fin de productos (404)")
                break

            else:
                print(f"   ❌ Error {response.status_code}")
                break

        except requests.exceptions.Timeout:
            print("   ⏱️ Timeout — reintentando...")
            time.sleep(5)
            continue

        except Exception as e:
            print(f"   ❌ Error: {e}")
            break

    with open(site["filename"], "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"\n💾 {len(all_products)} productos → {site['filename']}")
    return all_products


# ── EJECUTAR ───────────────────────────────────────────────────
print("🚀 Iniciando scraper multi-sitio...\n")

all_sites_products = []
summary = []

for site in SITES:
    products = scrape_site(site)
    all_sites_products.extend(products)
    summary.append({"site": site["name"], "total": len(products)})
    time.sleep(2)

with open("all_products.json", "w", encoding="utf-8") as f:
    json.dump(all_sites_products, f, ensure_ascii=False, indent=2)

print(f"\n{'='*55}")
print("📊 RESUMEN FINAL")
print(f"{'='*55}")
for s in summary:
    print(f"  {s['site']:<30} → {s['total']:>4} productos")
print(f"{'─'*55}")
print(f"  {'TOTAL':<30} → {len(all_sites_products):>4} productos")
print(f"\n✅ all_products.json listo!")

update_info = {
    "last_update": datetime.now(timezone.utc).isoformat(),
    "total_products": len(all_sites_products),
    "by_site": summary
}

with open("last_update.json", "w", encoding="utf-8") as f:
    json.dump(update_info, f, ensure_ascii=False, indent=2)

print("✅ last_update.json guardado")
