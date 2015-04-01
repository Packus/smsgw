#!/usr/bin/env python
# config.py
conf = {
	'sms_gw_host':'GOIP_IPADDRESS OR DNS',
  'sms_gw_user':'GOIP_admin',
  'sms_gw_passwd':'GOIP_PASSWORD',
  'daemon_loop_timeout':7,
	'db_engine':'mysql',
	'db_user':'zabbix',
	'db_passwd':'zabbix',
	'db_host':'MYSQL_IPADDRESS OR DNS',
	'db_base':'zabbix',
	
	'log' : {
		'filename':'/var/log/zabbix/sms.log',
		'maxSizeMB':'16',
		'backupCount':'10',
		'format':'%(asctime)s - %(levelname)s - %(message)s',
		'level':'INFO'
	},

	'providers' : {
		'mts':'1',
		'megafon':'2'
	}
}
