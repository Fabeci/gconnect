"""
G-Connect - Validateurs partagés
"""

from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 Mo


def validate_image_upload(file, label):
    """
    Valide un fichier image uploadé (taille + format RÉEL du contenu, pas le
    content_type déclaré par le client — celui-ci n'est pas fiable : certains
    clients mobiles (ex. image_picker sur Android/iOS) envoient des fichiers
    sans extension exploitable ou avec un content_type générique
    (application/octet-stream), ce qui provoquait des faux rejets alors que
    l'image était un JPEG/PNG parfaitement valide.

    Retourne un message d'erreur (str) si invalide, sinon None.
    Repositionne le curseur du fichier à 0 après lecture.
    """
    if file.size > MAX_IMAGE_SIZE:
        return f'{label} dépasse la taille maximale autorisée (5 Mo).'

    try:
        with Image.open(file) as img:
            img.verify()
            fmt = img.format
    except Exception:
        # PIL peut lever différents types selon la corruption (SyntaxError,
        # UnidentifiedImageError, OSError...) — tout échec de parsing signifie
        # simplement "pas une image valide" du point de vue de l'utilisateur.
        return f'{label} doit être une image valide (JPG, PNG ou WEBP).'
    finally:
        file.seek(0)

    if fmt not in ALLOWED_IMAGE_FORMATS:
        return f'{label} doit être au format JPG, PNG ou WEBP.'

    return None
