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

    if response.status_code == 200:
        logger.info('login get ok')
    else:
        logger.info('login get failed')

    soup = BeautifulSoup(response.text, 'html.parser')

    with open('forms/login.json') as f:
        form = json.load(f)

    form['__RequestVerificationToken'] = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
    form['__VIEWSTATE'] = soup.find(id='__VIEWSTATE').get('value')
    form['__EVENTVALIDATION'] = soup.find(id='__EVENTVALIDATION').get('value')
    form['dnn$ctr689$View$txtUserName'] = EZ_USERNAME
    form['dnn$ctr689$View$txtPassword'] = EZ_PASSWORD

    response = session.post(login_url, data=form)

    if response.status_code == 200:
        logger.info('login post ok')
    else:
        logger.info('login post failed')


def exception_handler(*args, **kwargs):
    # prevents invocation retry
    return True


if __name__ == '__main__':
    # check()
    login()
