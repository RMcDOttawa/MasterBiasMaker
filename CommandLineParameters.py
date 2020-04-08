#
#   All the info describing a master combine run from command line
#   taking arguments given on command line, and using preferences values
#   where command line argument is not given
#
from Constants import Constants


class CommandLineParameters:

    def __init__(self):
        self._pre_calibration_type: int = Constants.CALIBRATION_NONE
        self._combine_method: int = Constants.COMBINE_MEAN
        self._pedestal: int = 0
        self._fixed_calibration_file: str = ""
        self._min_max_drop: int = 0
        self._sigma_threshold: float = 0
        self._ignore_fits_type: bool = False
        self._ignore_filter_type: bool = False
        self._disposition_move: bool = False
        self._disposition_folder: str = ""
        self._output_path: str = ""
        self._file_names: [str] = []

    def get_pre_calibration_type(self) -> int:
        return self._pre_calibration_type

    def set_pre_calibration_type(self, value: int):
        self._pre_calibration_type = value

    def get_pedestal(self) -> int:
        return self._pedestal

    def set_pedestal(self, value: int):
        self._pedestal = value

    def get_fixed_calibration_file(self) -> str:
        return self._fixed_calibration_file

    def set_fixed_calibration_file(self, value: str):
        self._fixed_calibration_file = value

    def get_combine_method(self) -> int:
        return self._combine_method

    def set_combine_method(self, value: int):
        self._combine_method = value

    def get_min_max_drop(self) -> int:
        return self._min_max_drop

    def set_min_max_drop(self, value: int):
        self._min_max_drop = value

    def get_sigma_threshold(self) -> float:
        return self._sigma_threshold

    def set_sigma_threshold(self, value: float):
        self._sigma_threshold = value

    def get_ignore_fits_type(self) -> bool:
        return self._ignore_fits_type

    def set_ignore_fits_type(self, value: bool):
        self._ignore_fits_type = value

    def get_ignore_filter_type(self) -> bool:
        return self._ignore_filter_type

    def set_ignore_filter_type(self, value: bool):
        self._ignore_filter_type = value

    def get_disposition_move(self) -> bool:
        return self._disposition_move

    def set_disposition_move(self, value: bool):
        self._disposition_move = value

    def get_disposition_folder(self) -> str:
        return self._disposition_folder

    def set_disposition_folder(self, value: str):
        self._disposition_folder = value

    def get_output_path(self) -> str:
        return self._output_path

    def set_output_path(self, value: str):
        self._output_path = value

    def get_file_names(self) -> [str]:
        return self._file_names

    def set_file_names(self, names: [str]):
        self._file_names = names

    def print_all(self):
        print(f"pre_calibration_type: {Constants.calibration_string(self._pre_calibration_type)}")
        print(f"combine_method: {Constants.combine_method_string(self._combine_method)}")
        print(f"pedestal: {self._pedestal}")
        print(f"fixed_calibration_file: {self._fixed_calibration_file}")
        print(f"min_max_drop: {self._min_max_drop}")
        print(f"sigma_threshold: {self._sigma_threshold}")
        print(f"ignore_fits_type: {self._ignore_fits_type}")
        print(f"ignore_filter_type: {self._ignore_filter_type}")
        print(f"disposition_move: {self._disposition_move}")
        print(f"disposition_folder: {self._disposition_folder}")
        print(f"output_path: {self._output_path}")
