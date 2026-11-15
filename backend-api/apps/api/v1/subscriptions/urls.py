from django.urls import path

from .views import (
    CatalogView, MySubscriptionView, SuperadminOffersView,
    SuperadminOfferDetailView, SuperadminPricesView,
    SuperadminAssignmentsView, SuperadminAssignmentDetailView, SuperadminOrganisationsView, SuperadminPriceDetailView,
    SuperadminTopUpView, InstitutionSeatsView,
)

from .request_views import (
    MySubscriptionRequestsView, SuperadminSubscriptionRequestsView,
    SuperadminSubscriptionRequestDetailView,
)

from .invoice_views import MyInvoicesE38, MyInvoicePdfE38

from .checkout_views import (
    CheckoutConfigurationView, CheckoutOrdersView, CheckoutStartView,
    CheckoutVerifyView, CheckoutNotificationView,
)

urlpatterns = [
    path("invoices/my/", MyInvoicesE38.as_view(), name="e38-my-invoices"),
    path("invoices/<int:invoice_id>/pdf/", MyInvoicePdfE38.as_view(), name="e38-my-invoice-pdf"),
    path("checkout/config/", CheckoutConfigurationView.as_view(), name="subscription-checkout-config"),
    path("checkout/orders/", CheckoutOrdersView.as_view(), name="subscription-checkout-orders"),
    path("checkout/start/", CheckoutStartView.as_view(), name="subscription-checkout-start"),
    path("checkout/<uuid:transaction_id>/verify/", CheckoutVerifyView.as_view(), name="subscription-checkout-verify"),
    path("checkout/notify/", CheckoutNotificationView.as_view(), name="subscription-checkout-notify"),
    path("requests/my/", MySubscriptionRequestsView.as_view(), name="subscription-change-requests-my"),
    path("admin/requests/", SuperadminSubscriptionRequestsView.as_view(), name="subscription-change-requests-admin"),
    path("admin/requests/<int:request_id>/", SuperadminSubscriptionRequestDetailView.as_view(), name="subscription-change-request-review"),
    path("catalog/", CatalogView.as_view(), name="subscription-catalog"),
    path("my/", MySubscriptionView.as_view(), name="subscription-my"),
    path("institution/seats/", InstitutionSeatsView.as_view(), name="subscription-institution-seats"),
    path("admin/offers/", SuperadminOffersView.as_view(), name="subscription-admin-offers"),
    path("admin/offers/<int:offer_id>/", SuperadminOfferDetailView.as_view(), name="subscription-admin-offer"),
    path("admin/prices/", SuperadminPricesView.as_view(), name="subscription-admin-prices"),
    path("admin/prices/<int:price_id>/", SuperadminPriceDetailView.as_view(), name="subscription-admin-price"),
    path("admin/organisations/", SuperadminOrganisationsView.as_view(), name="subscription-admin-organisations"),
    path("admin/assignments/", SuperadminAssignmentsView.as_view(), name="subscription-admin-assignments"),
    path("admin/assignments/<int:subscription_id>/", SuperadminAssignmentDetailView.as_view(), name="subscription-admin-assignment"),
    path("admin/assignments/<int:subscription_id>/topups/", SuperadminTopUpView.as_view(), name="subscription-admin-topups"),
]

