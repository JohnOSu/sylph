import json
import enum
from json import JSONDecodeError

from requests import Response


class SylphDataGenerator(enum.Enum):
    AUTOMATION_CODE = "automation"
    API_REQUEST = "api_request"
    APP_UI_INSPECTION = "app"


class SylphDataDict(dict):
    data_generator: SylphDataGenerator

    def __init__(self, data_source: SylphDataGenerator, data: dict):
        super().__init__()
        self.data_generator = data_source
        for keyname in data.keys():
            self[keyname] = data[keyname]


class SylphObjectInitException(Exception):
    pass


class SylphDataObject:
    data_generator: SylphDataGenerator

    def __init__(self, response: Response = None, data: SylphDataDict = None):
        # Store init arg in self._src. If arg is response, transform into a dict.
        if response is not None and data is not None:
            raise SylphObjectInitException("Must be either a Response or a SylphDataDict")
        if response is None:
            if data is None:
                # must be defining function calls
                self._src = []
                self.data_generator = SylphDataGenerator.AUTOMATION_CODE
            else:
                if not hasattr(data, 'data_generator'):
                    raise SylphObjectInitException("If data is provided, it must be a SylphDataDict")
                self._src = data
                self.data_generator = data.data_generator
        else:
            self.data_generator = SylphDataGenerator.API_REQUEST
            self._src = json.loads(response.content.decode('utf-8'))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        try:
            return self.dump_data() == other.dump_data()
        except:
            return False

    def dump_data(self):
        data = {}
        for key in self._src.keys():
            data[key] = self._src[key].dump_data() if issubclass(type(self._src[key]), SylphDataObject) else self._src[key]

        return data


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

        self.dto_name = self._src['dto_name']
        self.dto_path = self._src['dto_path']
        self.dto_exc = self._src['dto_exc']
