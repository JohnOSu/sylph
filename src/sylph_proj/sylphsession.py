import os
import logging
from logging import Logger
import json
from pathlib import Path


class SylphSessionConfig:
    def __init__(self, data):
        self.geo: str = data['test_context']['geo'] if 'geo' in data['test_context'] else None
        self._engine: str = data['test_context']['engine']
        self.sut_url_override: str = data['test_context']['sut_url_override'] if 'sut_url_override' in data['test_context'] else None
        self._test_env: str = data['test_context']['test_env']
        self._exec_target_server: str = data['exec_target']['server']
        self._real_device = data['exec_target']['realDevice'] if 'realDevice' in data['exec_target'] else None
        self._browser: str = data['desired_caps']['browser'] if 'browser' in data['desired_caps'] else None
        self._platform: str = data['desired_caps']['platformName'] if 'platformName' in data['desired_caps'] else None
        self._desired_capabilities: dict = data['desired_caps']

    @property
    def environment(self) -> str:
        return self._test_env

    @property
    def is_api(self) -> bool:
        return self._engine.lower() == SylphSession.API

    @property
    def is_appium(self) -> bool:
        return self._engine.lower() == SylphSession.APPIUM

    @property
    def is_playwright(self) -> bool:
        return self._engine.lower() == SylphSession.PLAYWRIGHT

    @property
    def is_selenium(self) -> bool:
        return self._engine.lower() == SylphSession.SELENIUM

    @property
    def is_headless(self) -> bool:
        if 'is_headless' in self._desired_capabilities:
            return bool(self._desired_capabilities['is_headless'])
        return False

    @property
    def desired_capabilities(self) -> dict:
        return self._desired_capabilities

    @property
    def exec_target_server(self) -> str:
        return self._exec_target_server

    @property
    def is_chrome(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'chrome'

    @property
    def is_chromium(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'chromium'

    @property
    def is_webkit(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'webkit'

    @property
    def is_firefox(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'firefox'

    @property
    def is_safari(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'safari'

    @property
    def is_edge(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'edge'

    @property
    def is_android(self) -> bool:
        return False if self._platform is None else self._platform.lower() == 'android'

    @property
    def is_ios(self) -> bool:
        return False if self._platform is None else self._platform.lower() == 'ios'

    @property
    def is_real_device(self) -> bool:
        return self._real_device is True


class ConfigLoader:

    _log: Logger
    OVERRIDE_MSG = 'Environment override found:'

    def __init__(self, project_path, logger):
        self._project_path = project_path
        self._log = logger

    @property
    def data(self):
        return self._load_sylph_config()

    def _load_sylph_config(self):
        """
        Get the sylph config from json.
        If not found, get it from a template.
        Then check for os env overrides.
        :return:
        """
        try:
            config = Path(f'{self._project_path}/config/session_config.json')
            with open(config) as json_file:
                data = json.load(json_file)
        except FileNotFoundError:
            self._log.debug('No session_config.json found.')
            data = {}
        # now check for environment overrides
        data = self._get_sut_env_overrides(data)

        return data

    def _get_sut_env_overrides(self, data):
        if os.environ.get('GEO'):
            override = os.environ.get('GEO')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} GEO={override}")
            data['test_context']['geo'] = os.environ.get('GEO')

        if os.environ.get('ENGINE'):
            override = os.environ.get('ENGINE')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} ENGINE={override}")
            data['test_context']['engine'] = os.environ.get('ENGINE')

        if not data['test_context']['engine']:
            raise Exception("Cannot determine the test execution engine. No ENGINE environment variable set")

        if os.environ.get('URL_OVERRIDE'):
            override = os.environ.get('URL_OVERRIDE')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} URL_OVERRIDE={override}")
            data['test_context']['sut_url_override'] = os.environ.get('URL_OVERRIDE')

        engine = data['test_context']['engine']

        if os.environ.get('TEST_ENV'):
            override = os.environ.get('TEST_ENV')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} TEST_ENV={override}")
            data['test_context']['test_env'] = os.environ.get('TEST_ENV')

        if not data['test_context']['test_env']:
            raise Exception('No test environment specified')

        if engine == SylphSession.APPIUM:
            data = self._get_env_overrides_appium(data)
        elif engine == SylphSession.SELENIUM or engine == SylphSession.PLAYWRIGHT:
            data = self._get_env_overrides_web(data)
        elif engine == SylphSession.API:
            pass # No overrides necessary
        else:
            raise Exception(f'Unsupported test engine: {engine}')

        return data

    def _get_env_overrides_appium(self, data):
        if os.environ.get('PLATFORM_NAME'):
            override = os.environ.get('PLATFORM_NAME')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} PLATFORM_NAME={override}')
            data['desired_caps']['platformName'] = os.environ.get('PLATFORM_NAME')
        if os.environ.get('PLATFORM_VERSION'):
            override = os.environ.get('PLATFORM_VERSION')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} PLATFORM_VERSION={override}')
            data['desired_caps']['platformVersion'] = os.environ.get('PLATFORM_VERSION')
        if os.environ.get('APP'):
            override = os.environ.get('APP')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} APP={override}')
            data['desired_caps']['app'] = os.environ.get('APP')

        if os.environ.get('SERVER'):
            override = os.environ.get('SERVER')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} SERVER={override}')
            data['exec_target']['server'] = os.environ.get('SERVER')
        if os.environ.get('REAL_DEVICE'):
            override = os.environ.get('REAL_DEVICE')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} REAL_DEVICE={override}')
            data['exec_target']['realDevice'] = os.environ.get('REAL_DEVICE')

        return data

    def _get_env_overrides_web(self, data):
        if os.environ.get('BROWSER'):
            override = os.environ.get('BROWSER')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} BROWSER={override}')
            data['desired_caps']['browser'] = os.environ.get('BROWSER')
        if os.environ.get('PLATFORM'):
            override = os.environ.get('PLATFORM')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} PLATFORM={override}')
            data['desired_caps']['platform'] = os.environ.get('PLATFORM')
        if os.environ.get('IS_HEADLESS'):
            override = os.environ.get('IS_HEADLESS')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} IS_HEADLESS={override}')
            data['desired_caps']['is_headless'] = os.environ.get('IS_HEADLESS')
        if os.environ.get('SERVER'):
            override = os.environ.get('SERVER')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} SERVER={override}')
            data['exec_target']['server'] = os.environ.get('SERVER')

        return data

    def _get_env_overrides_api(self, data):
        # todo: determine if any additional overrides might be specifically api related
        return data


class SylphSession:
    """
    Loads sylph config, initialises sylph logging
    """
    log: Logger = Logger

    FIXTURES = "sylph_proj.fixtures"
    TEST_ROOT_DIR = 'tests'
    LOGGING_DIR = 'test_results'
    LOGFILE = 'results'

    # Session test execution engine
    API = 'api'
    APPIUM = 'appium'
    SELENIUM = 'selenium'
    PLAYWRIGHT = 'playwright'


    def __init__(self):
        self.project_path = self._get_solution_project_path()
        self._init_logging()
        self._data = ConfigLoader(self.project_path, self.log).data
        self._config = SylphSessionConfig(self._data)

    @property
    def project_path(self):
        return self._project_path

    @project_path.setter
    def project_path(self, value):
        self._project_path = value

    @property
    def config(self) -> SylphSessionConfig:
        return self._config

    def _get_solution_project_path(self):
        # Climb the tree until we are in the tests dir. Then return parent name.
        cwd = Path.cwd()
        while cwd.name is not SylphSession.TEST_ROOT_DIR:
            os.chdir(os.path.dirname(os.getcwd()))
            cwd = Path.cwd()

        return Path.cwd().parent

    def _get_logging_dir_path(self):
        project_root = self.project_path.parent
        logging_dir_path = Path(f'{project_root}/{self.LOGGING_DIR}')

        try:
            if not logging_dir_path.exists():
                logging_dir_path.mkdir(parents=True)
        except FileExistsError:
            pass  # it probably was created by another test

        return logging_dir_path

    def _init_logging(self):
        self.log = logging.getLogger('Session')
        self.log.setLevel(logging.DEBUG)

        log_dir_path = self._get_logging_dir_path()

        worker_id = os.environ.get("PYTEST_XDIST_WORKER")
        if worker_id is not None:
            logfile = f'{log_dir_path}/{self.LOGFILE}_{worker_id}'
        else:
            logfile = f'{log_dir_path}/{self.LOGFILE}'
        logfile = f'{logfile}.log'

        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(logfile)
        c_handler.setLevel(logging.INFO)
        f_handler.setLevel(logging.DEBUG)

        c_format = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
        f_format = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        self.log.addHandler(c_handler)
        self.log.addHandler(f_handler)

        self.log.debug(f'{self} Initialised...')
