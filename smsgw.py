#!/usr/bin/env python
# coding=utf-8

"""
    GoIP4 sms-gateway CLI API (for zabbix notify)

    * run without args - daemon mode (scan DB and send new sms)
    * 2 args: phone, msg - send sms to phone
    * 2 args: --ussd code - send ussd request with code and return response
    * featurs: --ussd --balance - get account balance for MTS provider
    *          --ussd --smspack - get left sms in package for MTS provider
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker

import logging
import logging.handlers
from datetime import datetime

import sys,os,re
import time
import urllib
import urllib2
import config as config

from config import conf

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

logger = logging.getLogger('smsgw')
logger_alc = logging.getLogger('sqlalchemy.engine')
logger_alc.setLevel(logging.ERROR)

LogHandler = logging.handlers.RotatingFileHandler(
    filename=conf['log']['filename'],
    maxBytes=conf['log']['maxSizeMB'] * 1024 * 1024,
    backupCount=conf['log']['backupCount'])
LogHandler.setFormatter(logging.Formatter(conf['log']['format']))
logger.addHandler(LogHandler)
logger.setLevel(conf['log']['level'])

logger_alc.addHandler(LogHandler)

stderr_logger = logging.getLogger('STDERR')
stderr_logger.addHandler(LogHandler)
sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)

# connecting to DB for logging
db = declarative_base()
db_connection_str = '{db_engine}://{db_user}:{db_passwd}@{db_host}/{db_base}'.format(**conf)
logger.debug('>> connection_string: ' + db_connection_str.replace(conf['db_passwd'], '********'))
db_engine = create_engine(db_connection_str)


class SMS(db):
    """ sms model """

    __tablename__ = 'sms'
    id = Column(Integer, primary_key=True, autoincrement=True)
    add_time = Column(DateTime, nullable=False, default=datetime.now())
    prov = Column(String(255), nullable=False, default='mts')
    phone = Column(String(11), nullable=False)
    msg = Column(Text, nullable=False)
    sent_time = Column(DateTime, default=None)

db.metadata.create_all(db_engine)
db_session = sessionmaker(bind=db_engine, autocommit=True)()


def get_USSD(ussd, prov):
    """ send ussd request and return response """

    smskey = uid8()
    req_values = dict(
        line=conf['providers'][prov],
        smskey=smskey,
        action='USSD',
        telnum=ussd,
        send='Send'
    )
    url_ussd = 'http://' + conf['sms_gw_host'] + '/default/en_US/ussd_info.html'
    req_values = urllib.urlencode(req_values)
    req = urllib2.Request(url_ussd, data=req_values)
    req.add_header('Authorization', encUserData(conf['sms_gw_user'], conf['sms_gw_passwd']))
    urllib2.urlopen(req)

    url_check = 'http://' + conf['sms_gw_host'] + '/default/en_US/send_sms_status.xml'
    req_status = urllib2.Request(url_check, data=req_values)
    req_status.add_header('Authorization', encUserData(conf['sms_gw_user'], conf['sms_gw_passwd']))
    resp = urllib2.urlopen(req_status)
    resp_content = resp.read()

    # wait for DONE response
    while 1:
        if (resp_content.find('DONE') > -1) and (resp_content.find(smskey) > -1):
            break
        else:
            resp = urllib2.urlopen(req_status)
            resp_content = resp.read()
            time.sleep(1)
    return resp_content[resp_content.find('<error>') + len('<error>'):resp_content.find('</error>')].decode('gb2312')


def get_msgs_count(all=False):
    """ get sent sms count from DB """

    if all:
        return db_session.query(SMS).count()
    else:
        return db_session.query(SMS).filter(SMS.sent_time == None).count()

uid8 = lambda: time.time().hex()[-11:-3]
encUserData = lambda user, passw: "Basic " + (user + ":" + passw).encode("base64").rstrip()


def daemon_loop():
    """ daemon mode: detect new sms in DB and send them """

    url_send = 'http://' + conf['sms_gw_host'] + '/default/en_US/sms_info.html'
    logger.debug('sms-gw url for send messages    : ' + url_send)
    url_check = 'http://' + conf['sms_gw_host'] + '/default/en_US/send_sms_status.xml'
    logger.debug('sms-gw url for check line status: ' + url_check)
    logger.info('begin daemon-loop')

    while True:
        sms4send = db_session.query(SMS).filter(SMS.sent_time == None).order_by(SMS.add_time).first()
        if not sms4send:
            time.sleep(conf['daemon_loop_timeout'])
            continue
        smskey = uid8()
        req_values = dict(
            line=conf['providers'][sms4send.prov],
            smskey=smskey,
            action='SMS',
            telnum=sms4send.phone,
            smscontent=sms4send.msg,
            send='Send'
        )
        req_values = urllib.urlencode(req_values)
        logger.debug('msg id={0} : prepare to send (msg:"{1}" to phone:{2} via prov:{3})'.format(
            sms4send.id, sms4send.msg, sms4send.phone, sms4send.prov))

        req = urllib2.Request(url_send, data=req_values)
        req.add_header('Authorization', encUserData(conf['sms_gw_user'], conf['sms_gw_passwd']))

        logger.info('msg id={0} : send'.format(sms4send.id))
        urllib2.urlopen(req)

        req_status = urllib2.Request(url_check, data=req_values)
        req_status.add_header('Authorization', encUserData(conf['sms_gw_user'], conf['sms_gw_passwd']))

        time.sleep(conf['daemon_loop_timeout'])
	logger.debug('begin to check line status')
        resp = urllib2.urlopen(req_status)
        resp_content = resp.read()

        while (-1 == resp_content.find('DONE')) and (-1 == resp_content.find(smskey)):
            resp = urllib2.urlopen(req_status)
            resp_content = resp.read()
            time.sleep(conf['daemon_loop_timeout'])
        logger.debug('recive status: DONE')
        curtime = datetime.now()
        logger.info('msg id={0} : sent in ({1})'.format(sms4send.id, curtime))
        db_session.begin()
        sms4send.sent_time = curtime
        db_session.commit()


def get_balance_mts():
    """ get account balance for MTS provider """

    ussd_res_string = get_USSD('*100#', 'mts')
    summ = ussd_res_string[ussd_res_string.find(':') + 1:ussd_res_string.find(',') + 3]
    summ = summ.replace(',', '.')
    return float(summ)


def get_sms_left_mts():
    """ get left sms count in SMS-package """

    ussd_res_string = get_USSD('*100*1#', 'mts').lower()
    count = ussd_res_string[ussd_res_string.find(':') + 1:ussd_res_string.find('sms')]
    count = count.replace(',', '.')
    return int(count)


def exit_with_help():
    """ help output """

    logger.error('wrong arguments ({0}) - exit'.format(','.join(sys.argv)))
    print('usage:\n '
          '\twithout arguments : run in daemon mode (send message from DB to sms-gw)\n'
          '\t<phone_number> <message_text> : add message to sms-queue (add record to DB)\n'
          '\t--ussd ussd_string <provider_name> : send USSD request\n')


argslen = len(sys.argv)

# args parsing
if 2 < argslen:
    if '--ussd' == sys.argv[1]:
        if '--balance' == sys.argv[2]:
            print get_balance_mts()
        elif '--smspack' == sys.argv[2]:
            print get_sms_left_mts()
        else:
            ussd = sys.argv[2]
            prov = sys.argv[3] if 3 < argslen else 'mts'
            print get_USSD(ussd, prov)
    else:
        phone_num = sys.argv[1]
        message = sys.argv[2]
        if conf['log']['level'] < logging.INFO:
            logger_alc.setLevel(logging.INFO)
        db_session.begin()
        db_session.add(SMS(phone=phone_num, msg=message))
        db_session.commit()
elif 1 == argslen:
    logger.info('>> run as daemon with timeout {0}s'.format(conf['daemon_loop_timeout']))
    daemon_loop()
else:
    exit_with_help()
