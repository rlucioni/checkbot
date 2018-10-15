import urllib.parse
from unittest.mock import patch

import pytest
import responses
from redis import StrictRedis

from checkbot import (
    HMART_POINTS_URL,
    SLACK_CHANNEL,
    Checkbot,
)


bot = Checkbot()
SLACK_MESSAGE_URL = 'https://slack.com/api/chat.postMessage'


@patch('checkbot.HMART_NUMBER', '123')
@patch('checkbot.HMART_NAME', 'foo')
@patch('checkbot.HMART_ZIP', '98110')
@patch('checkbot.SLACK_API_TOKEN', 'fake-token')
class TestCheckbot:
    @pytest.fixture(autouse=True)
    def flush_redis(self):
        StrictRedis().flushall()

    def mock_slack(self):
        responses.add(
            responses.POST,
            SLACK_MESSAGE_URL,
            json={'ok': True},
        )

    def assert_calls(self, *urls):
        assert len(responses.calls) == len(urls)

        for index, url in enumerate(urls):
            assert responses.calls[index].request.url == url

    def assert_slack(self, call, message):
        body = dict(urllib.parse.parse_qsl(call.request.body))
        assert body['channel'] == SLACK_CHANNEL
        assert body['text'] == message

    def reset_calls(self):
        responses.calls.reset()

    @responses.activate
    def test_hmart(self):
        body = {
            'tpldata': [
                {
                    'custno': '123',
                    'custname': 'foo',
                    'trdate': '07/14/2018',
                    'point': '182',
                    'isdeleted': '0',
                },
            ],
        }

        responses.add(
            responses.POST,
            HMART_POINTS_URL,
            json=body,
        )

        self.mock_slack()

        bot.hmart()

        self.assert_calls(HMART_POINTS_URL, SLACK_MESSAGE_URL)
        self.assert_slack(responses.calls[1], '182 Hmart points as of 07/14/2018')
        self.reset_calls()

        bot.hmart()

        self.assert_calls(HMART_POINTS_URL)
        self.reset_calls()

        new_body = {
            'tpldata': [
                {
                    'custno': '123',
                    'custname': 'foo',
                    'trdate': '07/15/2018',
                    'point': '213',
                    'isdeleted': '0',
                },
            ],
        }

        responses.replace(
            responses.POST,
            HMART_POINTS_URL,
            json=new_body,
        )

        bot.hmart()

        self.assert_calls(HMART_POINTS_URL, SLACK_MESSAGE_URL)
        self.assert_slack(responses.calls[1], '213 Hmart points as of 07/15/2018')
