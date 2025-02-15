#!/bin/bash
source /home/pi/.bash_tvh
python3 ~/check_m3u.py -s 127.0.0.1:9981 -user "${TVH_USER}" -pass "${TVH_PASS}" --smtp-server "${SMTP_SERVER}" --smtp-port "${SMTP_PORT}" --sender-email "${SMTP_SENDER}" --recipient-email ""${SMTP_RECIPIENT}"" --smtp-username "${SMTP_USER}" --smtp-password "${SMTP_PASS}"
