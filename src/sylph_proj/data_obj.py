import json
import enum
import re
import copy
from json import JSONDecodeError
import urllib
from requests import Response


class SylphDataGenerator(enum.Enum):
    AUTOMATION_CODE = "automation"
    API_REQUEST = "api_request"
    APP_UI_INSPECTION = "app"

class SylphRequestMetadata:
    def __init__(self):
        self.data_generator = None
        self.request_url = None
        self.request_hdr = None
        self.api_version = None
        self.api_minor_v = None
        self.api_patch_v = None
        self.source_data = None


class SylphDataDict(dict):
    def __init__(self, data_source, data: dict):
        super().__init__()

        if isinstance(data_source, SylphDataGenerator):
            self.metadata = SylphRequestMetadata()
            self.metadata.data_generator = data_source
        elif isinstance(data_source, SylphRequestMetadata):
            self.metadata = copy.deepcopy(data_source)
            self.metadata.source_data = data

        for keyname in data.keys():
            self[keyname] = data[keyname]


class SylphObjectInitException(Exception):
    pass


class SylphDataObject:
    def __init__(self, response: Response = None, data: SylphDataDict = None):
        # Store init arg in self._src. If arg is response, transform into a dict.
        self.metadata = SylphRequestMetadata()

        if response is not None and data is not None:
            raise SylphObjectInitException("Must be either a Response or a SylphDataDict")
        if response is None:
            if data is None:
                self.metadata.data_generator = SylphDataGenerator.AUTOMATION_CODE
                # must be defining function calls
                self.metadata.source_data = []

            else:
                if not isinstance(data, SylphDataDict):
                    raise SylphObjectInitException("If data is provided, it must be a SylphDataDict")
                self.metadata = copy.deepcopy(data.metadata)
                self.metadata.source_data = data

        else:
            api_version, api_minor_v, api_patch_v = try_get_api_version(response.url)

            self.metadata.data_generator = SylphDataGenerator.API_REQUEST
            self.metadata.request_url = response.url
            self.metadata.request_hdr = response.headers
            self.metadata.api_version = api_version
            self.metadata.api_minor_v = api_minor_v
            self.metadata.api_patch_v = api_patch_v
            self.metadata.source_data = json.loads(response.content.decode('utf-8'))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        try:
            return self.dump_data() == other.dump_data()
        except:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self.metadata.source_data.keys()))

    def dump_data(self):
        data = {}
        for key in self.metadata.source_data.keys():
            data[key] = (self.metadata.source_data[key].dump_data()
                         if issubclass(type(self.metadata.source_data[key]), SylphDataObject)
                         else self.metadata.source_data[key])

        return data

    def get_unprocessed_data(self, new_data=None):
        new_data = [] if new_data is None else new_data
        class_name = self.__class__.__name__
        for key in self.metadata.source_data.keys():
            if hasattr(self, key):
                item = self.__getattribute__(key)
                if issubclass(type(item), SylphDataObject):
                    new_data = item.get_unprocessed_data(new_data)
            elif isinstance(self.metadata.source_data[key], dict):
                for sub_key in self.metadata.source_data[key].keys():
                    if hasattr(self, sub_key):
                        sub_item = self.__getattribute__(sub_key)
                        if issubclass(type(sub_item), SylphDataObject):
                            new_data = sub_item.get_unprocessed_data(new_data)
                    else:
                        new_data.append(f"{class_name}.{sub_key}")
            else:
                new_data.append(f"{class_name}.{key}")

        return new_data


class SylphCollectionDataObject(SylphDataObject):
    def __init__(self, response: Response = None, data: SylphDataDict = None):
        super().__init__(response, data)
        self._items = []

    def __getitem__(self, idx):
        return self._items[idx]

    @property
    def items(self) -> []:
        return self._items

    @property
    def count(self):
        return len(self._items)


class ResponseError(SylphDataObject):
    def __init__(self, response: Response = None, data: SylphDataDict = None):
        try:
            super().__init__(response=response, data=data)
        except JSONDecodeError:
            self._src = {}
            self._src['errorCode'] = response.status_code if hasattr(response, 'status_code') else None
            self._src['errorMessage'] = response.reason if hasattr(response, 'reason') else None

        self.ok: bool = False
        self.error_code = self._src['errorCode'] if 'errorCode' in self._src else None
        self.error_message = self._src['errorMessage'] if 'errorMessage' in self._src else None
        if not self.error_message:
            self.error_message = response.text if hasattr(response, 'text') else None
        self.status_code = response.status_code if hasattr(response, 'status_code') else self.error_code
        self.reason = response.reason if hasattr(response, 'reason') else None


class ContractViolation(SylphDataObject):
    def __init__(self, response: Response = None, data: SylphDataDict = None):
        super().__init__(response=response, data=data)

        self.dto_name = self.metadata.source_data['dto_name']
        self.dto_path = self.metadata.source_data['dto_path']
        self.dto_exc = self.metadata.source_data['dto_exc']


def try_get_api_version(url):
    api_version = None
    api_minor_v = None
    api_patch_v = None

    try:
        url_split = urllib.parse.urlsplit(url)
        pattern = r'(api\/v[0-9]*)'
        regex = re.compile(pattern)
        result = regex.search(url_split.path)
        if result:
            api_v_str = result.string.split('/api/v')[1].split('/')[0]
            v_str_arr = api_v_str.split('.')
            api_version = set_version(v_str_arr[0])
            if len(v_str_arr) > 1:
                api_minor_v = set_version(v_str_arr[1])
            if len(v_str_arr) > 2:
                api_patch_v = set_version(v_str_arr[2])
    except:
        pass

    return api_version, api_minor_v, api_patch_v


def set_version(ver_str):
    try:
        as_int = int(ver_str)
        return as_int
    except:
        return ver_str
