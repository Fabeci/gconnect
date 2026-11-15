# backoffice/imports.py
"""
Import massif CSV/Excel — étudiants, alumni, promotions, établissements.
Chaque ligne est traitée dans sa propre transaction : une ligne en erreur
n'annule pas les lignes déjà importées avec succès. Les comptes créés par
import (étudiants/alumni) sont directement actifs — l'import est réalisé
par un admin déjà habilité (établissement ou superAdmin), contrairement à
l'auto-inscription publique qui exige une commande de comptes approuvée.

Note : le document justificatif alumni (`proof_document`, obligatoire à
l'auto-inscription) est laissé vide pour les comptes importés en masse —
l'import lui-même constitue la vérification côté admin.
"""
import csv
import io
import secrets
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from openpyxl import load_workbook

from apps.api.v1.establishments.models import (
    AlumniInstitution, AlumniPromotionMembership, Institution, Promotion,
    PromotionMembership, StudentInstitution,
)
from apps.api.v1.users.models import Alumni, Student

User = get_user_model()


def parse_rows(uploaded_file):
    """Retourne une liste de dicts {en-tête: valeur} depuis un .csv ou .xlsx."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        text = uploaded_file.read().decode("utf-8-sig")
        return [dict(row) for row in csv.DictReader(io.StringIO(text))]
    if name.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(uploaded_file, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        return [
            {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
            for row in rows[1:]
            if any(v is not None and str(v).strip() for v in row)
        ]
    raise ValueError("Format non supporté — utilisez un fichier .csv ou .xlsx.")


def _clean(row, key):
    v = row.get(key)
    return "" if v is None else str(v).strip()


def _parse_date(raw):
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"date invalide : « {raw} » (attendu AAAA-MM-JJ)")


def import_students(rows, institution):
    """Colonnes attendues : email, username, first_name, last_name,
    phone_number, password (optionnel), gender, date_of_birth, student_id."""
    errors, created = [], []
    general_promotion = Promotion.objects.filter(institution=institution, is_general=True).first()

    for i, row in enumerate(rows, start=2):  # ligne 1 = en-têtes
        email = _clean(row, "email")
        username = _clean(row, "username")
        try:
            if not email or not username:
                raise ValueError("email et username sont requis.")
            if User.objects.filter(email=email).exists():
                raise ValueError(f"email déjà utilisé : {email}")
            if User.objects.filter(username=username).exists():
                raise ValueError(f"username déjà pris : {username}")

            date_of_birth = _parse_date(_clean(row, "date_of_birth"))
            if not date_of_birth:
                raise ValueError("date_of_birth est requis (AAAA-MM-JJ).")

            provided_password = _clean(row, "password")
            password = provided_password or secrets.token_urlsafe(9)

            with transaction.atomic():
                user = User.objects.create_user(
                    email=email, username=username, password=password,
                    first_name=_clean(row, "first_name"), last_name=_clean(row, "last_name"),
                    phone_number=_clean(row, "phone_number"),
                    role="student", is_active=True,
                )
                student = Student.objects.create(
                    user=user,
                    gender=_clean(row, "gender") or "O",
                    date_of_birth=date_of_birth,
                    student_id=_clean(row, "student_id") or None,
                )
                StudentInstitution.objects.get_or_create(
                    student=student, institution=institution, defaults={"is_primary": True}
                )
                if general_promotion:
                    PromotionMembership.objects.get_or_create(
                        student=student, promotion=general_promotion, defaults={"is_approved": True}
                    )
            created.append({
                "row": i, "email": email,
                "generated_password": None if provided_password else password,
            })
        except Exception as exc:
            errors.append({"row": i, "message": str(exc)})

    return created, errors


def import_alumni(rows, institution):
    """Colonnes attendues : email, username, first_name, last_name,
    phone_number, password (optionnel), gender, graduation_date,
    promotion_name (optionnel — recherché dans l'établissement cible)."""
    errors, created = [], []

    for i, row in enumerate(rows, start=2):
        email = _clean(row, "email")
        username = _clean(row, "username")
        try:
            if not email or not username:
                raise ValueError("email et username sont requis.")
            if User.objects.filter(email=email).exists():
                raise ValueError(f"email déjà utilisé : {email}")
            if User.objects.filter(username=username).exists():
                raise ValueError(f"username déjà pris : {username}")

            promotion = None
            promo_name = _clean(row, "promotion_name")
            if promo_name:
                promotion = Promotion.objects.filter(institution=institution, name__iexact=promo_name).first()
                if not promotion:
                    raise ValueError(f"promotion introuvable dans cet établissement : « {promo_name} »")

            graduation_date = _parse_date(_clean(row, "graduation_date"))
            provided_password = _clean(row, "password")
            password = provided_password or secrets.token_urlsafe(9)

            with transaction.atomic():
                user = User.objects.create_user(
                    email=email, username=username, password=password,
                    first_name=_clean(row, "first_name"), last_name=_clean(row, "last_name"),
                    phone_number=_clean(row, "phone_number"),
                    role="alumni", is_active=True,
                )
                alumni = Alumni.objects.create(
                    user=user, gender=_clean(row, "gender") or "O",
                    proof_document="", institution=institution, promotion=promotion,
                    graduation_date=graduation_date,
                )
                AlumniInstitution.objects.get_or_create(alumni=alumni, institution=institution)
                if promotion:
                    AlumniPromotionMembership.objects.get_or_create(
                        alumni=alumni, promotion=promotion, defaults={"is_approved": True}
                    )
            created.append({
                "row": i, "email": email,
                "generated_password": None if provided_password else password,
            })
        except Exception as exc:
            errors.append({"row": i, "message": str(exc)})

    return created, errors


def import_promotions(rows, institution):
    """Colonnes attendues : name, is_general (optionnel), year (optionnel),
    department (optionnel), level (optionnel)."""
    errors, created = [], []

    for i, row in enumerate(rows, start=2):
        name = _clean(row, "name")
        try:
            if not name:
                raise ValueError("name est requis.")
            if Promotion.objects.filter(institution=institution, name__iexact=name).exists():
                raise ValueError(f"une promotion « {name} » existe déjà pour cet établissement.")

            year_raw = _clean(row, "year")
            promo = Promotion.objects.create(
                institution=institution, name=name,
                is_general=_clean(row, "is_general").lower() in ("true", "1", "oui", "yes"),
                year=int(year_raw) if year_raw.isdigit() else None,
                department=_clean(row, "department"),
                level=_clean(row, "level") or "OTHER",
            )
            created.append({"row": i, "name": promo.name})
        except Exception as exc:
            errors.append({"row": i, "message": str(exc)})

    return created, errors


def import_establishments(rows):
    """Colonnes attendues : name, acronym (optionnel), text_code (optionnel,
    auto-généré sinon), address, phone, email. Réservé au superAdmin."""
    errors, created = [], []

    for i, row in enumerate(rows, start=2):
        name = _clean(row, "name")
        text_code = _clean(row, "text_code")
        try:
            if not name:
                raise ValueError("name est requis.")
            if text_code and Institution.objects.filter(text_code=text_code).exists():
                raise ValueError(f"text_code déjà utilisé : {text_code}")

            inst = Institution.objects.create(
                name=name, acronym=_clean(row, "acronym"), text_code=text_code,
                address=_clean(row, "address"), phone=_clean(row, "phone"),
                email=_clean(row, "email"),
            )
            created.append({"row": i, "name": inst.name, "text_code": inst.text_code})
        except Exception as exc:
            errors.append({"row": i, "message": str(exc)})

    return created, errors


IMPORTERS = {
    "students": import_students,
    "alumni": import_alumni,
    "promotions": import_promotions,
}
