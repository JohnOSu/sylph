import sys
import os
import logging
from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver
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
    def __init__(self, sylph: SylphSession, client):
        super().__init__(sylph)
        self.client = client


class CustomAdapter(logging.LoggerAdapter):
    """
    This adapter expects the passed in dict-like object to have a
    'test_details' key, whose value in brackets is prepended to the log message.
    """

    def process(self, msg, kwargs):
        return '%s | %s' % (self.extra['test_details'], msg), kwargs
