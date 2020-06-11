import os
import logging
from logging import Logger
import json
from pathlib import Path


class SylphSessionConfig:
    def __init__(self, data):
        self._sut_type: str = data['test_context']['sut_type']
        self._test_env: str = data['test_context']['test_env']
        self._env_base_url: str = data['test_context']['env_base_url'] if 'env_base_url' in data['test_context'] else None
        self._api_version = data['test_context']['api_version'] if 'api_version' in data['test_context'] else None
        self._exec_target_server: str = data['exec_target']['server']
        self._real_device = data['exec_target']['realDevice'] if 'realDevice' in data['exec_target'] else None
        self._browser: str = data['desired_caps']['browser'] if 'browser' in data['desired_caps'] else None
        self._platform: str = data['desired_caps']['platformName'] if 'platformName' in data['desired_caps'] else None
        self._desired_capabilities: dict = data['desired_caps']

    @property
    def api_version(self) -> str:
        return self._api_version

    @property
    def environment(self) -> str:
        return self._test_env

    @property
    def env_base_url(self) -> str:
        return self._env_base_url

    @property
    def is_mobile(self) -> bool:
        return self._sut_type.lower() == SylphSession.MOBILE

    @property
    def is_web(self) -> bool:
        return self._sut_type.lower() == SylphSession.WEB

    @property
    def is_api(self) -> bool:
        return self._sut_type.lower() == SylphSession.API

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
    def is_firefox(self) -> bool:
        return False if self._browser is None else self._browser.lower() == 'firefox'

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
        if os.environ.get('SUT_TYPE'):
            override = os.environ.get('SUT_TYPE')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} SUT_TYPE={override}")
            data['test_context']['sut_type'] = os.environ.get('SUT_TYPE')

        if not data['test_context']['sut_type']:
            raise Exception("Cannot determine the subject under test. No SUT_TYPE environment variable set")

        sut_type = data['test_context']['sut_type']

        if os.environ.get('API_VERSION'):
            override = os.environ.get('API_VERSION')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} API_VERSION={override}")
            try:
                data['test_context']['api_version'] = int(os.environ.get('API_VERSION'))
            except ValueError:
                data['test_context']['api_version'] = os.environ.get('API_VERSION')

        if not data['test_context']['api_version']:
            raise Exception('No api version specified')

        if os.environ.get('TEST_ENV'):
            override = os.environ.get('TEST_ENV')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} TEST_ENV={override}")
            data['test_context']['test_env'] = os.environ.get('TEST_ENV')

        if not data['test_context']['test_env']:
            raise Exception('No test environment specified')

        if os.environ.get('ENV_BASE_URL'):
            override = os.environ.get('ENV_BASE_URL')
            self._log.debug(f"{ConfigLoader.OVERRIDE_MSG} ENV_BASE_URL={override}")
            data['test_context']['env_base_url'] = os.environ.get('ENV_BASE_URL')

        if not data['test_context']['env_base_url']:
            raise Exception('No test environment base URL specified')

        if sut_type == SylphSession.MOBILE:
            data = self._get_env_overrides_mobile(data)
        elif sut_type == SylphSession.WEB:
            data = self._get_env_overrides_web(data)
        elif sut_type == SylphSession.API:
            pass # because any config would need to be set already as api will likely be needed by the other sut_types
        else:
            raise Exception(f'Unsupported system under test type: {sut_type}')

        return data

    def _get_env_overrides_mobile(self, data):
        if os.environ.get('DEVICE_NAME'):
            override = os.environ.get('DEVICE_NAME')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} DEVICE_NAME={override}')
            data['desired_caps']['deviceName'] = os.environ.get('DEVICE_NAME')
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
        if os.environ.get('VERSION'):
            override = os.environ.get('VERSION')
            self._log.debug(f'{ConfigLoader.OVERRIDE_MSG} VERSION={override}')
            data['desired_caps']['version'] = os.environ.get('VERSION')

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
    LOGFILE = 'results.log'

    # Session platform
    MOBILE = 'mobile'
    WEB = 'web'
    API = 'api'

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
        logfile = f'{log_dir_path}/{self.LOGFILE}'

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
