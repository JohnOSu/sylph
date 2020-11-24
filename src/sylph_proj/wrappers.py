import sys
import os
import logging

import urllib3
from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver

from .data_obj import ResponseError, SylphDataGenerator, SylphDataDict
from .sylphsession import SylphSessionConfig, SylphSession


class BaseTestWrapper:
    """
    Provides logging, webdriver and sylph details
    """

    log: logging.LoggerAdapter
    config: SylphSessionConfig

    def __init__(self, sylph: SylphSession):
        self._external_test_id = None
        executing_test = self._get_calling_test_from_stack()
        self._internal_test_name = executing_test.name

        for mark in executing_test.iter_markers(name="testrail"):
            self._external_test_id = mark.kwargs['ids'][0]

        self.config = sylph.config
        test_details = f'{self._internal_test_name}'

        if self._external_test_id:
            test_details = f'{self.external_test_id} | {test_details}'

        adapter = CustomAdapter(sylph.log, {'test_details': test_details})
        self.log = adapter

    @property
    def external_test_id(self):
        return self._external_test_id

    @property
    def internal_test_name(self):
        return self._internal_test_name

    def _get_calling_test_from_stack(self, skip=5):
        def stack_(frame):
            framelist = []
            while frame:
                framelist.append(frame)
                frame = frame.f_back
            return framelist

        stack = stack_(sys._getframe(1))
        start = 0 + skip
        if len(stack) < start + 1:
            return ''
        parentframe = stack[start]

        try:
            fn_list = parentframe.f_locals['args']
            caller = fn_list[1]._pyfuncitem
        except:  # this is a unittest todo or a test with no eternal ID?
            caller = parentframe.f_locals['kwargs']['pyfuncitem']

        pytest_current_test = os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]
        if caller.name != pytest_current_test:
            raise ReferenceError(f'{caller.name} does not match PYTEST_CURRENT_TEST: {pytest_current_test}')

        return caller


class WebTestWrapper(BaseTestWrapper):
    def __init__(self, sylph: SylphSession, driver: SeleniumDriver):
        super().__init__(sylph)
        self.driver = driver


class MobileTestWrapper(BaseTestWrapper):
    def __init__(self, sylph: SylphSession, driver: AppiumDriver):
        super().__init__(sylph)
        self.driver = driver


class ApiTestWrapper(BaseTestWrapper):
    def __init__(self, sylph: SylphSession):
        super().__init__(sylph)
        self.driver = SylphApiDriver(sylph.config, sylph.log)


class CustomAdapter(logging.LoggerAdapter):
    """
    This adapter expects the passed in dict-like object to have a
    'test_details' key, whose value in brackets is prepended to the log message.
    """

    def process(self, msg, kwargs):
        return '%s | %s' % (self.extra['test_details'], msg), kwargs


class SylphApiDriver:
    response_error: ResponseError
    log: logging.Logger

    def __init__(self, config, log):
        # We do not intend to conduct security testing of the API with this driver
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._config = config
        self.log = log
        self._method = None
        self._base_url = None
        self._target = None
        self._headers = None
        self._data = None

        self.contract_error = None

    @property
    def config(self) -> SylphSessionConfig:
        return self._config

    @property
    def method(self):
        return self._method

    @property
    def target(self):
        return self._target

    @property
    def base_url(self):
        return self._base_url

    def send_request(self, method, url, data=None, params=None, token=None, headers=None):
        headers = headers if headers else {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        import json
        import requests
        payload = {} if data is None else json.dumps(data)

        try:
            self._method = method
            self._base_url = f"{url.split('com')[-1]}.com"
            self._target = url.split('com')[-1]
            self._headers = headers
            self._data = data

            response = requests.request(method, url, headers=headers, data=payload, verify=False, params=params)

            if not response.ok:
                self.response_error = ResponseError(response=response)
                self.log.warning(
                    f'API Client - Error: '
                    f'{self.response_error.status_code} - {self.response_error.reason}'
                )
                if response.text:
                    self.log.info(response.text)
        except Exception as exc:
            if len(exc.args) > 0:
                msg = exc.args[0]
                data_source = SylphDataGenerator.API_REQUEST
            else:
                msg = sys.exc_info()[0]
                data_source = SylphDataGenerator.AUTOMATION_CODE

            err_data = {"errorCode": "UNEXPECTED_ERROR", "errorMessage": msg}
            err_dict = SylphDataDict(data_source=data_source, data=err_data)
            self.response_error = ResponseError(data=err_dict)
            self.log.warning(f'API Client - Error: {msg}')
            response = self.response_error

        if hasattr(response, 'elapsed'):
            self.log.debug(f'API Client - Response Elapsed: {response.elapsed}')

        return response

    def process_contract_exception(self, exc):
        msg = exc.args[0]
        data_source = SylphDataGenerator.API_REQUEST
        err_data = {"errorCode": f"{exc.__class__.__name__}", "errorMessage": msg}
        err_dict = SylphDataDict(data_source=data_source, data=err_data)
        self.contract_error = ResponseError(data=err_dict)
        self.log.warning(f'API Client - {exc.__class__.__name__}: {msg}')
