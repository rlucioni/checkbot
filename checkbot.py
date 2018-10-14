import json
import logging
import os
from logging.config import dictConfig

import requests
from bs4 import BeautifulSoup
from redis import StrictRedis
from slackclient import SlackClient


dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '{asctime} {levelname} {process} [{filename}:{lineno}] - {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
})

logger = logging.getLogger(__name__)


HMART_NUMBER = os.environ.get('HMART_NUMBER')
HMART_NAME = os.environ.get('HMART_NAME')
HMART_ZIP = os.environ.get('HMART_ZIP')
HMART_POINTS_URL = 'http://scpoint.hmart.com/Controller-DMZPointInquiry/jsp/smc-dmz-get-cust-point.jsp'

EZ_USERNAME = os.environ.get('EZ_USERNAME')
EZ_PASSWORD = os.environ.get('EZ_PASSWORD')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_POINTS_KEY = 'points'

SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN')
SLACK_CHANNEL = '#checkbot'


class Checkbot:
    def __init__(self):
        self.redis = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
        self.slack = SlackClient(SLACK_API_TOKEN)

    def check(self):
        form = {
            'custno': HMART_NUMBER,
            'lastname': HMART_NAME,
            'zipcode': HMART_ZIP,
        }

        logger.info(f'checking points for {form}')

        response = requests.post(HMART_POINTS_URL, data=form)
        data = response.json()
        points = data['tpldata'][0]['point']
        date = data['tpldata'][0]['trdate']

        logger.info(f'{points} points as of {date}')

        cached = self.redis.get(REDIS_POINTS_KEY)
        is_point_change = int(points) != int(cached) if cached else False

        if not cached or is_point_change:
            logger.info('current points differ from cached points')

            self.redis.set(REDIS_POINTS_KEY, points)

            # TODO: include difference between old and new totals in message?
            self.message(f'{points} Hmart points as of {date}')

    def message(self, message):
        self.slack.api_call(
            'chat.postMessage',
            channel=SLACK_CHANNEL,
            text=message,
        )


def check():
    try:
        Checkbot().check()
    except:
        logger.exception('something went wrong')


def login():
    base_url = 'https://www.ezdrivema.com'
    session = requests.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/69.0.3497.100 Safari/537.36'
        )
    })

    login_url = f'{base_url}/ezpassmalogin'
    response = session.get(login_url)
    logger.info(f'{login_url} get {response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')

    with open('forms/login.json') as f:
        form = json.load(f)

    form['__RequestVerificationToken'] = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
    form['__VIEWSTATE'] = soup.find(id='__VIEWSTATE').get('value')
    form['__EVENTVALIDATION'] = soup.find(id='__EVENTVALIDATION').get('value')
    form['dnn$ctr689$View$txtUserName'] = EZ_USERNAME
    form['dnn$ctr689$View$txtPassword'] = EZ_PASSWORD

    response = session.post(login_url, data=form)
    logger.info(f'{login_url} post {response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')
    balance = soup.find(id='dnn_ctr670_ucAccountSummaryMassDot_lblBalance').text
    logger.info(f'balance {balance}')

    tx_url = f'{base_url}/ezpassviewtransactions'
    response = session.get(tx_url)
    logger.info(f'{tx_url} get {response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')

    with open('forms/tx.json') as f:
        form = json.load(f)

    form['__RequestVerificationToken'] = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
    form['__VIEWSTATE'] = soup.find(id='__VIEWSTATE').get('value')
    form['__EVENTVALIDATION'] = soup.find(id='__EVENTVALIDATION').get('value')
    form['dnn$ctr1180$ucMassDotTcoreTransaction$ucBaseTcoreTransaction$txtStartDate'] = '10/01/2018'
    form['dnn$ctr1180$ucMassDotTcoreTransaction$ucBaseTcoreTransaction$txtEndDate'] = '10/13/2018'

    response = session.post(tx_url, data=form)
    logger.info(f'{tx_url} post {response.status_code}')

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find(id='dnn_ctr1180_ucMassDotTcoreTransaction_ucBaseTcoreTransaction_AccountGridView')
    rows = table.find_all('tr')
    header = rows.pop(0)
    total = rows.pop()

    dollars = total.find_all('td')[-1].text
    if dollars.startswith('('):
        stripped = dollars.strip('()')
        dollars = f'-{stripped}'

    logger.info(f'found {len(rows)} transactions totaling {dollars}')

    for row in rows:
        cells = row.find_all('td')
        tx_type = cells[2].text.lower().strip()

        if 'toll' in tx_type:
            toll_ts = cells[1].get_text(' ')
            toll_loc = cells[6].text
            toll_dollars = cells[8].text.strip('()')

            logger.info(f'{tx_type} {toll_dollars} at {toll_loc} {toll_ts}')
        elif 'replenish' in tx_type:
            replenish_ts = cells[0].text
            replenish_dollars = cells[8].text

            logger.info(f'{tx_type} {replenish_dollars} on {replenish_ts}')


def exception_handler(*args, **kwargs):
    # prevents invocation retry
    return True


if __name__ == '__main__':
    # check()
    login()
