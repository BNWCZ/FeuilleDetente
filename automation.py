from playwright.sync_api import sync_playwright, Page, Frame

AVANT_VENTE_ROW = 23
DEBUG_DIR = "debug"


def _esc(ps_id: str) -> str:
    return ps_id.replace("$", "\\$")


def _wait_stable(page: Page):
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(300)


def _screenshot(page: Page, name: str):
    import os
    os.makedirs(DEBUG_DIR, exist_ok=True)
    page.screenshot(path=f"{DEBUG_DIR}/{name}.png", full_page=True)


def _get_iframe(page: Page) -> Frame:
    page.wait_for_selector("#main_target_win0", state="attached", timeout=10000)
    el = page.query_selector("#main_target_win0")
    frame = el.content_frame()
    if not frame:
        raise RuntimeError("Impossible d'accéder à l'iframe principal")
    return frame


def _find_in_page_or_frames(page: Page, selector: str, timeout: int = 10000):
    import time
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        if page.locator(selector).count() > 0:
            return page
        for frame in page.frames:
            if frame.locator(selector).count() > 0:
                return frame
        page.wait_for_timeout(300)
    raise RuntimeError(f"Element introuvable: {selector}")


def run_automation(*, uid: str, password: str, login_url: str, week: dict, work_days: list[dict], headless: bool):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=50)
        page = browser.new_page()
        page.set_default_timeout(15000)

        try:
            _do_automation(page, uid=uid, password=password, login_url=login_url, week=week, work_days=work_days)
        except Exception as e:
            _screenshot(page, "error")
            print(f"  Erreur: {e}")
            print(f"  Screenshots dans {DEBUG_DIR}/")
            raise
        finally:
            if headless:
                browser.close()
            else:
                print(f"\n  Screenshots de debug dans {DEBUG_DIR}/")
                print("  Navigateur ouvert pour inspection. Ctrl+C pour quitter.")
                try:
                    import time
                    while True:
                        time.sleep(60)
                except KeyboardInterrupt:
                    browser.close()


def _do_automation(page: Page, *, uid: str, password: str, login_url: str, week: dict, work_days: list[dict]):
    # === Login ===
    print("  [1/7] Connexion...")
    page.goto(login_url, wait_until="domcontentloaded")
    page.fill("#userid", uid)
    page.fill("#pwd", password)
    page.locator(".ps_box-button").first.click()
    _wait_stable(page)
    _screenshot(page, "01-login")

    # === Click "Mes Déclarations heures" tile ===
    print("  [2/7] Navigation vers les déclarations...")
    tile = f"#{_esc('win0groupletPTNUI_LAND_REC_GROUPLET$0')}"
    ctx = _find_in_page_or_frames(page, tile)
    ctx.locator(tile).click()
    _wait_stable(page)
    _screenshot(page, "02-declarations")

    # === Create or open existing timesheet ===
    print("  [3/7] Création feuille des temps...")
    date_sel = f"#{_esc('EX_TIME_ADD_VW_PERIOD_END_DT')}"
    form_ctx = _find_in_page_or_frames(page, date_sel)
    form_ctx.locator(date_sel).fill(week["saturday_str"])
    form_ctx.locator(f"#{_esc('PTS_CFG_CL_WRK_PTS_ADD_BTN')}").click()
    _wait_stable(page)

    open_sel = f"#{_esc('EX_ICLIENT_WRK_OK_PB')}"
    ok_btn = '#\\#ICOK'
    found_ctx = _find_in_page_or_frames(page, f"{open_sel}, {ok_btn}")

    if found_ctx.locator(ok_btn).count() > 0:
        print("    Feuille existante detectee, ouverture...")
        found_ctx.locator(ok_btn).click()
        _wait_stable(page)
        existing_sel = f"#{_esc('EX_TIME_ADD_VW_PERIOD_END_DT$0')}"
        ex_ctx = _find_in_page_or_frames(page, existing_sel)
        ex_ctx.locator(existing_sel).click()
        _wait_stable(page)
    else:
        found_ctx.locator(open_sel).click()
        _wait_stable(page)

    _screenshot(page, "03-timesheet")

    # === Fill Avant-vente hours via JS (like the bookmarklet) ===
    print("  [4/7] Saisie des heures Avant-vente...")
    frame = _get_iframe(page)
    frame.wait_for_selector(f"#{_esc(f'POL_DESCR${AVANT_VENTE_ROW}')}", timeout=10000)

    day_data = _serialize_days(work_days)
    result = frame.evaluate("""(args) => {
        const { days, row } = args;
        const filled = [];
        for (const day of days) {
            if (!day.is_work_day) continue;
            const id = `POL_TIME${day.time_field_index}$${row}`;
            const el = document.getElementById(id);
            if (!el) return { error: `Champ introuvable: ${id}` };
            el.value = String(day.hours);
            el.dispatchEvent(new Event('change', { bubbles: true }));
            filled.push(id);
        }
        return { filled };
    }""", {"days": day_data, "row": AVANT_VENTE_ROW})

    if "error" in result:
        raise RuntimeError(result["error"])
    print(f"    Champs remplis: {result['filled']}")
    _screenshot(page, "04-hours")

    # === Open additional info (opens as PeopleSoft modal) ===
    print("  [5/7] Informations additionnelles...")
    frame.click("#UC_EX_WRK_UC_TI_FRA_LINK")
    _wait_stable(page)

    modal_frame = _find_modal_frame(page)
    _screenshot(page, "05-addinfo-open")

    _fill_additional_info(modal_frame, day_data)
    _screenshot(page, "06-addinfo-filled")

    # === Save additional info (OK button in modal) ===
    print("  [6/7] Sauvegarde infos additionnelles...")
    modal_frame.click("#\\#ICSave")
    _wait_stable(page)
    _screenshot(page, "07-addinfo-saved")

    # === Save draft ===
    print("  [7/7] Enregistrement brouillon...")
    frame = _get_iframe(page)
    frame.click(f"#{_esc('EX_ICLIENT_WRK_SAVE_PB')}")
    _wait_stable(page)
    _screenshot(page, "08-draft-saved")

    print("  Termine !")


def _find_modal_frame(page: Page) -> Frame:
    """Find the PeopleSoft modal frame containing the additional info form."""
    page.wait_for_timeout(1000)
    for frame in page.frames:
        try:
            found = frame.evaluate("""() => {
                return !!document.querySelector('[id*="UC_EX_TDLY_FR"]')
                    || !!document.querySelector('td:has(> select)');
            }""")
            if found:
                return frame
        except Exception:
            continue
    raise RuntimeError("Frame de la modale infos additionnelles introuvable")


def _serialize_days(work_days: list[dict]) -> list[dict]:
    return [
        {
            "index": d["index"],
            "time_field_index": d["time_field_index"],
            "is_work_day": d["is_work_day"],
            "is_weekend": d["is_weekend"],
            "is_tt": d["is_tt"],
            "hours": d["hours"],
        }
        for d in work_days
    ]


def _fill_additional_info(frame: Frame, day_data: list[dict]):
    result = frame.evaluate("""(days) => {
        const filled = [];
        const missing = [];

        function set(ti, value) {
            const el = document.querySelector(`[tabindex="${ti}"]`);
            if (el) {
                el.value = value;
                el.dispatchEvent(new Event('change', { bubbles: true }));
                filled.push(ti);
            } else {
                missing.push(ti);
            }
        }

        // --- Repos quotidien ---
        // Rows 1-3 (selects): tabindex 31-37, 40-46, 49-55
        for (const start of [31, 40, 49]) {
            for (const day of days) {
                set(start + day.index, day.is_work_day ? 'Y' : 'NA');
            }
        }
        // Row 4 (pause déjeuner, inputs): tabindex 216-220 (Lu-Ve)
        for (const day of days) {
            if (day.is_weekend) continue;
            set(216 + (day.index - 1), day.is_work_day ? '1' : '');
        }

        // --- Localisation ---
        // Matin:      tabindex 372 + index (Di=0..Sam=6)
        // Après-midi: tabindex 381 + index (Di=0..Sam=6)
        for (const start of [372, 381]) {
            for (const day of days) {
                let value;
                if (!day.is_work_day) value = 'N/A';
                else if (day.is_tt) value = 'T';
                else value = 'O';
                set(start + day.index, value);
            }
        }

        return { filled: filled.length, missing };
    }""", day_data)
    print(f"    Infos additionnelles: {result['filled']} champs remplis, manquants: {result['missing']}")
