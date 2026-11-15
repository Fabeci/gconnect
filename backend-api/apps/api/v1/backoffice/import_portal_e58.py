"""E58 | Superadmin verified import cockpit.

Read-only history and safe, expiring preview for all supported files.
Only institution/promotion catalogues can be committed in E58.
Student/alumni account creation stays disabled here until an invitation-based
activation process replaces legacy generated passwords and active accounts.

Never expose existing ImportJob.created_rows: old records may include passwords.
"""
import csv
import hashlib
import io
import zipfile

from django.core import signing
from django.db import transaction
from django.db.models import Q, Sum
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.backoffice import imports as legacy
from apps.api.v1.backoffice.models import ImportJob
from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.models import Institution, Promotion
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ROWS = 500
SALT = "gconnect-import-e58-v1"
COLUMNS = {
    "establishments": ("name", "acronym", "text_code", "address", "phone", "email"),
    "promotions": ("name", "year", "department", "level", "is_general"),
    "students": ("email", "username", "first_name", "last_name", "date_of_birth", "student_id"),
    "alumni": ("email", "username", "first_name", "last_name", "graduation_date", "promotion_name"),
}
EXECUTABLE = frozenset(("establishments", "promotions"))


def _int(value, default):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result


def _signed_payload(raw, kind, institution):
    return {
        "digest": hashlib.sha256(raw).hexdigest(),
        "kind": kind,
        "institution": institution.pk if institution else None,
    }


def _load_csv(raw):
    try:
        text = raw.decode("utf-8-sig", errors="strict")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        if not header:
            raise ValueError("Fichier CSV vide.")
        names = [str(col).strip() for col in header]
        if not all(names) or len(names) != len(set(names)):
            raise ValueError("Colonnes CSV vides ou répétées.")
        if len(names) > 40:
            raise ValueError("Trop de colonnes.")
        rows = []
        for line in reader:
            if not any(value.strip() for value in line):
                continue
            if len(line) != len(names):
                raise ValueError("Une ligne comporte un nombre de colonnes incorrect.")
            rows.append(dict(zip(names, line)))
            if len(rows) > MAX_ROWS:
                raise ValueError("500 lignes maximum par import.")
        return names, rows
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("CSV invalide : utilisez UTF-8 et des colonnes cohérentes.") from exc


def _load_xlsx(raw):
    from openpyxl import load_workbook
    compressed = io.BytesIO(raw)
    try:
        with zipfile.ZipFile(compressed) as archive:
            if sum(meta.file_size for meta in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Classeur Excel trop volumineux après décompression.")
    except zipfile.BadZipFile as exc:
        raise ValueError("Classeur Excel invalide.") from exc
    try:
        with io.BytesIO(raw) as stream:
            workbook = load_workbook(stream, read_only=True, data_only=True, keep_links=False)
            try:
                data = workbook.active.iter_rows(values_only=True)
                first = next(data, None)
                if not first:
                    raise ValueError("Classeur Excel vide.")
                names = [str(col).strip() if col is not None else "" for col in first]
                if not all(names) or len(names) != len(set(names)):
                    raise ValueError("Colonnes Excel vides ou répétées.")
                if len(names) > 40:
                    raise ValueError("Trop de colonnes.")
                rows = []
                for record in data:
                    if not any(cell is not None and str(cell).strip() for cell in record):
                        continue
                    rows.append(dict(zip(names, record)))
                    if len(rows) > MAX_ROWS:
                        raise ValueError("500 lignes maximum par import.")
                return names, rows
            finally:
                workbook.close()
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Classeur Excel endommagé ou incompatible.") from exc


def _source(request):
    kind = str(request.data.get("import_type", "")).strip()
    if kind not in COLUMNS:
        raise ValueError("Type d'import invalide.")
    file = request.FILES.get("file")
    if not file:
        raise ValueError("Choisissez un fichier CSV ou XLSX.")
    name = str(file.name or "")[:255]
    if file.size < 1 or file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Le fichier doit être inférieur à 2 Mo.")
    if not (name.lower().endswith(".csv") or name.lower().endswith(".xlsx")):
        raise ValueError("Formats autorisés : CSV UTF-8 et XLSX.")
    raw = file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Le fichier dépasse 2 Mo.")
    institution = None
    if kind != "establishments":
        ident = _int(request.data.get("institution"), None)
        if not ident or ident < 1:
            raise ValueError("Sélectionnez l'établissement de destination.")
        institution = Institution.objects.filter(pk=ident, is_active=True).first()
        if not institution:
            raise ValueError("Établissement introuvable ou inactif.")
    fields, rows = _load_csv(raw) if name.lower().endswith(".csv") else _load_xlsx(raw)
    if "name" not in fields and kind in EXECUTABLE:
        raise ValueError("La colonne « name » est obligatoire.")
    if not rows:
        raise ValueError("Aucune ligne à importer.")
    return kind, name, raw, institution, fields, rows


def _preview_checks(kind, rows, institution):
    errors = []
    known = set()
    for index, record in enumerate(rows, start=2):
        name = str(record.get("name") or "").strip()
        if kind in EXECUTABLE:
            if not name:
                errors.append({"row": index, "message": "Le nom est obligatoire."})
                continue
            normal = name.casefold()
            if normal in known:
                errors.append({"row": index, "message": "Nom répété dans le fichier."})
            known.add(normal)
        if kind == "promotions":
            if Promotion.objects.filter(institution=institution, name__iexact=name).exists():
                errors.append({"row": index, "message": "Promotion déjà présente dans cet établissement."})
            year = str(record.get("year") or "").strip()
            if year and not year.isdecimal():
                errors.append({"row": index, "message": "Année invalide."})
        if kind == "establishments":
            code = str(record.get("text_code") or "").strip()
            if code and Institution.objects.filter(text_code=code).exists():
                errors.append({"row": index, "message": "Code établissement déjà utilisé."})
            if code:
                k = "code:" + code.casefold()
                if k in known:
                    errors.append({"row": index, "message": "Code établissement répété."})
                known.add(k)
        if kind in {"students", "alumni"} and not (
            str(record.get("email") or "").strip() and str(record.get("username") or "").strip()
        ):
            errors.append({"row": index, "message": "Email et identifiant requis."})
    return errors[:80]


class _SuperadminImportBase(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @staticmethod
    def reply(message, data):
        response = success_response(message, data)
        response["Cache-Control"] = "no-store"
        return response


class SuperadminImportDirectoryE58(_SuperadminImportBase):
    """GET historical job statistics. Generated passwords are never serialized."""

    def get(self, request):
        page = _int(request.query_params.get("page", 1), 1)
        kind = request.query_params.get("type", "all")
        if not page or page < 1 or kind not in set(COLUMNS) | {"all"}:
            return error_response("Paramètres invalides.", status_code=400)
        queryset = ImportJob.objects.select_related("institution", "initiated_by")
        all_jobs = ImportJob.objects
        summary = {
            "imports": all_jobs.count(),
            "integrated": all_jobs.aggregate(v=Sum("success_count"))["v"] or 0,
            "anomalies": all_jobs.aggregate(v=Sum("error_count"))["v"] or 0,
            "establishments": all_jobs.filter(import_type="establishments").aggregate(
                v=Sum("success_count")
            )["v"] or 0,
        }
        school_search = str(request.query_params.get("institution_search", "")).strip()[:80]
        schools = Institution.objects.filter(is_active=True)
        if school_search:
            schools = schools.filter(
                Q(name__icontains=school_search) | Q(acronym__icontains=school_search)
            )
        institutions = list(
            schools.order_by("name", "pk").values("id", "name")[:40]
        )
        if kind != "all":
            queryset = queryset.filter(import_type=kind)
        count = queryset.count()
        size = 8
        pages = max(1, (count + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)
        jobs = queryset.order_by("-created_at", "-pk")[(page - 1) * size:page * size]
        return self.reply("Historique réel des imports.", {
            "summary": summary, "count": count, "page": page, "pages": pages,
            "institutions": institutions,
            "results": [{
                "id": job.pk, "type": job.import_type, "file_name": job.file_name,
                "total": job.total_rows, "integrated": job.success_count,
                "anomalies": job.error_count,
                "institution": job.institution.name if job.institution else None,
                "operator": job.initiated_by.get_full_name().strip() or job.initiated_by.username
                    if job.initiated_by else "Compte supprimé",
                "created_at": job.created_at.isoformat(),
                # Never include created_rows / generated_password from legacy jobs.
            } for job in jobs],
        })


class SuperadminImportPreviewE58(_SuperadminImportBase):
    """POST multipart file, import_type, optional institution. No database changes."""

    def post(self, request):
        try:
            kind, name, raw, institution, fields, rows = _source(request)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)
        faults = _preview_checks(kind, rows, institution)
        enabled = kind in EXECUTABLE
        return self.reply("Prévisualisation sans écriture.", {
            "name": name, "type": kind, "institution": institution.pk if institution else None,
            "columns": fields, "rows": len(rows), "errors": faults,
            "executable": enabled and not faults,
            "notice": (
                "La création automatique de comptes étudiants et alumni est suspendue : "
                "un parcours d'activation sécurisé doit être raccordé."
                if not enabled else "L'import exigera une confirmation expresse."
            ),
            "preview_token": signing.dumps(
                _signed_payload(raw, kind, institution), salt=SALT, compress=False
            ) if enabled and not faults else None,
            "sample": [{
                "row": i, "values": {
                    key: str(row.get(key) or "")[:100]
                    for key in fields if key != "password"
                },
            } for i, row in enumerate(rows[:5], start=2)],
        })


class SuperadminImportExecuteE58(_SuperadminImportBase):
    """POST multipart with matching 10-minute preview signature and confirmation."""

    def post(self, request):
        if str(request.data.get("confirmation", "")).strip() != "CONFIRMER":
            return error_response("Confirmez explicitement cette opération.", status_code=400)
        try:
            kind, name, raw, institution, fields, rows = _source(request)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)
        if kind not in EXECUTABLE:
            return error_response("Création de comptes désactivée dans ce parcours.", status_code=403)
        try:
            signed = signing.loads(
                str(request.data.get("preview_token", "")), salt=SALT, max_age=600,
            )
        except (signing.BadSignature, signing.SignatureExpired):
            return error_response("Prévisualisation expirée : recommencez l'analyse.", status_code=400)
        if signed != _signed_payload(raw, kind, institution):
            return error_response("Le fichier ou la destination a changé.", status_code=400)
        faults = _preview_checks(kind, rows, institution)
        if faults:
            return error_response("Contrôles échoués : réanalysez ce fichier.", status_code=409)
        try:
            with transaction.atomic():
                if kind == "establishments":
                    created, errors = legacy.import_establishments(rows)
                else:
                    created, errors = legacy.import_promotions(rows, institution)
                if errors or len(created) != len(rows):
                    raise ValueError("Certaines lignes n'ont pas été intégrées, import annulé.")
                job = ImportJob.objects.create(
                    initiated_by=request.user, institution=institution,
                    import_type=kind, file_name=name,
                    total_rows=len(rows), success_count=len(created), error_count=0,
                    errors=[], created_rows=[],
                )
                log_audit_event(
                    "import_completed", user=request.user, request=request,
                    metadata={
                        "import_type": kind,
                        "job_id": job.pk,
                        "institution_id": institution.pk if institution else None,
                        "total": len(rows), "success": len(created), "errors": 0,
                    },
                )
        except Exception:
            return error_response(
                "Import annulé sans intégration : vérifiez le fichier et les doublons.",
                status_code=409,
            )
        return self.reply("Import terminé.", {
            "job_id": job.pk, "integrated": job.success_count, "anomalies": 0,
        })
