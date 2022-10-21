# from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium import webdriver

from .sylphsession import SylphSession, SylphSessionConfig
from selenium import webdriver as SeleniumDriver
from appium import webdriver as AppiumDriver


class RemoteWebDriverFactory:
    session: SylphSession
    config: SylphSessionConfig

    def __init__(self, session):
        self.session = session
        self.config = session.config


class AppiumDriverFactory(RemoteWebDriverFactory):
    driver: AppiumDriver

    def __init__(self, session):
        super().__init__(session)
        self.session.log.debug('Initialising appium driver')
        desired_caps = self.config.desired_capabilities
        test_execution_target = self.config.exec_target_server
        self.driver = AppiumDriver.Remote(test_execution_target, desired_caps)


class SeleniumDriverFactory(RemoteWebDriverFactory):
    driver: SeleniumDriver

    def __init__(self, session):
        super().__init__(session)
        platform = self.config.desired_capabilities['platform']
        is_linux = platform.lower() in 'linux'
        is_grid_test = True if self.config.exec_target_server else False
        if not isinstance(self.config.desired_capabilities['is_headless'], bool):
            if self.config.desired_capabilities['is_headless'].lower() in ['true', '1', 'y', 'yes']:
                is_headless = True
            else:
                is_headless = False
        else:
            is_headless = self.config.desired_capabilities['is_headless']

        if self.config.is_chrome:
            init_msg = 'Initialising Selenium driver (Chrome)'
        else:
            raise NotImplementedError('This version of sylph supports only Chrome')

        if is_grid_test:
            chrome_options = webdriver.ChromeOptions()
            if is_headless:
                init_msg = f'{init_msg[:-1]} - Headless)'
                chrome_options.add_argument("--headless")
            if is_linux:
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")

            self.session.log.debug(f'{init_msg} on {platform.upper()} for remote grid testing...')
            self.driver = webdriver.Remote(
                command_executor=self.config.exec_target_server,
                options=chrome_options
            )
        else:
            self.session.log.debug(f'{init_msg} on {platform} for local testing...')
            self.driver = SeleniumDriver.Chrome()

        self.driver.implicitly_wait(10)
        self.driver.maximize_window()
