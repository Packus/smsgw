smsgw
=====

GoIP4 sms-gateway CLI API (for zabbix notify)

    * run without args - daemon mode (scan DB and send new sms)
    * 2 args: phone, msg - send sms to phone
    * 2 args: --ussd code - send ussd request with code and return response
    * featurs: --ussd --balance - get account balance for MTS provider
    *          --ussd --smspack - get left sms in package for MTS provider
