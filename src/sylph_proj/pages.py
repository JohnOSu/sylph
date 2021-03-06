import time
import logging
from abc import ABCMeta, abstractmethod

from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver

from .sylphsession import SylphSessionConfig
from .wrappers import WebTestWrapper
from .wrappers import MobileTestWrapper


class BasePage(metaclass=ABCMeta):
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
        is_ready = self.is_element_available(locator_elem, name=self.page_name)
        if is_ready:
            self.log.info(f'{self.page_name} is available')
        return is_ready

    def is_element_available(self, elem, wait=30, name=None) -> bool:
        """Repeated safe check for the specified wait time (seconds) until the element is displayed and enabled.
           If not found, return false.

        Args:
            :param elem: A lambda function that returns a webelement.
            :param wait: (Default:10) The wait time in seconds for the process to complete.
            :param name: (Optional) A name describing the webelement for logging purposes.

        Returns:
            True if element is displayed.

        """
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
            wait_msg = f'Waiting for {name}'
            wait_msg = f'{wait_msg}: {name} | {span_msg}' if name else f'{wait_msg}. | {span_msg}'
            self.log.debug(wait_msg)

            if span >= wait:
                wait_msg = f'{name} not found' if name else 'Element not found'
                self.log.debug(wait_msg)
                return False

        msg = 'Found Element'
        self.log.debug(f'{msg}: {e.id}' if e else msg)
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


class BasePageWeb(BasePage):
    driver: SeleniumDriver

    def __init__(self, tw: WebTestWrapper, locator_elem, with_validation):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver

        if with_validation and not self._is_done_loading(locator_elem):
            raise Exception("Web.PAGE_LOAD")


class BasePageMobile(BasePage):
    driver: AppiumDriver

    def __init__(self, tw: MobileTestWrapper, locator_elem, with_validation):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver

        if with_validation and not self._is_done_loading(locator_elem):
            raise Exception("App.PAGE_LOAD")

    def try_find_element(self, locator, max_swipes=6, swipe_dir=BasePage.SWIPE_UP, name=None):
        """Repeated swipe action (default:up) for the specified number of attempts or until the element is found.
           If not found, no consequences.

        Args:
            :param locator: A lambda function that returns a webelement.
            :param max_swipes: The max number of swipes to attempt
            :param swipe_dir: 'up' to reveal elements below, 'down' to reveal elements above
            :param name: (Optional) A name describing the webelement for logging purposes.
        """
        located = self.is_element_available(lambda: locator(), 2, name)
        attempts = 0
        while not located:
            attempts +=1
            self.log.info(f'Swiping: {swipe_dir}')
            if swipe_dir is BasePage.SWIPE_UP:
                self.swipe_up()
            elif swipe_dir is BasePage.SWIPE_DOWN:
                self.swipe_down()
            elif swipe_dir is BasePage.SWIPE_LEFT:
                self.swipe_left()
            else:
                self.swipe_right()

            located = self.is_element_available(lambda: locator(), 2, name)
            if attempts >= max_swipes:
                break

    def swipe_up(self):
        if self.config.is_ios:
            self.driver.swipe(50, 350, 50, 310, 400)
        else:
            self.driver.swipe(100, 1000, 100, 845, 400)

    def swipe_down(self):
        if self.config.is_ios:
            self.driver.swipe(50, 310, 50, 350, 400)
        else:
            self.driver.swipe(100, 845, 100, 1000, 400)

    def swipe_left(self):
        if self.config.is_ios:
            self.driver.swipe(300, 250, 80, 250, 400)
        else:
            self.driver.swipe(600, 800, 500, 800, 400)

    def swipe_right(self):
        if self.config.is_ios:
            self.driver.swipe(80, 250, 300, 250, 400)
        else:
            self.driver.swipe(500, 800, 600, 800, 400)
