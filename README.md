smsgw
=====

GoIP1 GoIP4 GoIP8 sms-gateway CLI API for Zabbix SMS alerting

    * run without args - daemon mode (scan DB and send new sms)
    * 2 args: phone, msg - send sms to phone
    * 2 args: --ussd code - send ussd request with code and return response
    * featurs: --ussd --balance - get account balance for MTS provider
    *          --ussd --smspack - get left sms in package for MTS provider

1. Put *.py files in _alertscripts_ folder, as you configure in zabbix-server.conf
2. In Zabbix menu Adinistration-> Media types create script item with path smsgw.py
3. In Administration -> Actions create an Action using your script.
