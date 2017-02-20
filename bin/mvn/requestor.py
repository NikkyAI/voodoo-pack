import base64
import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth


class Requestor(object):
    def __init__(self, username = None, password = None, user_agent = "Maven Artifact Downloader/1.0"):
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.session = requests.session()
        if username and password:
            self.session.auth = HTTPBasicAuth(self.username, self.password)

    def request(self, url, onFail, onSuccess):
        headers = {"User-Agent": self.user_agent}
        print(f'downloading {url}')
        response = self.session.get(url, stream=True)
        try:
            response.raise_for_status()
        except HTTPError as e:
            onFail(url, e)
        except RequestException as e:
            onFail(url, e)
        else: return onSuccess(response)

class RequestException(Exception):
    def __init__(self, msg):
        self.msg = msg
