#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  Scraper MTPE – Empleo Formal (Planilla Electrónica)         ║
║  Extrae: Año, Mes, Región, Empleo                            ║
║  Método: Right-click → "Mostrar como tabla" en Power BI      ║
╚══════════════════════════════════════════════════════════════╝
Estrategia:
  1. Abrir reporte Power BI → pestaña EVOLUCIÓN
  2. Seleccionar cada región en el slicer
  3. Right-click gráfico → "Mostrar como tabla"
  4. Scraping de la tabla DOM resultante
  5. Repetir por cada región → CSV + XLSX
"""

import time, re
import pandas as pd
from playwright.sync_api import sync_playwright

URL_PAGINA = (
    "https://www2.trabajo.gob.pe/estadisticas/observatorio-de-la-formalizacion-laboral/"
    "tableros-interactivos/tablero-interactivo-del-empleo-informal-observatorio-iii/"
)

REGIONES = [
    "Perú", "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho",
    "Cajamarca", "Callao", "Cusco", "Huancavelica", "Huánuco", "Ica",
    "Junín", "La Libertad", "Lambayeque", "Lima Metropolitana",
    "Lima Provincias", "Loreto", "Madre de Dios", "Moquegua", "Pasco",
    "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali",
]


def find_chart_visual(page):
    """
    Encuentra el contenedor visual del gráfico 'NÚMERO DE TRABAJADORES'.
    Retorna el locator del container visual o None.
    """
    # Power BI visuals are in .visual-container elements
    # Find the one that contains "NÚMERO DE TRABAJADORES"
    try:
        header = page.get_by_text("NÚMERO DE TRABAJADORES", exact=False).first
        # Navigate up to the visual container
        # The visual container is typically a parent with class 'visual-container'
        visual = header.locator("xpath=ancestor::*[contains(@class,'visual')]").first
        return visual
    except Exception:
        pass
    return None


def extract_table_data(page, timeout_s=15):
    """
    Después de hacer 'Mostrar como tabla', extrae las filas de la tabla.
    Power BI usa virtual scrolling, así que scrolleamos para capturar todo.
    Retorna lista de dicts {grupo, fecha_str, valor_str}.
    """
    # Wait for table to render
    time.sleep(3)

    # Regex: Año, Mes-Año, Valor (valor MUST contain a period = thousands sep)
    ROW_RE = re.compile(
        r"(\d{4})[\s\n,]+((?:Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)-\d{4})"
        r"[\s\n,]+(\d{1,3}(?:\.\d{3})+)",
        re.IGNORECASE,
    )

    all_found = {}  # fecha_str → {grupo, fecha_str, valor_str}  dedup by date

    # --- First extraction from current view ---
    def _extract_from_body():
        try:
            body_text = page.inner_text("body")
            matches = ROW_RE.findall(body_text)
            for m in matches:
                fecha = m[1]
                if fecha not in all_found:
                    all_found[fecha] = {
                        "grupo": m[0],
                        "fecha_str": fecha,
                        "valor_str": m[2],
                    }
        except Exception:
            pass

    _extract_from_body()
    initial_count = len(all_found)
    print(f" [{initial_count} visible]", end="", flush=True)

    # --- Click inside the table to focus it, then scroll with keyboard ---
    # Find the table area: look for a cell with a date pattern
    try:
        date_cell = page.get_by_text(re.compile(r"Ene-\d{4}"), exact=False).first
        date_cell.click(force=True)
        time.sleep(0.5)
    except Exception:
        pass

    # Scroll with Ctrl+End to jump to bottom, extract, then Ctrl+Home back up
    for scroll_round in range(30):
        try:
            page.keyboard.press("PageDown")
            time.sleep(0.6)
            _extract_from_body()
            # If no new data found in 2 consecutive scrolls, stop
            if len(all_found) == initial_count and scroll_round > 2:
                break
            initial_count = len(all_found)
        except Exception:
            break

    # Sort by date
    rows = sorted(all_found.values(), key=lambda r: r["fecha_str"])
    return rows


def _parse_grid_cells(texts):
    """Intenta agrupar textos planos de gridcells en filas de 3."""
    rows = []
    # Filter out empty/header-like texts
    cleaned = [t for t in texts if t]

    # Detect column count by looking for date patterns
    date_pat = re.compile(r"(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)-\d{4}")
    date_indices = [i for i, t in enumerate(cleaned) if date_pat.search(t)]

    if not date_indices:
        return []

    # If dates are at positions 1, 4, 7... → 3 columns per row
    # If dates are at positions 1, 3, 5... → 2 columns per row
    if len(date_indices) >= 2:
        step = date_indices[1] - date_indices[0]
    else:
        step = 3  # assume 3 columns

    first_date_col = date_indices[0] % step

    if step == 3:
        for i in range(0, len(cleaned) - step + 1, step):
            rows.append({
                "grupo": cleaned[i],
                "fecha_str": cleaned[i + 1],
                "valor_str": cleaned[i + 2],
            })
    elif step == 2:
        for i in range(0, len(cleaned) - step + 1, step):
            rows.append({
                "grupo": "",
                "fecha_str": cleaned[i],
                "valor_str": cleaned[i + 1],
            })

    return rows


def parse_valor(val_str):
    """Convierte '36.641' o '3.770.677' a int (formato español: punto = miles)."""
    s = val_str.strip()
    # Our regex already guarantees format: digits + groups of .ddd
    # e.g. "36.641" → 36641, "3.770.677" → 3770677
    return int(s.replace(".", ""))


def switch_back_to_chart(page):
    """Vuelve de modo tabla a modo gráfico."""
    try:
        # Try right-click and "Volver al gráfico" or "Back to chart"
        # First try the back/chart icon button that appears
        back_btn = page.get_by_text(re.compile(r"Volver al gr|Back to|Mostrar como gr", re.IGNORECASE)).first
        back_btn.click(force=True)
        time.sleep(1)
        return True
    except Exception:
        pass

    try:
        # Try finding a back arrow or chart icon
        # Power BI adds a small button to switch back
        icons = page.query_selector_all("[aria-label*='chart'], [aria-label*='gráfico'], [aria-label*='Volver']")
        for icon in icons:
            if icon.is_visible():
                icon.click(force=True)
                time.sleep(1)
                return True
    except Exception:
        pass

    return False


def main():
    print("🚀 Scraper MTPE – Empleo Formal (Mostrar como tabla)")
    print("=" * 60)

    all_data = []

    with sync_playwright() as p:
        # Use headed mode for debugging (change to True for production)
        browser = p.chromium.launch(headless=False, slow_mo=300)
        # Tall viewport: Power BI table renders more rows with more vertical space
        ctx = browser.new_context(viewport={"width": 1920, "height": 3000})
        page = ctx.new_page()

        # ─── PASO 1: Obtener iframe Power BI ───
        print("\n[1] Buscando iframe Power BI…")
        page.goto(URL_PAGINA, wait_until="domcontentloaded")
        page.wait_for_selector("iframe", timeout=30000)
        time.sleep(3)

        embed_url = None
        for iframe in page.query_selector_all("iframe"):
            src = iframe.get_attribute("src") or ""
            if "app.powerbi.com" in src:
                embed_url = src
                break

        if not embed_url:
            print("❌ No encontré iframe Power BI.")
            browser.close()
            return
        print(f"  ✅ {embed_url[:80]}…")

        # ─── PASO 2: Cargar reporte ───
        print("\n[2] Cargando reporte…")
        page.goto(embed_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(10)
        print("  ✅ Reporte cargado")

        # ─── PASO 3: Ir a EVOLUCIÓN ───
        print("\n[3] Clic en EVOLUCIÓN…")
        try:
            btn = page.get_by_text(re.compile(r"EVOLUCI", re.IGNORECASE)).first
            btn.click(force=True)
            print("  ✅")
        except Exception as e:
            print(f"  ⚠️ {e}")

        time.sleep(10)
        page.screenshot(path="debug_01_evolucion.png")

        # ─── PASO 4: Iterar regiones con right-click per region ───
        # Para cada región:
        #   1. Click región (single-select slicer: auto-deselects previous)
        #   2. Wait for chart to update
        #   3. Right-click chart → "Mostrar como tabla"
        #   4. Extract table data
        #   5. "Volver al gráfico" (right-click or button)
        print(f"\n[4] Extrayendo datos para {len(REGIONES)} regiones…\n")
        failed = []

        def find_chart_coords():
            """Recalcula coordenadas del centro del gráfico CADA VEZ."""
            try:
                title = page.get_by_text("NÚMERO DE TRABAJADORES", exact=False).first
                bb = title.bounding_box()
                if bb:
                    return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] + 150
            except Exception:
                pass
            # Fallback: try a visual container
            try:
                vis = page.locator(".visual-container").nth(0)
                bb = vis.bounding_box()
                if bb:
                    return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
            except Exception:
                pass
            return 960, 800  # absolute fallback

        def go_back_to_chart():
            """Tries multiple methods to return from table to chart mode."""
            # Method 1: Look for a back-to-chart toggle icon/button
            for selector in [
                "[aria-label*='gráfico']",
                "[aria-label*='chart']",
                "[aria-label*='Volver']",
                "[aria-label*='Back']",
                ".backToVisualization",
                "[title*='Volver']",
                "[title*='Back']",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=500):
                        el.click(force=True)
                        time.sleep(2)
                        return True
                except Exception:
                    continue

            # Method 2: Right-click → "Volver al gráfico"
            cx, cy = find_chart_coords()
            page.mouse.click(cx, cy, button="right")
            time.sleep(1.5)
            try:
                back = page.get_by_text(
                    re.compile(r"Volver al gr|Back to|Mostrar como gr", re.IGNORECASE)
                ).first
                back.click(force=True)
                time.sleep(2)
                return True
            except Exception:
                page.keyboard.press("Escape")
                time.sleep(0.5)

            # Method 3: Keyboard Escape to dismiss any overlay
            page.keyboard.press("Escape")
            time.sleep(1)
            return False

        for idx, region in enumerate(REGIONES):
            print(f"  [{idx+1}/{len(REGIONES)}] {region}", end="", flush=True)

            try:
                # 1. Click region directly (single-select slicer auto-deselects prior)
                loc = page.get_by_text(region, exact=True).first
                loc.scroll_into_view_if_needed(timeout=5000)
                time.sleep(0.3)
                loc.click(force=True)
                time.sleep(4)  # wait for chart data to load

                # 2. Find chart coords fresh
                cx, cy = find_chart_coords()

                # Debug screenshots for first 3 regions
                if idx < 3:
                    page.screenshot(path=f"debug_before_rc_{idx}_{region}.png")

                # 3. Right-click on chart
                page.mouse.click(cx, cy, button="right")
                time.sleep(2)

                if idx < 3:
                    page.screenshot(path=f"debug_context_menu_{idx}_{region}.png")

                # 4. Click "Mostrar como tabla"
                menu_found = False
                try:
                    show_table = page.get_by_text("Mostrar como tabla", exact=False).first
                    if show_table.is_visible(timeout=2000):
                        show_table.click(force=True)
                        menu_found = True
                        time.sleep(4)
                except Exception:
                    pass

                if not menu_found:
                    # Maybe it says "Show as table" (English)
                    try:
                        show_table = page.get_by_text("Show as table", exact=False).first
                        if show_table.is_visible(timeout=1000):
                            show_table.click(force=True)
                            menu_found = True
                            time.sleep(4)
                    except Exception:
                        pass

                if not menu_found:
                    # Dismiss context menu and skip
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
                    print(f" → no menu ⚠️")
                    failed.append(region)
                    # Deselect
                    loc.click(force=True)
                    time.sleep(1)
                    continue

                # 5. Extract data
                table_rows = extract_table_data(page, timeout_s=8)

                if table_rows:
                    first_val = table_rows[0]["valor_str"] if table_rows else "?"
                    for row in table_rows:
                        try:
                            all_data.append({
                                "fecha_str": row["fecha_str"],
                                "empleo": parse_valor(row["valor_str"]),
                                "región": region,
                            })
                        except Exception:
                            pass
                    print(f" → {len(table_rows)} filas (v1={first_val}) ✅")
                else:
                    failed.append(region)
                    print(f" → 0 filas ⚠️")

                # 6. Go back to chart mode
                went_back = go_back_to_chart()
                if idx < 3:
                    page.screenshot(path=f"debug_after_back_{idx}_{region}.png")
                if not went_back:
                    print(" [⚠ no back]", end="")

                # 7. NO deseleccionar — el slicer single-select reemplaza
                #    automáticamente al hacer clic en la siguiente región.
                #    Deseleccionar dejaría 0 seleccionados → Power BI carga TODO.

            except Exception as e:
                failed.append(region)
                print(f" → Error: {e}")
                page.keyboard.press("Escape")
                time.sleep(1)
                page.mouse.click(10, 10)
                time.sleep(1)

        # ─── Reintentar fallidas ───
        if failed:
            print(f"\n  Reintentando {len(failed)} regiones…")
            for region in failed[:]:
                print(f"  [retry] {region}", end="", flush=True)
                try:
                    loc = page.get_by_text(region, exact=True).first
                    loc.scroll_into_view_if_needed(timeout=5000)
                    time.sleep(1)
                    loc.click(force=True)
                    time.sleep(5)

                    cx, cy = find_chart_coords()
                    page.mouse.click(cx, cy, button="right")
                    time.sleep(2)

                    menu_found = False
                    try:
                        show_table = page.get_by_text("Mostrar como tabla", exact=False).first
                        if show_table.is_visible(timeout=2000):
                            show_table.click(force=True)
                            menu_found = True
                            time.sleep(4)
                    except Exception:
                        pass

                    if not menu_found:
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        print(f" → no menu ⚠️")
                        # NO deseleccionar
                        continue

                    table_rows = extract_table_data(page, timeout_s=10)
                    if table_rows:
                        for row in table_rows:
                            try:
                                all_data.append({
                                    "fecha_str": row["fecha_str"],
                                    "empleo": parse_valor(row["valor_str"]),
                                    "región": region,
                                })
                            except Exception:
                                pass
                        failed.remove(region)
                        print(f" → {len(table_rows)} filas ✅")
                    else:
                        print(f" → 0 filas ⚠️")

                    go_back_to_chart()
                    time.sleep(1)
                    # NO deseleccionar
                except Exception as e:
                    print(f" → Error: {e}")

            if failed:
                print(f"\n  ⚠️ Sin datos: {failed}")

        browser.close()

    # ═══════════════════════════════════════════════════════════
    #  Guardar resultados
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 60)

    if not all_data:
        print("❌ No se extrajeron datos. Revisa debug_*.png")
        return

    df = pd.DataFrame(all_data)

    meses_map = {
        "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12,
    }

    def parse_fecha(f):
        parts = f.split("-")
        if len(parts) == 2:
            mes_str, anio_str = parts
            return int(anio_str), meses_map.get(mes_str, 0), mes_str
        return None, None, f

    df[["año", "mes", "mes_nombre"]] = df["fecha_str"].apply(
        lambda x: pd.Series(parse_fecha(x))
    )
    df["actividad_económica"] = "Total"
    cols = ["año", "mes", "mes_nombre", "región", "actividad_económica", "empleo"]
    df = df[cols].sort_values(["región", "año", "mes"]).reset_index(drop=True)

    df.to_csv("empleo_formal_mtpe.csv", index=False, encoding="utf-8-sig")
    df.to_excel("empleo_formal_mtpe.xlsx", index=False)

    print(f"\n✅ {len(df)} filas guardadas:")
    print(f"   → empleo_formal_mtpe.csv")
    print(f"   → empleo_formal_mtpe.xlsx")
    print(f"\nRegiones: {sorted(df['región'].unique())}")
    print(f"Total regiones: {df['región'].nunique()}")
    print(f"Rango: {df['año'].min()}–{df['año'].max()}")
    print(f"\nMuestra:\n{df.head(10).to_string()}")
    print(f"\n…\n{df.tail(10).to_string()}")


if __name__ == "__main__":
    main()
