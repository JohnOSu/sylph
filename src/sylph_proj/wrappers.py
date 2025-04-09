import sys
import os
import logging
import traceback
from urllib.parse import urlparse

import urllib3
from appium.webdriver.webdriver import WebDriver as AppiumDriver
from requests import RequestException
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver
from tenacity import stop_after_attempt, wait_fixed, retry, retry_if_exception_type, \
    Retrying, _utils

from .data_obj import ResponseError, SylphDataGenerator, SylphDataDict, ContractViolation
from .sylphsession import SylphSessionConfig, SylphSession


logger = logging.getLogger(__name__)


def custom_before_sleep(retry_state):
    is_function = retry_state.fn
    exception = retry_state.outcome.exception()
    exception_value = f"{exception.__class__.__name__}: {exception}"

    if is_function:
        retry_object = _utils.get_callback_name(retry_state.fn)
    else:
        try:
            tb_value = traceback.format_exception(type(exception), value=exception, tb=exception.__traceback__)
            code_block_tb = tb_value[1].split("\n")[0]
            fn = code_block_tb.split()[-1]
            retry_object = f'Code Block in {fn}'
        except Exception:
            retry_object = 'Code Block in unidentified function'

    logger.log(
        logging.DEBUG,
        f"Retrying {retry_object} "
        f"in {retry_state.next_action.sleep} seconds "
        f"as it raised {exception_value}, "
        f"this is the {_utils.to_ordinal(retry_state.attempt_number)} time calling it."
    )


def retriable(max_retries=10, retry_interval=5, upon_exception=False, code_block=False):
    retriable_kwargs = {'stop': stop_after_attempt(max_retries),
                        'wait': wait_fixed(retry_interval),
                        'before_sleep': custom_before_sleep
                        }

    if upon_exception:
        retriable_kwargs['retry'] = retry_if_exception_type(RetryTrigger)

    if code_block:
        # Tenacity class to retry a block of code
        return Retrying(**retriable_kwargs)
    else:
        return retry(**retriable_kwargs)


class RetryTrigger(Exception):
    pass


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

    def cleanup(self):
        if hasattr(self.config, "override_cleanup"):
            self.log.info(f'Test cleanup override: {getattr(self.config, "override_cleanup")}')


class PwTestWrapper(BaseTestWrapper):
    def __init__(self, sylph: SylphSession):
        super().__init__(sylph)
        self.driver = None
        self.browser = None
        self.page = None


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
        self._files = None

        # init empty ContractViolation instance
        err_data = {"dto_name": None, "dto_path": None, "dto_exc": None}
        err_dict = SylphDataDict(data_source=SylphDataGenerator.AUTOMATION_CODE, data=err_data)
        self.contract_error = ContractViolation(data=err_dict)

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

    def validate_contract(self):
        assertion = f'Contract is valid : {self.method} {self.target}'
        dto_name = self.contract_error.dto_name if self.contract_error.dto_name else None
        if dto_name:
            msg = f'{self.contract_error.dto_name} {self.contract_error.dto_exc}'
        else:
            msg = self.contract_error.dto_exc
        label = 'Issue:'
        assert self.contract_error.dto_exc is None, f'{self.method} {self.target}\n{label: >15} {msg}'

        self.log.info(assertion)

    def send_request(self, method, url,
                     data=None, files=None, params=None, token=None, headers=None,
                     validate_json=True, verbose=True, timeout=30):
        # init empty ContractViolation instance
        err_data = {"dto_name": None, "dto_path": None, "dto_exc": None}
        err_dict = SylphDataDict(data_source=SylphDataGenerator.AUTOMATION_CODE, data=err_data)
        self.contract_error = ContractViolation(data=err_dict)

        headers = headers if headers else {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'{token}'

        import json
        import requests
        payload = data if data else {}

        uri = urlparse(url)

        try:
            self._method = method
            self._base_url = f'{uri.scheme}://{uri.netloc}'
            self._target = uri.path
            self._headers = headers
            self._data = data
            self._files = files

            response = requests.request(method, url,
                                        headers=headers, data=payload, files=files, verify=False, params=params,
                                        timeout=timeout)

            if not response.ok:
                self.response_error = ResponseError(response=response)
                self.log.warning(
                    f'API Client - Error: '
                    f'{self.response_error.status_code} - {self.response_error.reason}'
                )
                if hasattr(response, 'text'):
                    self.log.info(response.text)
        except RequestException as exc:
            data_source = SylphDataGenerator.API_REQUEST
            err = type(exc).__name__
            msg = f'{exc.request.url}\n{exc.args[0].args[0]}'

            err_data = {"errorCode": err, "errorMessage": msg}
            err_dict = SylphDataDict(data_source=data_source, data=err_data)
            self.response_error = ResponseError(data=err_dict)
            self.log.warning(f'API Client - {err}: {msg}')
            response = self.response_error

        if verbose and hasattr(response, 'request') and hasattr(response.request, 'body'):
            self.log.debug(f'HEADERS: {response.request.headers}')
            self.log.debug(f'PAYLOAD: {response.request.body}')

        if hasattr(response, 'elapsed'):
            self.log.debug(f'ELAPSED: {response.elapsed}')

        # handler to trap responses that are not valid json dictionaries
        if response.ok and validate_json and len(response.content) > 0:
            try:
                src = json.loads(response.content.decode('utf-8'))

                if isinstance(src, list):
                    src = src[0]
                if not isinstance(src, dict):
                    raise Exception(f'Response content is not a dictionary: {src}')
            except Exception as exc:
                self.process_contract_exception(exc)

        return response

    def process_contract_exception(self, exc, dto=None):
        err = type(exc).__name__
        dto_name = getattr(dto, '__name__') if dto else None
        dto_path = str(dto).split()[-1][1:-2] if dto else None
        dto_exc = f'{err}: {exc.args[0]}'

        msg = f'{dto_name} {dto_exc}' if dto_name else dto_exc

        data_source = SylphDataGenerator.API_REQUEST
        err_data = {"dto_name": dto_name, "dto_path": dto_path, "dto_exc": dto_exc}
        err_dict = SylphDataDict(data_source=data_source, data=err_data)
        self.contract_error = ContractViolation(data=err_dict)

        self.log.warning(f'API Client - {msg}')


class SylphApiClient:
    driver: SylphApiDriver
    log: logging.Logger

    def __init__(self, driver: SylphApiDriver):
        self.driver = driver
        self.log = self.driver.log

    def get(self, **kwargs):
        return self.driver.send_request(method='GET', **kwargs)

    def put(self, **kwargs):
        return self.driver.send_request(method='PUT', **kwargs)

    def post(self, **kwargs):
        return self.driver.send_request(method='POST', **kwargs)

    def delete(self, **kwargs):
        return self.driver.send_request(method='DELETE', **kwargs)

    def patch(self, **kwargs):
        return self.driver.send_request(method='PATCH', **kwargs)

    def head(self, **kwargs):
        return self.driver.send_request(method='HEAD', **kwargs)

    def options(self, **kwargs):
        return self.driver.send_request(method='OPTIONS', **kwargs)

    def trace(self, **kwargs):
        return self.driver.send_request(method='TRACE', **kwargs)

    def deserialize(self, response, dto):
        if response.ok or hasattr(response, 'status_code'):
            try:
                response_obj = dto(response=response)
                return response_obj
            except Exception as exc:
                self.driver.process_contract_exception(exc, dto)

    def validate_contract(self):
        self.driver.validate_contract()
