import pytest
import responses
from redis import StrictRedis

from checkbot import Checkbot


class TestCheckbot:
    @pytest.fixture(autouse=True)
    def flush_redis(self):
        StrictRedis().flushall()

    @responses.activate
    def test_check_points(self):
        pass
        # responses.add(
        #     responses.GET,
        #     self.today_url,
        #     match_querystring=True,
        #     json=schedule.serialized(),
        # )

        # poll()

        # self.assert_calls(self.yesterday_url, self.today_url)
