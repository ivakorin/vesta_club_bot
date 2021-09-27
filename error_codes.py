import yaml
from os import path

basedir = path.abspath(path.dirname(__file__))


class ErrorCodes:
    def __init__(self, err_code=None):
        self.err_code = err_code
        self.list = 'error_codes.yaml'

    def __read_codes(self):
        self.config = yaml.load(open(path.join(basedir, self.list)), Loader=yaml.Loader)
        self.config_location = path.join(basedir, self.list)
        result = self.config.get(self.err_code)
        return result

    def codes_return(self):
        result = self.__read_codes()
        if result:
            result['error_code'] = self.err_code
            return result
        else:
            return None
