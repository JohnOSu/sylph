import pytest
from selenium import webdriver as SeleniumDriver
from appium import webdriver as AppiumDriver
from .sylphsession import SylphSession
from .factory import SeleniumDriverFactory
from .factory import AppiumDriverFactory
from .wrappers import WebTestWrapper, ApiTestWrapper
from .wrappers import MobileTestWrapper


@pytest.fixture(scope='session')
def sylph() -> SylphSession:
    sylph = SylphSession()
    yield sylph
    sylph.log.debug('Sylph Session fixture cleanup...')


@pytest.fixture(scope='function')
def appdriver(sylph) -> AppiumDriver:
    appdriver = AppiumDriverFactory(sylph).driver
    yield appdriver
    appdriver.quit()
    sylph.log.debug('Appium Driver fixture cleanup...')


@pytest.fixture(scope='function', name='app')
def appwrapper(sylph, appdriver) -> MobileTestWrapper:
    app = MobileTestWrapper(sylph, appdriver)
    yield app
    sylph.log.debug('App Test Wrapper fixture cleanup...')


@pytest.fixture(scope='function')
def webdriver(sylph) -> SeleniumDriver:
    webdriver = SeleniumDriverFactory(sylph).driver
    yield webdriver
    webdriver.quit()
    sylph.log.debug('Selenium Driver fixture cleanup...')


@pytest.fixture(scope='function', name='web')
def webwrapper(sylph, webdriver) -> WebTestWrapper:
    web = WebTestWrapper(sylph, webdriver)
    yield web
    sylph.log.debug('Web Test Wrapper fixture cleanup...')


@pytest.fixture(scope='function')
def api(sylph):
    wrapper = ApiTestWrapper(sylph)
    yield wrapper
    sylph.log.debug('Api Test Wrapper fixture cleanup...')

