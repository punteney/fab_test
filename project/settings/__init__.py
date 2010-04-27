import os

##################
# Importing the appropriate settings file for this environment
##################
ENVIRONMENT = os.getenv("CONFIG_IDENTIFIER")
if not ENVIRONMENT:
    ENVIRONMENT = 'dev'

if ENVIRONMENT == 'production':
    from production import *
elif ENVIRONMENT == 'dev':
    from dev import *
    print("Dev settings enabled")
elif ENVIRONMENT == 'staging':
    from staging import *
