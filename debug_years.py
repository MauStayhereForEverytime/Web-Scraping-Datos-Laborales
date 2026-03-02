#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug: inspeccionar el slicer de años en la pestaña EVOLUCIÓN."""

import time, re
from playwright.sync_api import sync_playwright

URL_PAGINA = (
    "https://www2.trabajo.gob.pe/estadisticas/observatorio-de-la-formalizacion-laboral/"
    "tableros-interactivos/tablero-interactivo-del-empleo-informal-observatorio-iii/"
)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        # Cargar iframe
        page.goto(URL_PAGINA, wait_until="domcontentloaded")
        page.wait_for_selector("iframe", timeout=30000)
        time.sleep(3)

        embed_url = None
        for iframe in page.query_selector_all("iframe"):
            src = iframe.get_attribute("src") or ""
            if "app.powerbi.com" in src:
                embed_url = src
                break

        page.goto(embed_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(10)

        # Ir a EVOLUCIÓN
        try:
            btn = page.get_by_text(re.compile(r"EVOLUCI", re.IGNORECASE)).first
            btn.click(force=True)
        except Exception as e:
            print(f"WARN: {e}")
        time.sleep(10)

        # Seleccionar Loreto primero
        try:
            loc = page.get_by_text("Loreto", exact=True).first
            loc.click(force=True)
            time.sleep(3)
        except Exception:
            pass

        page.screenshot(path="debug_year_slicer_full.png")

        # Buscar todos los elementos que contengan texto de años
        print("\n=== Buscando elementos con texto de años ===")
        for year in ["2016", "2017", "2020", "2022", "2025"]:
            try:
                els = page.get_by_text(year, exact=True).all()
                print(f"\n'{year}': {len(els)} elementos encontrados")
                for i, el in enumerate(els):
                    try:
                        bb = el.bounding_box()
                        visible = el.is_visible()
                        tag = el.evaluate("e => e.tagName")
                        cls = el.evaluate("e => e.className")
                        parent_cls = el.evaluate("e => e.parentElement?.className || ''")
                        text = el.inner_text()
                        print(f"  [{i}] tag={tag} visible={visible} bb={bb}")
                        print(f"       class='{cls}' parent_class='{parent_cls}'")
                        print(f"       text='{text[:50]}'")
                    except Exception as ex:
                        print(f"  [{i}] error: {ex}")
            except Exception as e:
                print(f"'{year}': error - {e}")

        # Buscar elementos tipo slicer
        print("\n=== Buscando slicers (visual-container) ===")
        visuals = page.query_selector_all(".visual-container")
        print(f"Total visual-containers: {len(visuals)}")
        for i, v in enumerate(visuals):
            try:
                bb = v.bounding_box()
                text = v.inner_text()[:100].replace('\n', ' | ')
                print(f"  [{i}] bb={bb} text='{text}'")
            except Exception:
                pass

        # Buscar el slicer de años específicamente
        print("\n=== Buscando slicer con años (chiclet/timeline) ===")
        for sel in [
            "[class*='slicer']",
            "[class*='Slicer']",
            "[aria-label*='año']",
            "[aria-label*='year']",
            "[aria-label*='Año']",
            "[class*='timeline']",
            "[class*='chiclet']",
            "[role='slider']",
            "[role='listbox']",
            "button",
        ]:
            try:
                els = page.query_selector_all(sel)
                if els:
                    print(f"\n'{sel}': {len(els)} elementos")
                    for j, el in enumerate(els[:5]):
                        try:
                            bb = el.bounding_box()
                            text = el.inner_text()[:80].replace('\n', ' | ')
                            aria = el.get_attribute("aria-label") or ""
                            print(f"  [{j}] bb={bb} aria='{aria}' text='{text}'")
                        except Exception:
                            pass
            except Exception:
                pass

        # Dump del HTML de la zona superior (slicer area)
        print("\n=== HTML del área de slicers ===")
        try:
            # Get all elements in the top portion of the page (y < 200)
            all_elements = page.evaluate("""() => {
                const results = [];
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const rect = el.getBoundingClientRect();
                    if (rect.top > 0 && rect.top < 150 && rect.width > 50 && rect.height > 10) {
                        results.push({
                            tag: el.tagName,
                            class: el.className?.toString()?.substring(0, 80) || '',
                            text: el.innerText?.substring(0, 60) || '',
                            aria: el.getAttribute('aria-label') || '',
                            role: el.getAttribute('role') || '',
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                        });
                    }
                }
                return results.slice(0, 40);
            }""")
            for el in all_elements:
                print(f"  {el['tag']} x={el['x']} y={el['y']} w={el['w']} h={el['h']}")
                print(f"    class='{el['class']}' role='{el['role']}' aria='{el['aria']}'")
                if el['text']:
                    print(f"    text='{el['text'][:60]}'")
        except Exception as e:
            print(f"Error: {e}")

        input("\nPresiona Enter para cerrar...")
        browser.close()


if __name__ == "__main__":
    main()
