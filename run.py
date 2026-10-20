"""Jeden lub wiele przebiegów QA newslettera Domino's przez Camoufox bez okna."""

import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image
from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


DOMINOS_URL = "https://www.dominospizza.pl/AplikacjaMobilna"
MAIL_URL = "https://10minutemail.net/?lang=pl"
MAIL_EXTEND_URL = "https://10minutemail.net/more100.html"
CONFIRM_SUBJECTS = (
    "Potwierdzenie subskrypcji newslettera Domino's",
    "Request for subscription confirmation",
)
COUPON_SUBJECTS = (
    "Witaj w newsletterze Domino's!",
    "Welcome to Domino's newsletter!",
)
POLL_SECONDS = 15
MAIL_TIMEOUT_SECONDS = 15 * 60
ACTIVATION_TIMEOUT_MS = 60_000
NAVIGATION_TIMEOUT_MS = 60_000
CAPTCHA_INIT_TIMEOUT_MS = 30_000
LAB_DIR = Path(__file__).parent
LOGO_IMAGE = LAB_DIR / "logo-dominos.jpg"
CODE_LEDGER = LAB_DIR / "kody.csv"
CODE_COLUMNS = ("czas_utc", "email", "kod", "raport")
PROGRESS = {
    "SELECTORS_OK": (1, "Formularz i zgoda są gotowe"),
    "MAILBOX_READY": (2, "Skrzynka jest gotowa na wiadomości"),
    "CAPTCHA_READY": (3, "reCAPTCHA została załadowana"),
    "FORM_SENT": (4, "Domino’s potwierdziło zapis"),
    "FORM_UNCONFIRMED": (4, "Brak potwierdzenia zapisu; sprawdzam skrzynkę"),
    "MAIL_RECEIVED": (5, "Odebrano mail aktywacyjny"),
    "ACTIVATION_LINK_FOUND": (6, "Znaleziono link aktywacyjny"),
    "ACTIVATED": (7, "Newsletter został aktywowany"),
    "COUPON_RECEIVED": (8, "Odebrano kod rabatowy"),
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def configure_console():
    """Pokaż polskie znaki i włącz kolory ANSI, jeśli konsola je obsługuje."""
    if sys.platform == "win32":
        if sys.stdout.isatty():
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return False
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.argtypes = [ctypes.c_ulong]
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
        kernel.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        output = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if not kernel.GetConsoleMode(output, ctypes.byref(mode)):
            return False
        if not kernel.SetConsoleMode(output, mode.value | 0x0004):
            return False
    return True


def colorize(text, color, enabled):
    return f"\033[{color}m{text}\033[0m" if enabled else text


def print_logo(colors):
    """Rysuj załączone logo w CMD: dwa piksele obrazu na znak ▀."""
    if not colors:
        print("  Kolorowe logo: uruchom python run.py --preview w CMD")
        return
    width = min(60, shutil.get_terminal_size((80, 25)).columns - 2)
    if width < 20:
        print("  Poszerz okno CMD, aby wyświetlić logo.")
        return
    with Image.open(LOGO_IMAGE) as source:
        height = max(2, round(width * source.height / source.width / 2) * 2)
        pixels = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS).load()
        for y in range(0, height, 2):
            line = []
            for x in range(width):
                top = pixels[x, y]
                bottom = pixels[x, y + 1]
                line.append(
                    f"\033[38;2;{top[0]};{top[1]};{top[2]}m"
                    f"\033[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m▀"
                )
            print("".join(line) + "\033[0m")


def print_banner(colors=False):
    """Logo odtworzone z JPG i tytuł laboratorium."""
    title = (
        "    ____  ____  __  ________   ______ _ _____",
        "   / __ \\/ __ \\/  |/  /  _/ | / / __ ( ) ___/",
        "  / / / / / / / /|_/ // //  |/ / / / //\\__ \\ ",
        " / /_/ / /_/ / /  / // // /|  / /_/ / ___/ /",
        "/_____/\\____/_/  /_/___/_/ |_/\\____/ /____/",
    )
    print()
    print_logo(colors)
    for line in title:
        print(colorize(line, "1;97", colors))
    print("  " + colorize("━━ SOURCE", "1;94", colors) + colorize(" • LAB ━━", "1;91", colors))
    print("  " + colorize("Newsletter QA  |  Camoufox", "2;37", colors))
    print()


def append_coupon(run_dir, email, coupon, received_at):
    """Dopisz udany przebieg do jednego pliku, bez duplikowania raportu."""
    report_ref = f"runs/{run_dir.name}/result.json"
    if CODE_LEDGER.exists():
        with CODE_LEDGER.open("r", encoding="utf-8-sig", newline="") as handle:
            if any(row.get("raport") == report_ref for row in csv.DictReader(handle, delimiter=";")):
                return False
    new_file = not CODE_LEDGER.exists() or CODE_LEDGER.stat().st_size == 0
    with CODE_LEDGER.open("a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CODE_COLUMNS, delimiter=";")
        if new_file:
            writer.writeheader()
        writer.writerow({"czas_utc": received_at, "email": email, "kod": coupon, "raport": report_ref})
    return True


def backfill_coupons():
    """Odtwórz centralny plik z udanych przebiegów zapisanych przed tą zmianą."""
    if not (LAB_DIR / "runs").exists():
        return
    for result_path in sorted((LAB_DIR / "runs").glob("*/result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "COUPON_RECEIVED" or not result.get("coupon"):
            continue
        received_at = next(
            (stage["at"] for stage in result.get("stages", []) if stage["status"] == "COUPON_RECEIVED"),
            result.get("finished_at", ""),
        )
        append_coupon(result_path.parent, result["email"], result["coupon"], received_at)


def allowed_host(url, hosts):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in hosts:
        raise RuntimeError(f"Nieoczekiwana domena linku: {parsed.hostname}")


def read_address(mail_page):
    address = mail_page.locator("#fe_text").input_value().strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address):
        raise RuntimeError("10 Minute Mail nie udostępnił poprawnego adresu e-mail.")
    return address


def dismiss_cookie_banner(page):
    """Poczekaj na opóźniony baner OneTrust i wybierz tylko niezbędne cookies."""
    reject = page.locator("#onetrust-reject-all-handler")
    try:
        reject.wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeoutError:
        return
    reject.click()
    page.locator(".onetrust-pc-dark-filter").wait_for(state="hidden", timeout=10_000)


def wait_for_mail(mail_page, subject, description):
    subjects = (subject,) if isinstance(subject, str) else tuple(subject)
    subject_pattern = re.compile("|".join(re.escape(item) for item in subjects), re.IGNORECASE)
    deadline = time.monotonic() + MAIL_TIMEOUT_SECONDS
    started = time.monotonic()
    next_update = started + 60
    print(f"      Czekam na {description} (maksymalnie 15 minut)...", flush=True)
    while time.monotonic() < deadline:
        mail_page.goto(MAIL_URL, wait_until="domcontentloaded")
        row = mail_page.locator("#maillist tr").filter(has_text=subject_pattern)
        if row.count():
            row = row.first
            sender = row.locator("td").first.inner_text().strip()
            sender_name = next((line.strip() for line in sender.splitlines() if line.strip()), "")
            if "dominos" not in sender_name.casefold():
                raise RuntimeError(f"Temat pasuje, ale nazwa nadawcy nie zawiera „dominos”: {sender_name}")
            href = row.locator('a[href*="readmail.html"]').first.get_attribute("href")
            if not href:
                raise RuntimeError("Brak linku do wiadomości.")
            message_url = urljoin(MAIL_URL, href)
            allowed_host(message_url, {"10minutemail.net"})
            mail_page.goto(message_url, wait_until="domcontentloaded")
            mail_page.get_by_role("heading", name=subject_pattern).wait_for()
            return sender
        if time.monotonic() >= next_update:
            elapsed = int((time.monotonic() - started) // 60)
            print(f"      Nadal czekam na {description}: {elapsed}/15 min", flush=True)
            next_update += 60
        time.sleep(POLL_SECONDS)
    expected = " / ".join(f"„{item}”" for item in subjects)
    raise RuntimeError(f"MAIL_TIMEOUT: nie dotarła wiadomość {expected} w ciągu 15 minut.")


def run_single_generation(colors=False, check_mode=False):
    """Wykonuje pojedynczą próbę rejestracji i odbioru kuponu."""
    run_dir = LAB_DIR / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "mode": "check" if check_mode else "live",
        "started_at": now_iso(),
        "status": "STARTED",
        "stages": [],
    }

    def save():
        (run_dir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def stage(status, **details):
        report["status"] = status
        report["stages"].append({"status": status, "at": now_iso(), **details})
        save()
        number, label = PROGRESS[status]
        step = colorize(f"[{number}/8]", "1;96", colors)
        print(f"{step} {datetime.now().strftime('%H:%M:%S')}  {label}", flush=True)

    save()
    if not check_mode:
        backfill_coupons()

    with Camoufox(headless=True, humanize=True, os="windows", locale="pl-PL") as browser:
        context = browser.new_context()
        mail_page = context.new_page()
        dominos_page = context.new_page()
        mail_page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
        dominos_page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
        current_page = dominos_page
        try:
            mail_page.goto(MAIL_URL, wait_until="domcontentloaded")
            address = read_address(mail_page)
            report["email"] = address
            print(f"Adres testowy: {address}", flush=True)
            dominos_page.goto(DOMINOS_URL, wait_until="domcontentloaded")
            dismiss_cookie_banner(dominos_page)

            email_field = dominos_page.locator("#Email")
            consent = dominos_page.locator("#Consents-2")
            consent_label = dominos_page.locator('label[for="Consents-2"]')
            submit = dominos_page.get_by_role("button", name=re.compile(r"odbierz rabat", re.I))
            counts = (email_field.count(), consent.count(), consent_label.count(), submit.count())
            if counts != (1, 1, 1, 1):
                raise RuntimeError(f"Formularz Domino’s zmienił się: liczby dopasowań email/zgoda/etykieta/przycisk = {counts}.")
            if mail_page.locator("#maillist").count() != 1:
                raise RuntimeError("Nie znaleziono tabeli skrzynki 10 Minute Mail.")
            
            consent_label.click()
            if not consent.is_checked():
                raise RuntimeError("Nie udało się zaznaczyć zgody marketingowej.")
            stage("SELECTORS_OK")

            if check_mode:
                print("Tryb kontrolny: formularz nie został wysłany.", flush=True)
                return True, None

            current_page = mail_page
            mail_page.goto(MAIL_EXTEND_URL, wait_until="domcontentloaded")
            if read_address(mail_page) != address:
                raise RuntimeError("Adres skrzynki zmienił się podczas przedłużania ważności.")
            stage("MAILBOX_READY")

            current_page = dominos_page
            email_field.fill(address)
            captcha_frame = dominos_page.locator('[data-newsletter-captcha] iframe[src*="recaptcha"]')
            try:
                captcha_frame.wait_for(state="attached", timeout=CAPTCHA_INIT_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                email_field.blur()
                email_field.focus()
                captcha_frame.wait_for(state="attached", timeout=CAPTCHA_INIT_TIMEOUT_MS)
            stage("CAPTCHA_READY")
            form_responses = []
            page_errors = []

            def capture_response(response):
                parsed = urlparse(response.url)
                method = response.request.method
                if parsed.hostname and parsed.hostname.endswith("dominospizza.pl") and method != "GET":
                    form_responses.append({"method": method, "path": parsed.path, "status": response.status})

            dominos_page.on("response", capture_response)
            dominos_page.on("pageerror", lambda error: page_errors.append(str(error)[:300]))
            
            submit.click()
            form_confirmed = False
            try:
                dominos_page.get_by_text(
                    "Na podany adres wysłaliśmy link aktywacyjny.", exact=False
                ).wait_for(state="visible", timeout=ACTIVATION_TIMEOUT_MS)
                form_confirmed = True
            except PlaywrightTimeoutError:
                report["form_diagnostics"] = {
                    "email_valid": email_field.evaluate("element => element.checkValidity()"),
                    "consent_checked": consent.is_checked(),
                    "validation_errors": [
                        text.strip() for text in dominos_page.locator('[data-js="error"]').all_text_contents()
                        if text.strip()
                    ],
                    "recaptcha_present": dominos_page.locator('iframe[src*="recaptcha"]').count() > 0,
                    "recaptcha_challenge_present": dominos_page.locator('iframe[src*="recaptcha/api2/bframe"]').count() > 0,
                    "recaptcha_response_length": len(dominos_page.locator('#g-recaptcha-response').input_value()) if dominos_page.locator('#g-recaptcha-response').count() else 0,
                    "captcha_field_length": len(dominos_page.locator('input[name="Captcha"]').input_value()),
                    "form_response": dominos_page.locator('[data-formnewsletter-response]').inner_text().strip(),
                    "form_responses": form_responses[-10:],
                    "page_errors": page_errors[-10:],
                }
                save()
            dominos_page.screenshot(path=str(run_dir / "01-formularz.png"))
            stage("FORM_SENT" if form_confirmed else "FORM_UNCONFIRMED")

            current_page = mail_page
            confirmation_sender = wait_for_mail(mail_page, CONFIRM_SUBJECTS, "mail aktywacyjny")
            mail_page.screenshot(path=str(run_dir / "02-mail-aktywacyjny.png"))
            stage("MAIL_RECEIVED", sender=confirmation_sender)

            activation_href = (
                mail_page.locator("#tab1 a")
                .filter(has_text=re.compile(r"Aktywuj subskrypcję|Activate(?: your)? subscription", re.I))
                .first.get_attribute("href")
            )
            if not activation_href:
                raise RuntimeError("Mail nie zawiera linku aktywacyjnego.")
            allowed_host(activation_href, {"tracking.dominospizza.pl", "www.dominospizza.pl"})
            stage("ACTIVATION_LINK_FOUND", link_host=urlparse(activation_href).hostname)

            activation_page = context.new_page()
            activation_page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
            current_page = activation_page
            activation_page.goto(activation_href, wait_until="domcontentloaded")
            allowed_host(activation_page.url, {"www.dominospizza.pl"})
            activation_page.get_by_text(
                re.compile(r"Twój e-mail został aktywowany|Your email has been activated", re.I)
            ).wait_for(state="visible", timeout=ACTIVATION_TIMEOUT_MS)
            activation_page.screenshot(path=str(run_dir / "03-aktywacja.png"))
            stage("ACTIVATED", path=urlparse(activation_page.url).path)

            current_page = mail_page
            coupon_sender = wait_for_mail(mail_page, COUPON_SUBJECTS, "mail z kodem")
            body = mail_page.locator("#tab1")
            if not re.search(
                r"Twój unikalny, jednorazowy kod na zniżkę 50%|"
                r"your unique, one-time code for a 50% discount",
                body.inner_text(),
                re.I,
            ):
                raise RuntimeError("Drugi mail nie zawiera oczekiwanego opisu kuponu.")
            candidates = {
                text.strip() for text in body.locator("p").all_text_contents()
                if re.fullmatch(r"[A-Z0-9]{6,12}", text.strip())
            }
            if len(candidates) != 1:
                raise RuntimeError(f"Nie udało się jednoznacznie odczytać kodu: {len(candidates)} kandydatów.")
            coupon = next(iter(candidates))
            report["coupon"] = coupon
            mail_page.screenshot(path=str(run_dir / "04-kupon.png"), full_page=True)
            append_coupon(run_dir, address, coupon, now_iso())
            stage("COUPON_RECEIVED", sender=coupon_sender)
            print(f"\n{colorize('SUKCES!', '1;92', colors)} Kod 50%: {coupon}", flush=True)
            print(f"Wszystkie kody: {CODE_LEDGER}", flush=True)
            return True, coupon
        except Exception as exc:
            report["status"] = "FAILED"
            report["error"] = str(exc)
            save()
            try:
                current_page.screenshot(path=str(run_dir / "blad.png"), full_page=True)
            except Exception:
                pass
            print(f"{colorize('Błąd:', '1;91', colors)} {exc}", file=sys.stderr, flush=True)
            return False, None
        finally:
            report["finished_at"] = now_iso()
            save()
            print(f"Raport: {run_dir / 'result.json'}", flush=True)


def main(colors=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Pokaż kolorowy baner bez uruchamiania testu.")
    parser.add_argument("--check", action="store_true", help="Sprawdź selektory, bez zapisu.")
    parser.add_argument("--live", action="store_true", help="Wykonaj rzeczywisty zapis.")
    parser.add_argument("--count", type=int, default=1, help="Liczba kodów do wygenerowania w trybie --live (domyślnie: 1).")
    args = parser.parse_args()

    if args.preview:
        print_banner(colors)
        print("Podgląd banera — test newslettera nie został uruchomiony.")
        return 0

    if not args.check and not args.live:
        parser.error("Musisz podać jeden z argumentów: --preview, --check lub --live")

    print_banner(colors)
    print("Przeglądarka działa bez widocznego okna.\n", flush=True)

    if args.check:
        success, _ = run_single_generation(colors=colors, check_mode=True)
        return 0 if success else 1

    if args.live:
        target_count = args.count
        generated_codes = []

        for i in range(1, target_count + 1):
            print(f"\n{colorize(f'=== Generowanie kodu {i} z {target_count} ===', '1;95', colors)}")
            success, code = run_single_generation(colors=colors, check_mode=False)
            if success and code:
                generated_codes.append(code)
                print(f"Pomyślnie wygenerowano kod #{i}: {code}")
            else:
                print(f"Nie udało się wygenerować kodu #{i}.")

            if i < target_count:
                print("Czekam 10 sekund przed kolejną próbą...")
                time.sleep(10)

        print(f"\n{colorize('Zakończono!', '1;92', colors)} Wygenerowane kody ({len(generated_codes)}/{target_count}):")
        for code in generated_codes:
            print(f" - {code}")
        print(f"Wszystkie kody zapisane w: {CODE_LEDGER}")

        return 0 if len(generated_codes) == target_count else 1


if __name__ == "__main__":
    raise SystemExit(main(configure_console()))
