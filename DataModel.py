#
#   Data model for this program, storing the information for one combination session.
#   (As opposed to the Preferences object which permanently stores default settings that will
#   be used for future sessions.)
#
#   This data model is displayed and edited on the main window when using the GUI, or
#   modified by command-line flags when using the command line.  It is initialized when
#   created from values in the Preferences object
#
from Constants import Constants
from Preferences import Preferences


class DataModel:

    # Create data model from given preferences object.  This also lists all the fetch/settable values

    def __init__(self, preferences: Preferences):
        self._master_combine_method: int = preferences.get_master_combine_method()
        self._min_max_number_clipped_per_end: int = preferences.get_min_max_number_clipped_per_end()
        self._sigma_clip_threshold: float = preferences.get_sigma_clip_threshold()
        self._input_file_disposition: int = preferences.get_input_file_disposition()
        self._disposition_subfolder_name: str = preferences.get_disposition_subfolder_name()
        self._group_by_size: bool = preferences.get_group_by_size()
        self._group_by_temperature: bool = preferences.get_group_by_temperature()
        self._temperature_group_bandwidth: float = preferences.get_temperature_group_bandwidth()
        self._ignore_file_type: bool = False
        self._ignore_groups_fewer_than: bool = preferences.get_ignore_groups_fewer_than()
        self._minimum_group_size: int = preferences.get_minimum_group_size()

    def get_master_combine_method(self) -> int:
        result = self._master_combine_method
        assert (result == Constants.COMBINE_SIGMA_CLIP) \
               or (result == Constants.COMBINE_MINMAX) \
               or (result == Constants.COMBINE_MEDIAN) \
               or (result == Constants.COMBINE_MEAN)
        return result

    def set_master_combine_method(self, value: int):
        assert (value == Constants.COMBINE_SIGMA_CLIP) or (value == Constants.COMBINE_MINMAX) \
               or (value == Constants.COMBINE_MEDIAN) or (value == Constants.COMBINE_MEAN)
        self._master_combine_method = value

    # If the Min-Max method is used, how many points are dropped from each end (min and max)
    # before the remaining points are Mean-combined?  Returns an integer > 0.

    def get_min_max_number_clipped_per_end(self) -> int:
        result = self._min_max_number_clipped_per_end
        assert result > 0
        return result

    def set_min_max_number_clipped_per_end(self, value: int):
        assert value > 0
        self._min_max_number_clipped_per_end = value

    # If Sigma-Clip method is used, what is the threshold sigma score?
    # Data farther than this many sigmas (ratio of value and std deviation of set) from the sample mean
    # are rejected, the the remaining points are mean-combined.  Floating point number > 0.

    def get_sigma_clip_threshold(self) -> float:
        result = self._sigma_clip_threshold
        assert result > 0.0
        return result

    def set_sigma_clip_threshold(self, value: float):
        assert value > 0.0
        self._sigma_clip_threshold = value

    # What to do with input files after a successful combine

    def get_input_file_disposition(self):
        result = self._input_file_disposition
        assert (result == Constants.INPUT_DISPOSITION_NOTHING) or (result == Constants.INPUT_DISPOSITION_SUBFOLDER)
        return result

    def set_input_file_disposition(self, value: int):
        assert (value == Constants.INPUT_DISPOSITION_NOTHING) or (value == Constants.INPUT_DISPOSITION_SUBFOLDER)
        self._input_file_disposition = value

    # Where to move input files if disposition "subfolder" is chosen

    def get_disposition_subfolder_name(self):
        return self._disposition_subfolder_name

    def set_disposition_subfolder_name(self, value: str):
        self._disposition_subfolder_name = value

    # Are we processing multiple file sets at once using grouping?

    def get_group_by_size(self) -> bool:
        return self._group_by_size

    def set_group_by_size(self, is_grouped: bool):
        self._group_by_size = is_grouped

    def get_group_by_temperature(self) -> bool:
        return self._group_by_temperature

    def set_group_by_temperature(self, is_grouped: bool):
        self._group_by_temperature = is_grouped

    # How much, as a percentage, can exposures vary before the files are considered to be in a different group?

    def get_temperature_group_bandwidth(self) -> float:
        bandwidth: float = self._temperature_group_bandwidth
        assert 0.1 <= bandwidth <= 50.0
        return bandwidth

    def set_temperature_group_bandwidth(self, bandwidth: float):
        assert 0.1 <= bandwidth <= 50.0
        self._temperature_group_bandwidth = bandwidth

    def get_ignore_file_type(self) -> bool:
        return self._ignore_file_type

    def set_ignore_file_type(self, ignore: bool):
        self._ignore_file_type = ignore

    def get_ignore_groups_fewer_than(self) -> bool:
        return self._ignore_groups_fewer_than

    def set_ignore_groups_fewer_than(self, ignore: bool):
        self._ignore_groups_fewer_than = ignore

    def get_minimum_group_size(self) -> int:
        return self._minimum_group_size

    def set_minimum_group_size(self, minimum: int):
        self._minimum_group_size = minimum
