-- disable konnect payment provider
UPDATE payment_provider
   SET konnect_wallet_key = NULL,
       konnect_api_key = NULL,
       lifespan = NULL,
       payment_fees = NULL,
       checkout_form = NULL,
       silent_webhook = NULL,
       theme = NULL,
       description = NULL,
       type = NULL;
DELETE FROM payment_method
WHERE id IN (
    (SELECT id
    FROM payment_method
    WHERE code IN ('bank_card', 'e-dinar', 'flouci', 'wallet')
    )
);
