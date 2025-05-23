import pytest
import time

from selenium import webdriver as SeleniumDriver
from appium import webdriver as AppiumDriver

from . import PwTestWrapper, PlaywrightInstanceFactory
from .sylphsession import SylphSession
from .factory import SeleniumDriverFactory
from .factory import AppiumDriverFactory
from .wrappers import WebTestWrapper, ApiTestWrapper
from .wrappers import MobileTestWrapper


@pytest.fixture(scope='session')
def sylph() -> SylphSession:
    sylph = SylphSession()
    yield sylph


@pytest.fixture(scope='function')
def appdriver(sylph, request) -> AppiumDriver:
    appdriver = AppiumDriverFactory(sylph).driver
    yield appdriver

    if request.node.rep_setup.failed:
        sylph.log.warning(f'TEST SETUP FAIL: {request.node.nodeid}')
    elif request.node.rep_setup.passed:
        xfail = hasattr(request.node.rep_call, 'wasxfail')
        need_screenshot = True if xfail or request.node.rep_call.failed else False
        if need_screenshot:
            take_screenshot(sylph, appdriver, request.node.nodeid)
        if request.node.rep_call.failed:
            sylph.log.info(f'Page Source:\n{appdriver.page_source}\n')

    appdriver.quit()


@pytest.fixture(scope='function', name='app')
def appwrapper(sylph, appdriver) -> MobileTestWrapper:
    app = MobileTestWrapper(sylph, appdriver)
    yield app
    app.cleanup()


@pytest.fixture(name='web_pw')
def playwright_wrapper(playwright, sylph, request):
    web_pw = PwTestWrapper(sylph)
    web_pw.log.debug('Initialising Playwright Sync API')

    PlaywrightInstanceFactory.initialise(web_pw, playwright)

    yield web_pw

    if request.node.rep_setup.failed:
        sylph.log.warning(f'TEST SETUP FAIL: {request.node.nodeid}')
    elif request.node.rep_setup.passed:
        xfail = hasattr(request.node.rep_call, 'wasxfail')
        need_screenshot = True if xfail or request.node.rep_call.failed else False
        if need_screenshot:
            driver = request.node.funcargs['web_pw']
            take_screenshot(sylph, driver, request.node.nodeid)

    web_pw.page.close()
    web_pw.browser.close()


@pytest.fixture(scope='function')
def webdriver(sylph, request) -> SeleniumDriver:
    webdriver = SeleniumDriverFactory(sylph).driver
    yield webdriver

    if request.node.rep_setup.failed:
        sylph.log.warning(f'TEST SETUP FAIL: {request.node.nodeid}')
    elif request.node.rep_setup.passed:
        xfail = hasattr(request.node.rep_call, 'wasxfail')
        need_screenshot = True if xfail or request.node.rep_call.failed else False
        if need_screenshot:
            driver = request.node.funcargs['webdriver']
            take_screenshot(sylph, driver, request.node.nodeid)

    webdriver.quit()
    sylph.log.debug('Selenium Driver fixture cleanup...')


@pytest.fixture(scope='function', name='web_se')
def webwrapper(sylph, webdriver):
    web_se = WebTestWrapper(sylph, webdriver)
    yield web_se
    web_se.cleanup()


@pytest.fixture(scope='function')
def api(sylph):
    wrapper = ApiTestWrapper(sylph)
    yield wrapper
    wrapper.cleanup()


# set up a hook to be able to check if a test has failed
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # get primary test case id
    tr_mark = [i for i in item.own_markers if i.name == 'testrail']
    if tr_mark:
        mark = tr_mark[0]
        rep.id = mark.kwargs['ids'][0]
    else:
        rep.id = 'No ID'

    # get test case defect id
    tr_mark = [i for i in item.own_markers if i.name == 'testrail_defects']
    if tr_mark:
        mark = tr_mark[0]
        rep.defect_id = mark.kwargs['defect_ids']
    else:
        rep.defect_id = ''

    extras = getattr(rep, 'extras', [])

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)

    # if fail, set override_cleanup as True
    if rep.when == 'call' and item.funcargs.get('sylph') and not rep.passed:
        cfg = item.funcargs['sylph'].config
        setattr(cfg, 'override_cleanup', True)
        stderr = rep.capstderr if rep.capstderr else 'No stderr message'
        msg = f'{rep.id} | {rep.head_line} | {stderr}'
        setattr(cfg, 'override_cleanup_reason', msg)

    is_mobile_ui = True if item.funcargs.get('appdriver') else False
    is_web_ui = True if item.funcargs.get('webdriver') else False
    is_web_pw_ui = True if item.funcargs.get('web_pw') else False

    if not is_mobile_ui and not is_web_ui and not is_web_pw_ui:
        return

    img_size = "width:150px;height:250px;" if is_mobile_ui else "width:512px;height:240px;"

    # if mobile or web ui fail, prepare html report to display screenshot
    if rep.when == 'call' and hasattr(item.config.option, 'htmlpath'):
        xfail = hasattr(rep, 'wasxfail')
        if (rep.skipped and xfail) or (rep.failed and not xfail):
            # inject the screenshot name
            test_details = f'{rep.nodeid}.png'.replace("/", "_").replace("::", "*")
            file_name = get_file_name(test_details)
            html = f'<div><img src="%s" alt="screenshot" style={img_size} ' \
                   'onclick="window.open(this.src)" align="right"/></div>' % file_name
            extras.append(pytest_html.extras.html(html))

        rep.extras = extras


# make a screenshot with a name of the test
def take_screenshot(sylph, driver, nodeid):
    time.sleep(1)
    test_details = f'{nodeid}.png'.replace("::","*")
    # handle parameterized tests
    file_name = get_file_name(test_details)
    file_path = f'{sylph.project_path.parent}/{sylph.LOGGING_DIR}/{file_name}'
    sylph.log.warning(f'TEST FAIL | Screenshot saved as: {file_path}')
    if isinstance(driver, PwTestWrapper):
        driver.page.screenshot(path=file_path)
    else:
        driver.save_screenshot(file_path)


def get_file_name(test_details):
    # handle parameterized tests
    file_name = test_details.split('*')[1]
    if '[' in file_name:
        file_name = file_name.replace('[', '*').replace(']', '*')
        file_name_arr = file_name.split('*')
        file_name = file_name_arr[0] + file_name_arr[-1]
    return file_name