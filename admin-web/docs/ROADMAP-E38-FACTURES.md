# G-Connect · E38 · Factures PDF réelles

**Statut : implémenté en préproduction, émission manuelle contrôlée.**

## Livré dans `feat/e38-real-invoicing`

- Modèles Django : `InvoiceIssuerProfile`, `InvoiceSequence`, `IssuedInvoice`; migration `subscriptions.0005_issued_invoices`.
- Formulaire Superadmin pour la vraie raison sociale de l'émetteur, l'immatriculation, l'identifiant fiscal, le pays, l'adresse, le régime de taxe, la base légale d'exonération éventuelle et le préfixe des factures.
- Émission **uniquement** à partir d'une commande `SubscriptionCheckout` payée, vérifiée par le prestataire et liée au bon `BusinessSubscription`.
- Numérotation annuelle atomique `PREFIX-AAAA-000001`, une seule facture par transaction, sans doublon après nouvelle requête.
- Conservation de tous les éléments de la facture en instantanés immuables : émetteur, client, contrat, tarif payé, taxe, transaction, dates.
- Génération du PDF A4 avec ReportLab sur le serveur et vérification de texte dans les tests automatisés avec pypdf.
- Historique filtrable et paginé, récupération de ses propres factures pour Établissements et Entreprises, contrôle d'autorisation obligatoire par compte et organisation, PDF transmis en connexion authentifiée.
- Animations, couleurs, cartes et modales de l'identité Finance, alignées avec le reste de G-Connect.

## Routes

### Superadmin (MFA WebToken obligatoire)

- `GET /api/v1/backoffice/finance/issuer/` : paramètres juridiques (jamais de valeurs légales inventées).
- `PUT /api/v1/backoffice/finance/issuer/` : enregistrer l'émetteur réel.
- `GET /api/v1/backoffice/finance/invoices/?search=&page=1` : historique et recherche.
- `POST /api/v1/backoffice/finance/invoices/issue/` : émettre une seule fois depuis le paiement identifié ; fournir adresse, pays, e-mail du client et identifiant fiscal si applicable.
- `GET /api/v1/backoffice/finance/invoices/<id>/pdf/` : PDF authentifié.

### Organisations (session MFA de l'organisation, strictement isolée)

- `GET /api/v1/subscriptions/invoices/my/` : uniquement ses factures.
- `GET /api/v1/subscriptions/invoices/<id>/pdf/` : PDF de sa propre organisation ou 404.

## Activation locale

1. Sauvegarder `db.local.sqlite3`, puis `python manage.py migrate --settings=gconnect_api.settings.dev` sur la base explicitement sélectionnée via `GCONNECT_DEV_DB_PATH`.
2. Installer les deux dépendances `reportlab` et `pypdf` incluses dans `requirements.txt`.
3. Démarrer le backend et le frontend depuis les branches E38 respectives.
4. Dans Superadmin > Factures & paiements : configurer **la véritable entité émettrice** et le régime fiscal vérifié. Aucun paramètre fiscal n'est prérempli.
5. Sur une commande déjà vérifiée par CinetPay, saisir l'adresse et le pays du client, puis cliquer sur **Émettre facture**. Elle apparaît dans l'historique et le PDF est téléchargeable dans les trois espaces autorisés.

## Précautions obligatoires avant facturation en production

- Vérifier l'identité légale et le régime fiscal applicable avec un responsable fiscal / comptable du pays d'émission. Le contrôle automatisé vérifie la présence et la forme des données, **pas la validité juridique des identifiants**.
- La première version émet les factures **sur demande explicite du Superadmin** pour les paiements en ligne vérifiés. Pas d'émission automatique après checkout faute de données de facturation client obligatoires : il faut un profil de facturation client complet avant d'automatiser.
- Les montants sont les sommes brutes réellement payées. Si le régime est `included`, la taxe est calculée comme fraction incluse; si `exempt`, une raison légale est obligatoire.
- Aucun avoir, annulation comptable ou envoi SMTP de facture automatique n'est encore fourni. Ces flux doivent être implémentés et validés avant production, ainsi que les politiques d'archivage et mentions obligatoires propres au pays.
- Une facture émise n'est pas modifiable. Une correction future doit créer un **avoir**, jamais écraser l'historique.
- Aucun paiement manuel ni forfait attribué gratuitement ne doit être présenté comme un encaissement.
