from PyQt5.QtCore import QSettings, QSize

from Constants import Constants


class Preferences(QSettings):
    # The following are the preferences available

    # How should frames be combined?  Stored as an integer corresponding to one of
    # the COMBINE_xxx constants in the Constants class
    MASTER_COMBINE_METHOD = "master_combine_method"

    # If the Min-Max method is used, how many points are dropped from each end (min and max)
    # before the remaining points are Mean-combined?  Returns an integer > 0.
    MIN_MAX_NUMBER_CLIPPED_PER_END = "min_max_number_clipped_per_end"

    # If Sigma-Clip method is used, what is the threshold sigma score?
    # Data farther than this many standard deviations from the sample mean are rejected,
    # the the remaining points are mean-combined.  Floating point number > 0.
    SIGMA_CLIP_THRESHOLD = "sigma_clip_threshold"

    # What do we do with the input files after a successful combine?
    # Gives an integer from the constants class DISPOSITION_xxx
    INPUT_FILE_DISPOSITION = "input_file_disposition"

    # Folder name to move input files if DISPOSITION is SUBFOLDER
    DISPOSITION_SUBFOLDER_NAME = "disposition_subfolder_name"

    # Main window size - so last window resizing is remembered
    MAIN_WINDOW_SIZE = "main_window_size"

    def __init__(self):
        QSettings.__init__(self, "EarwigHavenObservatory.com", "MasterBiasMaker_b")
        # print(f"Preferences file path: {self.fileName()}")

    # Getters and setters for preferences values

    # How should frames be combined?  Stored as an integer corresponding to one of
    # the COMBINE_xxx constants in the Constants class

    def get_master_combine_method(self) -> int:
        result = int(self.value(self.MASTER_COMBINE_METHOD, defaultValue=Constants.COMBINE_SIGMA_CLIP))
        assert (result == Constants.COMBINE_SIGMA_CLIP) \
               or (result == Constants.COMBINE_MINMAX) \
               or (result == Constants.COMBINE_MEDIAN) \
               or (result == Constants.COMBINE_MEAN)
        return result

    def set_master_combine_method(self, value: int):
        assert (value == Constants.COMBINE_SIGMA_CLIP) or (value == Constants.COMBINE_MINMAX) \
               or (value == Constants.COMBINE_MEDIAN) or (value == Constants.COMBINE_MEAN)
        self.setValue(self.MASTER_COMBINE_METHOD, value)

    # If the Min-Max method is used, how many points are dropped from each end (min and max)
    # before the remaining points are Mean-combined?  Returns an integer > 0.

    def get_min_max_number_clipped_per_end(self) -> int:
        result = int(self.value(self.MIN_MAX_NUMBER_CLIPPED_PER_END, defaultValue=2))
        assert result > 0
        return result

    def set_min_max_number_clipped_per_end(self, value: int):
        assert value > 0
        self.setValue(self.MIN_MAX_NUMBER_CLIPPED_PER_END, value)

    # If Sigma-Clip method is used, what is the threshold sigma score?
    # Data farther than this many sigmas (ratio of value and std deviation of set) from the sample mean
    # are rejected, the the remaining points are mean-combined.  Floating point number > 0.

    def get_sigma_clip_threshold(self) -> float:
        result = float(self.value(self.SIGMA_CLIP_THRESHOLD, defaultValue=3.0))
        assert result > 0.0
        return result

    def set_sigma_clip_threshold(self, value: float):
        assert value > 0.0
        self.setValue(self.SIGMA_CLIP_THRESHOLD, value)

    # What to do with input files after a successful combine

    def get_input_file_disposition(self):
        result = int(self.value(self.INPUT_FILE_DISPOSITION, defaultValue=Constants.INPUT_DISPOSITION_NOTHING))
        assert (result == Constants.INPUT_DISPOSITION_NOTHING) or (result == Constants.INPUT_DISPOSITION_SUBFOLDER)
        return result

    def set_input_file_disposition(self, value: int):
        assert (value == Constants.INPUT_DISPOSITION_NOTHING) or (value == Constants.INPUT_DISPOSITION_SUBFOLDER)
        self.setValue(self.INPUT_FILE_DISPOSITION, value)

    # Where to move input files if disposition "subfolder" is chosen

    def get_disposition_subfolder_name(self):
        return self.value(self.DISPOSITION_SUBFOLDER_NAME, defaultValue="originals-%d-%t")

    def set_disposition_subfolder_name(self, value: str):
        self.setValue(self.DISPOSITION_SUBFOLDER_NAME, value)

    # Main window size when resized

    def get_main_window_size(self) -> QSize:
        return self.value(self.MAIN_WINDOW_SIZE, defaultValue=None)

    def set_main_window_size(self, size: QSize):
        self.setValue(self.MAIN_WINDOW_SIZE, size)
