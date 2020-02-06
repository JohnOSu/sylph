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
        self.session.log.debug('Initialising selenium driver')

        test_execution_target = self.config.exec_target_server

        if self.config.is_chrome:
            self.driver = SeleniumDriver.Chrome()
        elif self.config.is_firefox:
            self.driver = SeleniumDriver.Firefox()
        else:
            raise Exception(f'Unsupported browser: {self.config.desired_capabilities["browser"]}')

        self.driver.implicitly_wait(10)
        self.driver.maximize_window()
