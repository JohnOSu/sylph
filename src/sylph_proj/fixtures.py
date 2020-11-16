import os
import pytest
import time
from datetime import datetime
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
def appdriver(sylph, request) -> AppiumDriver:
    appdriver = AppiumDriverFactory(sylph).driver
    yield appdriver

    if request.node.rep_setup.failed:
        sylph.log.warning(f'TEST SETUP FAIL: {request.node.nodeid}')
    elif request.node.rep_setup.passed:
        if request.node.rep_call.failed:
            driver = request.node.funcargs['appdriver']
            take_screenshot(sylph, driver, request.node.nodeid)

    appdriver.quit()
    sylph.log.debug('Appium Driver fixture cleanup...')


def take_screenshot(sylph, driver, nodeid):
    time.sleep(1)
    test_details = f'{nodeid}.png'.replace("::","*")
    file_name = test_details.split('*')[1]
    file_path = f'{sylph.project_path.parent}/{sylph.LOGGING_DIR}/{file_name}'
    sylph.log.warning(f'TEST FAIL | Screenshot saved as: {file_path}')
    driver.save_screenshot(file_path)


# set up a hook to be able to check if a test has failed
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    report = rep
    extra = getattr(report, 'extra', [])

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)

    if report.when == 'call':
        xfail = hasattr(report, 'wasxfail')
        if (report.skipped and xfail) or (report.failed and not xfail):
            report_directory = os.path.dirname(item.config.option.htmlpath)

            file_name = str(int(round(time.time() * 1000))) + ".png"

            test_details = f'{report.nodeid}.png'.replace("/", "_").replace("::", "*")
            file_name = test_details.split('*')[1]


            # full_path = os.path.join("C:\Screenshots", file_name)
            full_path = os.path.join(report_directory, file_name)
            if item.funcargs.get('appdriver'):
                #print(f"[INFO] screenshot: {full_path}")
                item.funcargs['appdriver'].get_screenshot_as_file(full_path)
                if file_name:
                    html = '<div><img src="%s" alt="screenshot" style="width:228px;height:304px;" ' \
                           'onclick="window.open(this.src)" align="right"/></div>' % file_name
                    extra.append(pytest_html.extras.html(html))
        report.extra = extra


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

