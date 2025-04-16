import enum
import time
import logging
from abc import ABCMeta, abstractmethod

from appium.webdriver.webdriver import WebDriver as AppiumDriver
from playwright.sync_api import Playwright, Browser, Page
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver

from .sylphsession import SylphSessionConfig
from .wrappers import WebTestWrapper, PwTestWrapper
from .wrappers import MobileTestWrapper


class ViewSection(enum.Enum):
    UPPER = 25
    MIDDLE = 50
    LOWER = 75


class BasePagePw:
    def __init__(self, web_pw: PwTestWrapper):
        self.driver: Playwright = web_pw.driver
        self.browser: Browser = web_pw.browser
        self.page: Page = web_pw.page
        self.log = web_pw.log
        self.config = web_pw.config

        self.console_errors = []
        self.page_errors = []
        self.traffic_errors = []

        self.page.on('console', lambda msg: self.console_errors.append(msg.text) if msg.type == 'error' else None)
        self.page.on('pageerror', lambda msg: self.page_errors.append(msg.text) if msg.type == 'error' else None)
        self.page.on('response', lambda resp: self.traffic_errors.append(resp) if resp.status >= 400 else None)


class BasePageSe(metaclass=ABCMeta):
    log: logging.Logger
    config: SylphSessionConfig

    SWIPE_UP = 'up'
    SWIPE_DOWN = 'down'
    SWIPE_LEFT = 'left'
    SWIPE_RIGHT = 'right'

    def __init__(self, tw):
        self.config = tw.config
        self.log = tw.log
        self.page_name = self.__class__.__name__

    @abstractmethod
    def _locator(self, *args):
        pass

    def _is_done_loading(self, locator_elem) -> bool:
        self.log.info(f'{self.page_name} is loading...')
        is_ready = self.is_element_available(locator_elem)
        if is_ready:
            self.log.info(f'{self.page_name} is available')
        return is_ready

    def _get_elem_name(self, locator):
        try:
            page_name = locator.__closure__[0].cell_contents.page_name
            element = locator.__code__.co_names[0]
            return f'{page_name}.{element}'
        except:
            return None

    def is_element_available(self, elem, wait=30) -> bool:
        """Repeated safe check for the specified wait time (seconds) until the element is displayed and enabled.
           If not found, return false.

        Args:
            :param elem: A lambda function that returns a webelement.
            :param wait: (Default:10) The wait time in seconds for the process to complete.
            :param name: (Optional) A name describing the webelement for logging purposes.

        Returns:
            True if element is displayed.

        """
        name = self._get_elem_name(elem)
        if not name:
            name = self.page_name
        e = None
        beginning = time.time()
        for w in range(0, wait):

            try:
                e = elem()
                action_displayed = e.is_displayed
                action_enabled = e.is_enabled
                if action_displayed() and action_enabled() is True:
                    break
            except:
                pass

            time.sleep(1)
            since = time.time()
            span = self.span(since, beginning)

            span_msg = f'Elapsed seconds: {span}'
            wait_msg = f'Waiting for: {name} | {span_msg}'
            self.log.info(wait_msg)

            if span >= wait:
                wait_msg = f'{name} not found'
                self.log.info(wait_msg)
                return False

        try:
            coords = e.rect
        except:
            coords = 'Coordinates unavailable'

        msg = f'Found {name}: {coords}'
        self.log.info(msg)
        return True

    def wait_for_condition(self, condition, wait=10):
        """Process an action repeatedly for the specified wait time (seconds) until it returns true.

        Args:
            :param condition: A function that returns a bool.
            :param wait: The wait time for the process to complete.

         Throws:
            TimeoutError if the action is not true within the specified wait time (seconds)
        """
        beginning = time.time()
        for w in range(0, wait):

            try:
                if condition() is True:
                    break
            except:
                pass

            time.sleep(1)
            since = time.time()
            span = self.span(since, beginning)
            action_name = condition.__name__

            if hasattr(condition, '__self__'):
                container_name = condition.__self__.__class__.__name__
                self.log.debug(f'Waiting for {container_name}.{action_name}() | Elapsed seconds: {span}')
            else:
                self.log.debug(f'Waiting for {action_name}() | Elapsed seconds: {span}')

            if span >= wait:
                self.log.debug(f'Condition was not met: Elapsed seconds: {span}')
                raise TimeoutError('The condition was not met within the expected time span.')

    def span(self, since, beginning):
        """Calculate an integral span.

        Args:
            :param since: The end point since beginning.
            :param beginning: The beginning.

        Returns:
            The absolute span between two numbers as an integer.
        """
        span = beginning - since
        return abs(int(f"{span:.0f}"))


class BasePageWeb(BasePageSe):
    driver: SeleniumDriver

    def __init__(self, tw: WebTestWrapper, locator_elem, with_validation):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver

        if with_validation and not self._is_done_loading(locator_elem):
            raise Exception("Web.PAGE_LOAD")


class BasePageMobile(BasePageSe):
    driver: AppiumDriver

    def __init__(self, tw: MobileTestWrapper, locator_elem, with_validation):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver

        if with_validation and not self._is_done_loading(locator_elem):
            raise Exception("App.PAGE_LOAD")

    def try_find_element(self, **kwargs):
        """
        :param kwargs: locator - A lambda for a property that returns a WebElement
        :param kwargs: swipe_action - A tuple containing coordinates and a duration

        Usage::\n
        locator (always required) should be a lambda for a property that returns a WebElement. swipe_action should
        be a tuple of coordinates and a duration - e.g:
            locator=lambda: self._start_btn, swipe_action=(1000, 800, 40, 800, 500)
        """
        locator = kwargs['locator']
        action = kwargs['swipe_action']
        max_swipes = kwargs['max_swipes'] if 'max_swipes' in kwargs else 6

        located = False
        attempts = 0
        while not located:
            attempts += 1
            self.log.info(f'Swiping...')
            self.driver.swipe(*action)

            located = self.is_element_available(lambda: locator(), 2)
            if attempts >= max_swipes:
                break

    def R_L_coords(self, duration=500, start_at: ViewSection = ViewSection.MIDDLE):
        """
        :return: coords to swipe screen from Right to Left (Horizontal)
        """
        h = Horizontal(self.config.is_ios, self.driver.get_window_size(), start_at)
        return h.startx, h.starty, h.endx, h.starty, duration

    def L_R_coords(self, duration=500, start_at: ViewSection = ViewSection.MIDDLE):
        """
        :return: coords to swipe screen from Left to Right (Horizontal)
        """
        h = Horizontal(self.config.is_ios, self.driver.get_window_size(), start_at)
        return h.endx, h.starty, h.startx, h.starty, duration

    def B_T_coords(self, duration=500, start_at: ViewSection = ViewSection.MIDDLE):
        """
        :return: coords to swipe screen from Bottom to Top (Vertical)
        """
        v = Vertical(self.config.is_ios, self.driver.get_window_size(), start_at)
        return v.startx, v.starty, v.startx, v.endy, duration

    def T_B_coords(self, duration=500, start_at: ViewSection = ViewSection.MIDDLE):
        """
        :return: coords to swipe screen from Top to Bottom (Vertical)
        """
        v = Vertical(self.config.is_ios, self.driver.get_window_size(), start_at)
        return v.startx, v.endy, v.startx, v.starty, duration


class Horizontal:
    def __init__(self, is_ios, window_size, start_at: ViewSection = ViewSection.MIDDLE):
        offset_s = 0.90 if is_ios else 0.70
        offset_e = 0.20 if is_ios else 0.30
        self.startx = int(window_size['width'] * offset_s)
        self.endx = int(window_size['width'] * offset_e)
        self.starty = int(window_size['height'] / 100 * start_at.value)


class Vertical:
    def __init__(self, is_ios, window_size, start_at: ViewSection = ViewSection.MIDDLE):
        offset_s = 0.60 if is_ios else 0.50
        offset_e = 0.15 if is_ios else 0.20
        self.starty = int(window_size['height'] * offset_s)
        self.endy = int(window_size['height'] * offset_e)
        self.startx = int(window_size['width'] / 100 * start_at.value)
