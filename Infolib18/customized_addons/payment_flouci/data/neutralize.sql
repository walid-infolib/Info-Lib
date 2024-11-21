-- disable flouci payment provider
UPDATE payment_provider
   SET flouci_app_token = NULL,
       flouci_app_secret = NULL;
DELETE FROM payment_method
WHERE id IN (
    (SELECT id
    FROM payment_method
    WHERE code IN ('flouci_methods')
    )
);
