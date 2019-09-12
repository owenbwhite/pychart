import requests
import sys
import json
import time

class ChartmetricException(Exception):

    def __init__(self, http_status, code, msg, headers=None):
        self.http_status = http_status
        self.code = code
        self.msg = msg
        if headers is None:
            headers = {}
        self.headers = headers

    def __str__(self):
        return 'http status: {0}, code:{1} - {2}'.format(
            self.http_status, self.code, self.msg)


class Chartmetric(object):

    trace = False
    trace_out = False
    max_get_retries = 10

    # Constructor
    def __init__(self, auth = None,
                 requests_session = True,
                 client_credentials_manager = None,
                 proxies = None,
                 requests_timeout = None
                ):

        self.prefix = 'https://api.chartmetric.com/api/'
        self._auth = auth
        self.client_credentials_manager = client_credentials_manager
        self.proxies = proxies
        self.requests_timeout = requests_timeout

        if isinstance(requests_session, requests.Session):
            self._session = requests.Session()
        else:
            from requests import api
            self._session = api

    def _auth_headers(self):
        if self._auth:
            return {'Authorization': 'Bearer {0}'.format(self._auth)}
        elif self.client_credentials_manager:
            token = self.client_credentials_manager.get_access_token()
            return {'Authorization': 'Bearer {0}'.format(token)}
        else:
            return {}

    def _internal_call(self, method, url, payload, params):
        args = dict(params = params)
        args["timeout"] = self.requests_timeout
        if not url.startswith("http"):
            url = self.prefix + url
        headers = self._auth_headers()
        headers['Content-Type'] = 'application/json'

        if payload:
            args['data'] = json.dumps(payload)

        if self.trace_out:
            print(url)

        r = self._session.request(method, url,
                                  headers=headers,
                                  proxies=self.proxies,
                                  **args)


        if self.trace:
            print()
            print('headers', headers)
            print('http_status', http)
            print(method, r.url)
            if payload:
                print('DATA', json.dumps(payload))
        try:
            r.raise_for_status()
        except:
            if r.text and len(r.text) > 0 and r.text != 'null':
                raise ChartmetricException(r.status_code, -1, '%s:\n %s' % (r.url, r.json()['error']['message']),
                    headers=r.headers)
            else:
                raise ChartmetricException(r.status_code, -1, '%s:\n %s' % (r.url, 'error'), headers=r.headers)
        finally:
            r.connection.close()
        if r.text and len(r.text) > 0 and r.text != 'null':
            results = r.json()
            if self.trace:
                print('RESP', results)
            print()
            return results
        else:
            return None

    def _get(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        retries = self.max_get_retries
        delay = 1
        while retries > 0:
            try:
                return self._internal_call('GET', url, payload, kwargs)
            except ChartmetricException as e:
                retries -= 1
                status = e.http_status
                if status == 429 or (status >= 500 and status < 600):
                    if retries < 0:
                        raise
                    else:
                        sleep_seconds = int(e.headers.get('Retry-After', delay))
                        print('retrying...' + str(sleep_seconds) + 'secs')
                        time.sleep(sleep_seconds + 1)
                        delay += 1
                else:
                    raise
            except Exception as e:
                raise
                print('exception', str(e))

                retries -= 1

                if retries >= 0:
                    sleep_seconds = int(e.headers.get('Retry-After', delay))
                    print('retrying...' + str(delay) + 'secs')
                    time.sleep(sleep_seconds + 1)
                    delay += 1
                else:
                    raise
    def track(self, track_id):
        # trid = self._get_id('track', track_id)
        return self._get('track/' + track_id)

    def search(self, query):
        return self._get('search?q=' + query)

    def _get_id(self, type, id):
        fields = id.split(':')
        if len(fields) >= 3:
            if type != fields[-2]:
                self._warn('expected id of type %s but found type %s %s',
                           type, fields[-2], id)
            return fields[-1]
        fields = id.split('/')
        if len(fields) >= 3:
            itype = fields[-2]
            if type != itype:
                self._warn('expected id of type %s but found type %s %s',
                           type, itype, id)
            return fields[-1]
        return id

    def _warn(self, msg, *args):
        print('warning:' + msg.format(*args), file=sys.stderr)
