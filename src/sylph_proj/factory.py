from selenium import webdriver

from .sylphsession import SylphSession, SylphSessionConfig
from selenium import webdriver as SeleniumDriver
from appium import webdriver as AppiumDriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions


class RemoteWebDriverFactory:
    session: SylphSession
    config: SylphSessionConfig

    def __init__(self, session):
        self.session = session
        self.config = session.config

    def get_bool_cfg_value(self, cfg_key):
        if not isinstance(self.config.desired_capabilities[cfg_key], bool):
            return str(self.config.desired_capabilities[cfg_key]).lower() in ['true', '1', 'y', 'yes']
        else:
            return self.config.desired_capabilities[cfg_key]


class AppiumDriverFactory(RemoteWebDriverFactory):
    driver: AppiumDriver

    def __init__(self, session):
        super().__init__(session)
        self.session.log.debug('Setting deviceName capability from platformName')
        target = self.config.desired_capabilities['platformName']
        self.config.desired_capabilities['deviceName'] = target

        if self.config.is_ios:
            target = f'{target[0]}{target[1:3].upper()}'
            automationName = 'xcuitest'
            opts = XCUITestOptions().load_capabilities(self.config.desired_capabilities)
        elif self.config.is_android:
            target = target.capitalize()
            automationName = 'uiautomator2'
            opts = UiAutomator2Options().load_capabilities(self.config.desired_capabilities)
        else:
            raise Exception('Unsupported platform')

        self.session.log.debug(f'Initialising appium {automationName} driver for {target} testing...')
        test_execution_target = self.config.exec_target_server
        self.driver = AppiumDriver.Remote(test_execution_target, options=opts)


class SeleniumDriverFactory(RemoteWebDriverFactory):
    driver: SeleniumDriver

    def __init__(self, session):
        super().__init__(session)

        import logging
        from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
        seleniumLogger.setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        platform = self.config.desired_capabilities['platform']
        is_linux = platform.lower() in 'linux'
        is_grid_test = True if self.config.exec_target_server else False
        is_headless = self.get_bool_cfg_value('is_headless')

        init_msg = 'Initialising Selenium driver'
        if self.config.is_chrome:
            init_msg = f'{init_msg} (Chrome)'
            self.driver = self._get_chrome_driver(is_grid_test, is_linux, is_headless, platform, init_msg)
        elif self.config.is_firefox:
            init_msg = f'{init_msg} (Firefox)'
            self.driver = self._get_firefox_driver(is_grid_test, is_linux, is_headless, platform, init_msg)
        elif self.config.is_safari:
            init_msg = f'{init_msg} (Safari)'
            self.driver = self._get_safari_driver(is_grid_test, is_headless, platform, init_msg)
        elif self.config.is_edge:
            init_msg = f'{init_msg} (Edge)'
            self.driver = self._get_edge_driver(is_grid_test, is_linux, is_headless, platform, init_msg)
        else:
            raise NotImplementedError(f'This version of sylph does not support '
                                      f'{self.config.desired_capabilities["browser"]}')

        self.driver.implicitly_wait(10)
        if is_headless:
            self.session.log.debug(f'Browser Window: {self.driver.get_window_size()}')
            return
        else:
            self.driver.maximize_window()
        # In my setup, this is necessary to ensure the chrome instance on my desired monitor is within bounds
        if self.config.is_chrome and not is_grid_test:
            # the previous maximise moves the chrome window to monitor 1 which is smaller than my dev monitor
            self.driver.maximize_window()

        self.session.log.debug(f'Browser Window: {self.driver.get_window_size()}')

    def _get_chrome_driver(self, is_grid_test, is_linux, is_headless, platform, init_msg):
        if is_grid_test:
            chrome_options = webdriver.ChromeOptions()
            if is_headless:
                init_msg = f'{init_msg[:-1]} - Headless)'
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--window-size=1920,1080")
            if is_linux:
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")

            self.session.log.debug(f'{init_msg} on {platform.upper()} for remote grid testing...')
            return self.retry_get_remote_wd(init_msg, lambda: webdriver.Remote(
                command_executor=self.config.exec_target_server,
                options=chrome_options)
            )

        if is_headless:
            self.session.log.debug('Headless driver is not supported for local testing.')
        self.session.log.debug(f'{init_msg} on {platform.upper()} for local testing...')
        return SeleniumDriver.Chrome()

    def _get_firefox_driver(self, is_grid_test, is_linux, is_headless, platform, init_msg):
        if is_grid_test:
            firefox_options = webdriver.FirefoxOptions()
            if is_headless:
                init_msg = f'{init_msg[:-1]} - Headless)'
                firefox_options.add_argument("--headless")
                firefox_options.add_argument("--width=1920")
                firefox_options.add_argument("--height=1080")
            if is_linux:
                firefox_options.add_argument("--no-sandbox")
                firefox_options.add_argument("--disable-dev-shm-usage")

            self.session.log.debug(f'{init_msg} on {platform.upper()} for remote grid testing...')
            return self.retry_get_remote_wd(init_msg, lambda: webdriver.Remote(
                command_executor=self.config.exec_target_server,
                options=firefox_options)
            )

        if is_headless:
            self.session.log.debug('Headless driver is not supported for local testing.')
        self.session.log.debug(f'{init_msg} on {platform.upper()} for local testing...')
        return SeleniumDriver.Firefox()

    def _get_safari_driver(self, is_grid_test, is_headless, platform, init_msg):
        from selenium.webdriver.safari.options import Options
        platform = platform if platform else 'mac'

        if is_grid_test:
            safari_options = Options()
            if is_headless:
                init_msg = 'Safari (Headless) driver is not supported.'
                raise NotImplementedError(init_msg)
            if platform.lower() not in ['mac', 'macos', 'apple']:
                init_msg = f'Safari driver on {platform.upper()} is not supported.'
                raise NotImplementedError(init_msg)

            self.session.log.debug(f'{init_msg} on MAC for remote grid testing...')
            return self.retry_get_remote_wd(init_msg, lambda: webdriver.Remote(
                command_executor=self.config.exec_target_server,
                options=safari_options)
            )

        if is_headless:
            self.session.log.debug('Safari (Headless) driver is not supported.')
        self.session.log.debug(f'{init_msg} on {platform.upper()} for local testing...')
        return SeleniumDriver.Safari()

    def _get_edge_driver(self, is_grid_test, is_linux, is_headless, platform, init_msg):
        if is_grid_test:
            edge_options = webdriver.EdgeOptions()
            if is_headless:
                init_msg = f'{init_msg[:-1]} - Headless)'
                edge_options.add_argument("--headless=new")
                edge_options.add_argument("--window-size=1920,1080")
            if is_linux:
                edge_options.add_argument("--no-sandbox")
                edge_options.add_argument("--disable-dev-shm-usage")

            self.session.log.debug(f'{init_msg} on {platform.upper()} for remote grid testing...')
            return self.retry_get_remote_wd(init_msg, lambda: webdriver.Remote(
                command_executor=self.config.exec_target_server,
                options=edge_options)
            )

        if is_headless:
            self.session.log.debug('Headless driver is not supported for local testing.')
        self.session.log.debug(f'{init_msg} on {platform.upper()} for local testing...')
        return SeleniumDriver.Edge()

    def retry_get_remote_wd(self, init_msg, action):
        is_headless = self.get_bool_cfg_value('is_headless')
        nm_arr = init_msg.split()
        from . import RetryTrigger
        rd_name = f'{nm_arr[-3]} {nm_arr[-2]} {nm_arr[-1]}' if is_headless else nm_arr[-1]
        for attempt in self.retriable():
            with attempt:
                try:
                    r_wd = action()
                except Exception as exc:
                    msg = f'{type(exc).__name__} | Cannot create session: {rd_name}.'
                    self.session.log.info(msg)
                    raise RetryTrigger(msg)

                self.session.log.info(f'***DESIRED CAPABILITIES - {rd_name}***')
                for k, v in r_wd.desired_capabilities.items():
                    self.session.log.info(f'{k}: {v}')
                return r_wd

    def retriable(self, max_retries=2, retry_interval=30, upon_exception=True, code_block=True):
        from . import RetryTrigger
        from tenacity import stop_after_attempt, wait_fixed, retry, retry_if_exception_type, \
            Retrying
        retriable_kwargs = {'stop': stop_after_attempt(max_retries),
                            'wait': wait_fixed(retry_interval),
                            'before_sleep': None
                            }

        if upon_exception:
            retriable_kwargs['retry'] = retry_if_exception_type(RetryTrigger)

        if code_block:
            # Tenacity class to retry a block of code
            return Retrying(**retriable_kwargs)
        else:
            return retry(**retriable_kwargs)
