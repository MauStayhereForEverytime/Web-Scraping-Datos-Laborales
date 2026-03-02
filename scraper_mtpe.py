#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Scraper MTPE - Empleo Formal (Planilla Electronica)
Estrategia:
  1. Abrir reporte Power BI -> pestania EVOLUCION
  2. Seleccionar UN departamento (ej: Loreto)
  3. Seleccionar TODOS los anios (clic en cada <rect> del timeline)
  4. Right-click grafico -> "Mostrar como tabla"
  5. Extraer datos de la tabla DOM (scroll con PageDown)
  6. Guardar CSV + XLSX (con numeracion incremental si ya existen)
"""

import time, re, os
import pandas as pd
from playwright.sync_api import sync_playwright

URL_PAGINA = (
    "https://www2.trabajo.gob.pe/estadisticas/observatorio-de-la-formalizacion-laboral/"
    "tableros-interactivos/tablero-interactivo-del-empleo-informal-observatorio-iii/"
)

# -- Configuracion --
DEPARTAMENTOS = ["Loreto"]
ANIOS = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]

BASE_DIR = r"D:\1.WORKS AND CLASES\7. Encargos pendejos"
BASE_NAME = "empleo_formal_mtpe"


def next_filename(base_dir, base_name, ext):
    """
    Retorna el siguiente nombre disponible:
      empleo_formal_mtpe.csv  (si no existe)
      empleo_formal_mtpe(1).csv  (si ya existe)
      empleo_formal_mtpe(2).csv  ...
    """
    path = os.path.join(base_dir, f"{base_name}.{ext}")
    if not os.path.exists(path):
        return path
    i = 1
    while True:
        path = os.path.join(base_dir, f"{base_name}({i}).{ext}")
        if not os.path.exists(path):
            return path
        i += 1


def parse_valor(val_str):
    """Convierte '36.641' o '3.770.677' a int (punto = miles)."""
    return int(val_str.strip().replace(".", ""))


def select_all_years(page):
    """
    Selecciona todos los anios en el slicer timeline de Power BI.
    El slicer esta en iframes sandbox. Cada anio es un <rect class="cellRect">
    con <title>Año 2016</title> adentro. Click con Ctrl para multi-select.
    """
    clicked = []
    for anio in ANIOS:
        target_text = f"Año {anio}"
        found = False
        for frame in page.frames:
            try:
                title_loc = frame.locator(f"title:has-text('{target_text}')")
                if title_loc.count() > 0:
                    parent_rect = title_loc.first.locator("xpath=..")
                    # Primer anio: clic normal. Siguientes: Ctrl+clic para agregar.
                    if len(clicked) == 0:
                        parent_rect.click(force=True)
                    else:
                        parent_rect.click(force=True, modifiers=["Control"])
                    clicked.append(anio)
                    found = True
                    break
            except Exception:
                continue
        if not found:
            for frame in page.frames:
                try:
                    el = frame.get_by_text(target_text, exact=True).first
                    if el.is_visible(timeout=1000):
                        if len(clicked) == 0:
                            el.click(force=True)
                        else:
                            el.click(force=True, modifiers=["Control"])
                        clicked.append(anio)
                        found = True
                        break
                except Exception:
                    continue
        status = "OK" if found else "MISS"
        print(f"    {anio}: {status}")
        time.sleep(0.5)

    print(f"  Anios seleccionados: {len(clicked)}/{len(ANIOS)}")
    return clicked


def extract_table_data(page):
    """
    Despues de 'Mostrar como tabla', extrae filas con scroll.
    Retorna lista de dicts {grupo, fecha_str, valor_str}.
    """
    time.sleep(4)

    ROW_RE = re.compile(
        r"(\d{4})[\s\n,]+((?:Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)-\d{4})"
        r"[\s\n,]+(\d{1,3}(?:\.\d{3})+)",
        re.IGNORECASE,
    )

    all_found = {}

    def _extract():
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

    _extract()
    prev_count = len(all_found)
    print(f"    Visible inicial: {prev_count} filas")

    # Enfocar la tabla: buscar una celda con fecha y hacer clic
    try:
        date_cell = page.get_by_text(re.compile(r"Ene-\d{4}"), exact=False).first
        date_cell.click(force=True)
        time.sleep(0.5)
    except Exception:
        pass

    # === SCROLL ARRASTRANDO EL SCROLLBAR VERTICAL DE LA TABLA ===
    # Power BI usa scrollbar custom: div.scroll-bar-part-bar dentro de
    # un contenedor vertical. El scrollbar horizontal del grafico esta
    # en otra posicion. Necesitamos encontrar el scrollbar VERTICAL
    # de la tabla y arrastrarlo hacia abajo.

    # Buscar el scrollbar vertical de la tabla
    # Los scrollbars de Power BI tienen la clase "scroll-bar-part-bar"
    # El vertical tiene width ~9px y se mueve en Y (translateY)
    scrollbar = None
    scrollbar_container = None
    try:
        bars = page.locator(".scroll-bar-part-bar").all()
        print(f"    Scrollbars encontrados: {len(bars)}")
        for i, bar in enumerate(bars):
            bb = bar.bounding_box(timeout=2000)
            if bb:
                print(f"      Bar {i}: {int(bb['width'])}x{int(bb['height'])} en ({int(bb['x'])},{int(bb['y'])})")
                # El scrollbar vertical es angosto (width ~9px) y alto
                # El horizontal es ancho y bajo (height ~9px)
                if bb["width"] < 20 and bb["height"] > 20:
                    scrollbar = bar
                    scrollbar_container = bb
                    print(f"      -> Scrollbar VERTICAL encontrado (bar {i})")
    except Exception as e:
        print(f"    WARN buscando scrollbar: {e}")

    if scrollbar and scrollbar_container:
        # Arrastrar el scrollbar hacia abajo en pasos
        sb = scrollbar_container
        drag_x = sb["x"] + sb["width"] / 2
        start_y = sb["y"] + sb["height"] / 2
        # Calcular cuanto espacio hay para arrastrar
        # El contenedor del scrollbar es el padre
        try:
            parent = scrollbar.locator("xpath=..").first
            parent_bb = parent.bounding_box(timeout=2000)
            if parent_bb:
                max_y = parent_bb["y"] + parent_bb["height"] - sb["height"] / 2
                total_drag = max_y - start_y
                print(f"    Arrastrando scrollbar: {int(total_drag)}px de recorrido")
            else:
                total_drag = 500
        except Exception:
            total_drag = 500

        # Arrastrar en pasos, extrayendo datos entre cada paso
        steps = 20
        step_size = total_drag / steps

        for step in range(steps):
            current_y = start_y + step_size * step
            next_y = start_y + step_size * (step + 1)

            try:
                page.mouse.move(drag_x, current_y)
                page.mouse.down()
                page.mouse.move(drag_x, next_y, steps=5)
                page.mouse.up()
                time.sleep(0.8)
                _extract()
                new_count = len(all_found)
                if step % 5 == 0:
                    print(f"    ... paso {step}/{steps}: {new_count} filas")
            except Exception:
                break

    else:
        # Fallback: intentar wheel sobre una celda de la tabla (no el grafico)
        # Buscar el contenedor de datos de la tabla por su role="grid" o similar
        print("    No encontre scrollbar vertical, intentando wheel sobre gridcells...")
        try:
            # Buscar celdas con role="gridcell" que contengan datos de la tabla
            gridcells = page.locator("[role='gridcell']")
            if gridcells.count() > 0:
                cell_bb = gridcells.first.bounding_box(timeout=3000)
                if cell_bb:
                    wx = cell_bb["x"] + cell_bb["width"] / 2
                    wy = cell_bb["y"] + cell_bb["height"] / 2
                    print(f"    Wheel sobre gridcell en ({int(wx)}, {int(wy)})")
                    stale = 0
                    for rnd in range(100):
                        page.mouse.move(wx, wy)
                        page.mouse.wheel(0, 200)
                        time.sleep(0.4)
                        _extract()
                        nc = len(all_found)
                        if nc == prev_count:
                            stale += 1
                            if stale >= 8:
                                break
                        else:
                            stale = 0
                            prev_count = nc
        except Exception as e:
            print(f"    WARN fallback wheel: {e}")

    print(f"    Total extraido: {len(all_found)} filas")
    return sorted(all_found.values(), key=lambda r: r["fecha_str"])


def find_chart_coords(page):
    """Recalcula coordenadas del centro del grafico."""
    try:
        title = page.get_by_text(re.compile(r"N.MERO DE TRABAJADORES", re.IGNORECASE)).first
        bb = title.bounding_box(timeout=5000)
        if bb:
            return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] + 150
    except Exception:
        pass
    try:
        containers = page.locator(".visual-container").all()
        for c in containers:
            bb = c.bounding_box(timeout=2000)
            if bb and bb["height"] > 200 and bb["width"] > 400:
                return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    except Exception:
        pass
    return 960, 800


def click_mostrar_como_tabla(page):
    """Right-click en el grafico y selecciona 'Mostrar como tabla'."""
    cx, cy = find_chart_coords(page)
    print(f"    Right-click en ({int(cx)}, {int(cy)})...")
    page.mouse.click(cx, cy, button="right")
    time.sleep(2)

    page.screenshot(path="debug_context_menu.png")

    for label in ["Mostrar como tabla", "Show as table"]:
        try:
            btn = page.get_by_text(label, exact=False).first
            if btn.is_visible(timeout=2000):
                btn.click(force=True)
                print(f"    '{label}' clickeado OK")
                time.sleep(4)
                return True
        except Exception:
            continue

    page.keyboard.press("Escape")
    time.sleep(0.5)
    print("    WARN: No encontre opcion de tabla en el menu contextual")
    return False


def main():
    print("=" * 60)
    print("  Scraper MTPE - Empleo Formal")
    print("  Estrategia: seleccionar todos los anios + mostrar tabla")
    print("=" * 60)

    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1920, "height": 3000})
        page = ctx.new_page()

        # --- PASO 1: Obtener iframe Power BI ---
        print("\n[1] Buscando iframe Power BI...")
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
            print("ERROR: No encontre iframe Power BI.")
            browser.close()
            return
        print(f"  OK: {embed_url[:80]}...")

        # --- PASO 2: Cargar reporte ---
        print("\n[2] Cargando reporte Power BI...")
        page.goto(embed_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(10)
        print("  OK: Reporte cargado")

        # --- PASO 3: Ir a EVOLUCION ---
        print("\n[3] Navegando a pestania EVOLUCION...")
        try:
            btn = page.get_by_text(re.compile(r"EVOLUCI", re.IGNORECASE)).first
            btn.click(force=True)
            print("  OK")
        except Exception as e:
            print(f"  WARN: {e}")
        time.sleep(10)
        page.screenshot(path="debug_01_evolucion.png")

        # Debug: listar frames
        print(f"\n  Frames disponibles: {len(page.frames)}")
        for i, frame in enumerate(page.frames):
            try:
                rects = frame.locator("rect.cellRect").count()
                if rects > 0:
                    print(f"    Frame {i}: {rects} cellRects (timeline slicer)")
            except Exception:
                pass

        # --- PASO 4: Para cada departamento ---
        for depto in DEPARTAMENTOS:
            print(f"\n{'='*60}")
            print(f"  DEPARTAMENTO: {depto}")
            print(f"{'='*60}")

            # Seleccionar departamento
            try:
                loc_depto = page.get_by_text(depto, exact=True).first
                loc_depto.scroll_into_view_if_needed(timeout=5000)
                time.sleep(0.5)
                loc_depto.click(force=True)
                time.sleep(4)
                print(f"  OK: '{depto}' seleccionado")
            except Exception as e:
                print(f"  ERROR: No pude seleccionar '{depto}': {e}")
                continue

            page.screenshot(path=f"debug_depto_{depto}.png")

            # Seleccionar TODOS los anios
            print("\n  Seleccionando todos los anios...")
            clicked_years = select_all_years(page)

            if not clicked_years:
                print("  ERROR: No se pudo seleccionar ningun anio")
                continue

            # Devolver foco al frame principal
            page.mouse.click(10, 10)
            time.sleep(2)

            # Esperar a que el grafico se actualice con todos los anios
            time.sleep(5)
            page.screenshot(path=f"debug_{depto}_all_years.png")

            # Mostrar como tabla
            print("\n  Abriendo tabla...")
            if not click_mostrar_como_tabla(page):
                page.screenshot(path=f"debug_{depto}_no_menu.png")
                print("  No se pudo abrir tabla, saltando departamento")
                continue

            page.screenshot(path=f"debug_{depto}_tabla.png")

            # Extraer datos
            print("\n  Extrayendo datos de la tabla...")
            rows = extract_table_data(page)

            if rows:
                for row in rows:
                    try:
                        all_data.append({
                            "fecha_str": row["fecha_str"],
                            "empleo": parse_valor(row["valor_str"]),
                            "region": depto,
                        })
                    except Exception:
                        pass
                print(f"\n  RESULTADO: {len(rows)} filas extraidas para {depto}")
            else:
                print(f"\n  WARN: 0 filas para {depto}")

            # Escape para cerrar cualquier overlay
            page.keyboard.press("Escape")
            time.sleep(1)

        browser.close()

    # ═════════════════════════════════════════════════════════
    #  Guardar resultados con numeracion incremental
    # ═════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  GUARDANDO RESULTADOS")
    print("=" * 60)

    if not all_data:
        print("ERROR: No se extrajeron datos. Revisa debug_*.png")
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

    df[["anio", "mes", "mes_nombre"]] = df["fecha_str"].apply(
        lambda x: pd.Series(parse_fecha(x))
    )
    df["actividad_economica"] = "Total"
    cols = ["anio", "mes", "mes_nombre", "region", "actividad_economica", "empleo"]
    df = df[cols].sort_values(["region", "anio", "mes"]).reset_index(drop=True)

    # Archivos con numeracion incremental
    csv_path = next_filename(BASE_DIR, BASE_NAME, "csv")
    xlsx_path = next_filename(BASE_DIR, BASE_NAME, "xlsx")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    print(f"\n  {len(df)} filas guardadas:")
    print(f"    -> {csv_path}")
    print(f"    -> {xlsx_path}")
    print(f"\n  Regiones: {sorted(df['region'].unique())}")
    print(f"  Rango anios: {df['anio'].min()}-{df['anio'].max()}")
    print(f"\n  Muestra (primeras 10):")
    print(df.head(10).to_string(index=False))
    print(f"\n  Muestra (ultimas 10):")
    print(df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
