# settings for app

# PAYPAL_ENDPOINT = 'https://svcs.sandbox.paypal.com/AdaptivePayments/' # sandbox
PAYPAL_ENDPOINT = 'https://svcs.paypal.com/AdaptivePayments/' # production

# PAYPAL_PAYMENT_HOST = 'https://www.sandbox.paypal.com/au/cgi-bin/webscr' # sandbox
PAYPAL_PAYMENT_HOST = 'https://www.paypal.com/webscr' # production

PAYPAL_USERID = 'will.taylor_api1.60secondlaundry.com'
PAYPAL_PASSWORD = 'A49UBQGNB867WYB5'
PAYPAL_SIGNATURE = 'A9DjNk8Rr-UrlRVhRUm.1wVPW2SpAHPVaivltNg.Tt6SlbMHUzxFQQ2V'
# PAYPAL_APPLICATION_ID = 'APP-80W284485P519543T' # sandbox only
PAYPAL_APPLICATION_ID = 'APP-80W284485P519543T' # sandbox only
PAYPAL_EMAIL = 'will.taylor-facilitator@60secondlaundry.com'

PREAPPROVAL_PERIOD = 182 # days to ask for in a preapproval

DEBUG = False # No outbound texts or emails.

PAYPAL_COMMISSION = 0.1