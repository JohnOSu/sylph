import os
import logging
from logging import Logger
import json
from pathlib import Path


class SessionConfig:
    def __init__(self, data):
        self._sut_type: str = data['test_context']['sut_type']
        self._exec_target_server: str = data['exec_target']['server']
        self._real_device = data['exec_target']['realDevice'] if 'realDevice' in data['exec_target'] else None
        self._browser: str = data['desired_caps']['browser'] if 'browser' in data['desired_caps'] else None
        self._platform: str = data['desired_caps']['platformName'] if 'platformName' in data['desired_caps'] else None

        # Selenium grid doesn't handle mobile platformName capability correctly, so remove it if executing on grid.
        self._is_grid_hub = data['exec_target']['isGridHub'] if 'isGridHub' in data['exec_target'] else False
        if self._is_grid_hub and self.is_mobile and 'platformName' in data['desired_caps']:
            del data['desired_caps']['platformName']

        self._desired_capabilities: dict = data['desired_caps']

    @property
    def is_mobile(self) -> bool:
        return self._sut_type.lower() == Session.MOBILE

    @property
    def is_web(self) -> bool:
        return self._sut_type.lower() == Session.WEB

    @property
    def is_api(self) -> bool:
        return self._sut_type.lower() == Session.API

    @property
    def desired_capabilities(self) -> dict:
        return self._desired_capabilities

    @property
    def exec_target_server(self) -> str:
        return self._exec_target_server

    @property
    def is_chrome(self) -> bool:
        return self._browser.lower() == 'chrome'

    @property
    def is_firefox(self) -> bool:
        return self._browser.lower() == 'firefox'

    @property
    def is_android(self) -> bool:
        return self._platform.lower() == 'android'

    @property
    def is_ios(self) -> bool:
        return self._platform.lower() == 'ios'

    @property
    def is_real_device(self) -> bool:
        return self._real_device == True


class ConfigLoader:
    def __init__(self, project_path):
        self._project_path = project_path

    @property
    def data(self):
        return self._load_session_config()

    def _load_session_config(self):
        """
        Get the session config from json.
        If not found, get it from a template.
        Then check for os env overrides.
        :return:
        """
        try:
            config = Path(f'{self._project_path}/config/session_config.json')
            with open(config) as json_file:
                data = json.load(json_file)
        except FileNotFoundError:
            # If not found, get template based on 'sut_type' env variable.
            sut_type = os.environ.get('SUT_TYPE')
            if sut_type:
                data = self._get_config_template(sut_type)
            else:
                raise Exception('Cannot identify the system under test. This should '
                                'be set in a session config file, or with an environment variable.')
        # sut_type is now in data
        # now check for environment overrides
        data = self._get_env_overrides(data)

        if os.environ.get('JIRA_USER_NAME'):
            data['tool_integration']['jira_username'] = os.environ.get('JIRA_USER_NAME')
        if os.environ.get('JIRA_PASSWORD'):
            data['tool_integration']['jira_password'] = os.environ.get('JIRA_PASSWORD')

        if os.environ.get('TESTRAIL_REPORT'):
            data['tool_integration']['testrail_report'] = os.environ.get('TESTRAIL_REPORT')
        if os.environ.get('TESTRAIL_USER_NAME'):
            data['tool_integration']['testrail_username'] = os.environ.get('TESTRAIL_USER_NAME')
        if os.environ.get('TESTRAIL_PASSWORD'):
            data['tool_integration']['testrail_password'] = os.environ.get('TESTRAIL_PASSWORD')
        if os.environ.get('TESTRAIL_HOST'):
            data['tool_integration']['testrail_host'] = os.environ.get('TESTRAIL_HOST')
        if os.environ.get('TESTRAIL_TEST_SUITE_NAME'):
            data['tool_integration']['testrail_test_suite_name'] = os.environ.get('TESTRAIL_TEST_SUITE_NAME')
        if os.environ.get('TESTRAIL_PROJECT_NAME'):
            data['tool_integration']['testrail_project_name'] = os.environ.get('TESTRAIL_PROJECT_NAME')

        return data

    def _get_config_template(self, sut_type):
        if sut_type == Session.MOBILE:
            data = self._get_config_template_mobile()
        elif sut_type == Session.WEB:
            data = self._get_config_template_web()
        elif sut_type == Session.API:
            data = self._get_config_template_api()
        else:
            raise Exception(f'Unsupported system under test: {sut_type}')

        return data

    def _get_env_overrides(self, data):
        sut_type = data['test_context']['sut_type']
        if sut_type == Session.MOBILE:
            data = self._get_env_overrides_mobile(data)
        elif sut_type == Session.WEB:
            data = self._get_env_overrides_web(data)
        elif sut_type == Session.API:
            data = self._get_env_overrides_api(data)
        else:
            raise Exception(f'Unsupported system under test: {sut_type}')

        # todo get general env overrides - e.g. TestRail & Jira

        return data

    def _get_env_overrides_mobile(self, data):
        if os.environ.get('DEVICE_NAME'):
            data['desired_caps']['deviceName'] = os.environ.get('DEVICE_NAME')
        if os.environ.get('PLATFORM_NAME'):
            data['desired_caps']['platformName'] = os.environ.get('PLATFORM_NAME')
        if os.environ.get('PLATFORM_VERSION'):
            data['desired_caps']['platformVersion'] = os.environ.get('PLATFORM_VERSION')
        if os.environ.get('APP'):
            data['desired_caps']['app'] = os.environ.get('APP')
        if os.environ.get('AUTOMATION_NAME'):
            data['desired_caps']['automationName'] = os.environ.get('AUTOMATION_NAME')
        if os.environ.get('WDA_LOCAL_PORT'):
            data['desired_caps']['wdaLocalPort'] = os.environ.get('WDA_LOCAL_PORT')

        if os.environ.get('SERVER'):
            data['exec_target']['server'] = os.environ.get('SERVER')
        if os.environ.get('REAL_DEVICE'):
            data['exec_target']['realDevice'] = os.environ.get('REAL_DEVICE')

        return data

    def _get_env_overrides_web(self, data):
        if os.environ.get('BROWSER'):
            data['desired_caps']['browser'] = os.environ.get('BROWSER')
        if os.environ.get('PLATFORM'):
            data['desired_caps']['platform'] = os.environ.get('PLATFORM')
        if os.environ.get('VERSION'):
            data['desired_caps']['version'] = os.environ.get('VERSION')

        return data

    def _get_env_overrides_api(self, data):
        # todo
        pass

    @staticmethod
    def _get_config_template_mobile():
        return {
            "test_context": {
                "sut_type": Session.MOBILE,
                "test_env": None
            },
            "desired_caps": {
                "deviceName": None,
                "platformName": None,
                "platformVersion": None,
                "app": None,
                "automationName": None,
                "wdaLocalPort": None
            },
            "exec_target": {
                "server": None,
                "realDevice": None
            },
            "tool_integration": {
                "jira_username": None,
                "jira_password": None,
                "testrail_report": None,
                "testrail_username": None,
                "testrail_password": None,
                "testrail_host": None,
                "testrail_test_suite_name": None,
                "testrail_project_name": None
            }
        }

    @staticmethod
    def _get_config_template_web():
        return {
            "test_context": {
                "sut_type": Session.WEB,
                "test_env": None
            },
            "desired_caps": {
                "browser": None,
                "platform": None,
                "version": None
            },
            "exec_target": {
                "server": None
            },
            "tool_integration": {
                "jira_username": None,
                "jira_password": None,
                "testrail_report": None,
                "testrail_username": None,
                "testrail_password": None,
                "testrail_host": None,
                "testrail_test_suite_name": None,
                "testrail_project_name": None
            }
        }

    @staticmethod
    def _get_config_template_api():
        return {
            "test_context": {
                "sut_type": Session.API,
                "test_env": None
            },
            "desired_caps": {
                "deviceName": None,
                "platformName": None,
                "platformVersion": None,
                "app": None,
                "automationName": None,
                "wdaLocalPort": None
            },
            "exec_target": {
                "server": None,
                "realDevice": None
            },
            "tool_integration": {
                "jira_username": None,
                "jira_password": None,
                "testrail_report": None,
                "testrail_username": None,
                "testrail_password": None,
                "testrail_host": None,
                "testrail_test_suite_name": None,
                "testrail_project_name": None
            }
        }


class Session:
    """
    Loads session config, initialises session logging
    """
    log: Logger = Logger

    TEST_ROOT_DIR = 'tests'
    LOGGING_DIR = 'test_results'
    LOGFILE = 'results.log'

    MOBILE = 'mobile'
    WEB = 'web'
    API = 'api'

    def __init__(self):
        self.project_path = self._get_solution_project_path()
        self._init_logging()
        self.log.debug('Node session initialiser loading the session config')
        self._data = ConfigLoader(self.project_path).data
        self._config = SessionConfig(self._data)

    @property
    def project_path(self):
        return self._project_path

    @project_path.setter
    def project_path(self, value):
        self._project_path = value

    @property
    def config(self) -> SessionConfig:
        return self._config

    def _get_solution_project_path(self):
        # Climb the tree until we are in the tests dir. Then return parent name.
        cwd = Path.cwd()
        while cwd.name is not Session.TEST_ROOT_DIR:
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

        self.log.debug(f'Node {self} instance: Initialised {self.log.name} logger')
