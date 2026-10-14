from datetime import date, timedelta


def _easter(year: int) -> date:
    """Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def get_french_holidays(year: int) -> set[date]:
    easter = _easter(year)
    return {
        date(year, 1, 1),       # Jour de l'an
        easter + timedelta(1),   # Lundi de Pâques
        date(year, 5, 1),       # Fête du travail
        date(year, 5, 8),       # Victoire 1945
        easter + timedelta(39),  # Ascension
        easter + timedelta(50),  # Lundi de Pentecôte
        date(year, 7, 14),      # Fête nationale
        date(year, 8, 15),      # Assomption
        date(year, 11, 1),      # Toussaint
        date(year, 11, 11),     # Armistice
        date(year, 12, 25),     # Noël
    }


DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def get_current_week(reference: date | None = None):
    """Return week info: Sunday→Saturday, matching PeopleSoft TIME1(Di)→TIME7(Sam)."""
    ref = reference or date.today()
    # Python: monday=0 … sunday=6. PeopleSoft week starts Sunday.
    py_weekday = ref.weekday()  # 0=Mon … 6=Sun
    # Sunday of current week
    sunday = ref - timedelta(days=(py_weekday + 1) % 7)
    saturday = sunday + timedelta(6)

    holidays = get_french_holidays(sunday.year)
    if saturday.year != sunday.year:
        holidays |= get_french_holidays(saturday.year)

    # PeopleSoft order: Di(TIME1), Lu(TIME2), Ma(TIME3), Me(TIME4), Je(TIME5), Ve(TIME6), Sam(TIME7)
    ps_day_names = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    days = []
    for i in range(7):
        d = sunday + timedelta(i)
        days.append({
            "index": i,
            "time_field_index": i + 1,  # TIME1=sunday … TIME7=saturday
            "name": ps_day_names[i],
            "date": d,
            "date_str": d.strftime("%d/%m"),
            "date_str_full": d.strftime("%d/%m/%Y"),
            "is_weekend": i == 0 or i == 6,
            "is_holiday": d in holidays,
        })

    return {
        "saturday": saturday,
        "saturday_str": saturday.strftime("%d/%m/%Y"),
        "days": days,
    }
