"""Helpers for numbering teaching weeks from the start of the school year."""

from datetime import date, timedelta
import re


ISO_WEEK_PATTERN = re.compile(r"^(?P<year>\d{4})-W(?P<week>\d{2})$")


def selected_date_from_value(value: str) -> date:
    """Parse an HTML input[type=week] value or an ISO date."""
    match = ISO_WEEK_PATTERN.fullmatch(value)
    if match:
        try:
            return date.fromisocalendar(int(match["year"]), int(match["week"]), 1)
        except ValueError as exc:
            raise ValueError("Semaine ISO invalide") from exc
    try:
        selected_date = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("La semaine doit etre au format AAAA-WNN ou AAAA-MM-JJ") from exc
    return selected_date


def school_week(value: str, school_start: date) -> dict:
    """Build teaching-week metadata from an administrator-defined school start."""
    selected_date = selected_date_from_value(value)
    if selected_date < school_start:
        raise ValueError("La date sélectionnée est antérieure à la rentrée scolaire")
    number = ((selected_date - school_start).days // 7) + 1
    week_start = school_start + timedelta(days=(number - 1) * 7)
    week_end = week_start + timedelta(days=6)
    academic_year = f"{school_start.year}-{school_start.year + 1}"
    return {
        "semaine": f"Semaine {number:02d}, {academic_year}",
        "semaine_numero": number,
        "annee_scolaire": academic_year,
        "date_debut": week_start.isoformat(),
        "date_fin": week_end.isoformat(),
        "semaine_iso": value,
    }
