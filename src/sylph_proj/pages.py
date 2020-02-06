import time
import logging
from appium.webdriver.webdriver import WebDriver as AppiumDriver
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumDriver
from .sylphsession import SylphSessionConfig
from .wrappers import WebTestWrapper
from .wrappers import MobileTestWrapper


class BasePage:
    log: logging.Logger
    config: SylphSessionConfig

    SWIPE_UP = 'up'
    SWIPE_DOWN = 'down'

    def __init__(self, tw):
        self.config = tw.config
        self.log = tw.log
        self.log.debug(f'{self.__class__.__name__} initialiser connected to {self.log.name} logger')

    def is_element_displayed(self, elem, wait=10) -> bool:
        """Repeated safe check for the specified wait time (seconds) until the element is displayed.
           If not found, return false.

        Args:
            :param elem: A lambda function that returns a webelement.
            :param wait: The wait time for the process to complete.

        Returns:
            True if element is displayed.

        """
        beginning = time.time()
        for w in range(0, wait):

            try:
                e = elem()
                action = e.is_displayed
                if action() is True:
                    break
            except:
                pass

            time.sleep(1)
            since = time.time()
            span = self.span(since, beginning)
            self.log.debug(f'Waiting for element | Elapsed seconds: {span}')

            if span >= wait:
                self.log.debug(f'Element was not found: Elapsed seconds: {span}')
                return False

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

    def __init__(self, tw: WebTestWrapper):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver


class BasePageMobile(BasePage):
    driver: AppiumDriver

    def __init__(self, tw: MobileTestWrapper):
        self._tw = tw
        super().__init__(tw)
        self.driver = tw.driver

    def try_find_element(self, locator, max_swipes=3, swipe_dir=BasePage.SWIPE_UP):
        """Repeated swipe action (default:up) for the specified number of attempts or until the element is found.
           If not found, no consequences.

        Args:
            :param locator: A lambda function that returns a webelement.
            :param max_swipes: The max number of swipes to attempt
            :param swipe_dir: 'up' to reveal elements below, 'down' to reveal elements above
        """
        located = False
        attempts = 0
        while not located:
            attempts +=1
            self.swipe_up() if swipe_dir is BasePage.SWIPE_UP else self.swipe_down()
            located = self.is_element_displayed(lambda: locator(), 2)
            if attempts >= max_swipes:
                break

    def swipe_up(self):
        if self.config.is_ios:
            self.driver.swipe(50, 350, 50, 290, 1000)
        else:
            self.driver.swipe(100, 1000, 100, 845, 1000)

    def swipe_down(self):
        if self.config.is_ios:
            self.driver.swipe(50, 290, 50, 350, 1000)
        else:
            self.driver.swipe(100, 845, 100, 1000, 1000)
