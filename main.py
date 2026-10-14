import argparse
import sys
from datetime import datetime
from pathlib import Path

from week import get_current_week
from automation import run_automation


def load_env() -> dict[str, str]:
    env_path = Path(__file__).parent / ".env"
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Separateur = le premier ':' ou '=' rencontre (une valeur URL peut
        # contenir les deux, ex. https://...?cmd=login).
        positions = [line.find(c) for c in (":", "=") if c in line]
        if positions:
            idx = min(positions)
            env[line[:idx].strip()] = line[idx + 1:].strip()
    return env


def build_work_days(week: dict, tt: list[str], conges: list[str]) -> list[dict]:
    result = []
    for day in week["days"]:
        is_conge = day["name"] in conges
        is_tt = day["name"] in tt
        is_work_day = not day["is_weekend"] and not day["is_holiday"] and not is_conge

        result.append({
            **day,
            "is_conge": is_conge,
            "is_tt": is_tt,
            "is_work_day": is_work_day,
            "hours": 8 if is_work_day else 0,
            "location": ("TT" if is_tt else "Bureau") if is_work_day else None,
        })
    return result


def print_summary(title: str, work_days: list[dict]):
    print(f"\n{title}")
    print("-" * 60)

    for day in work_days:
        if day["is_weekend"]:
            continue
        label = f"  {day['name'].capitalize()} {day['date_str']}"
        if day["is_holiday"]:
            print(f"{label} : Jour ferie")
        elif day["is_conge"]:
            print(f"{label} : Conge")
        else:
            loc = "TT" if day["location"] == "TT" else "Bureau"
            print(f"{label} : {loc} ; Avant-vente : {day['hours']}h")

    total = sum(d["hours"] for d in work_days)
    print("-" * 60)
    print(f"  Total : {total}h")


def main():
    parser = argparse.ArgumentParser(description="Feuille Detente - Saisie automatique")
    parser.add_argument("--tt", default="", help="Jours de teletravail (ex: lundi,mercredi)")
    parser.add_argument("--conges", default="", help="Jours de conge (ex: vendredi)")
    parser.add_argument("--headless", action="store_true", help="Navigateur en arriere-plan")
    parser.add_argument("--samedi", default="", help="Date du samedi cible (DD/MM/YYYY). Defaut: samedi de la semaine courante")
    parser.add_argument("--dry-run", action="store_true", help="Afficher le resume sans saisir")
    args = parser.parse_args()

    tt = [d.strip().lower() for d in args.tt.split(",") if d.strip()]
    conges = [d.strip().lower() for d in args.conges.split(",") if d.strip()]

    env = load_env()
    if not env.get("UID") or not env.get("PASSWORD") or not env.get("LOGIN_URL"):
        print("Erreur: UID, PASSWORD et LOGIN_URL requis dans .env", file=sys.stderr)
        sys.exit(1)

    ref = None
    if args.samedi:
        ref = datetime.strptime(args.samedi, "%d/%m/%Y").date()
    week = get_current_week(ref)
    work_days = build_work_days(week, tt, conges)

    print_summary("Feuille des temps - Prevision", work_days)

    if args.dry_run:
        print("\nMode dry-run : pas de saisie effectuee.")
        return

    print("\nLancement de la saisie automatique...")
    run_automation(
        uid=env["UID"],
        password=env["PASSWORD"],
        login_url=env["LOGIN_URL"],
        week=week,
        work_days=work_days,
        headless=args.headless,
    )

    # Notification Discord simulée
    print("\n--- Notification Discord (simulee) ---")
    print_summary("Feuille des temps creee", work_days)
    print("\n  Rappel 13h45 : la feuille sera soumise a 14h si OK.")


if __name__ == "__main__":
    main()
