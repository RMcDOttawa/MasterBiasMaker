#
#   Class to handle calibration of images using specified method (including none)
#
import sys
from typing import Optional

from numpy import ndarray

import MasterMakerExceptions
from Console import Console
from Constants import Constants
from DataModel import DataModel
from FileDescriptor import FileDescriptor
from RmFitsUtil import RmFitsUtil
from SessionController import SessionController
from SharedUtils import SharedUtils


class Calibrator:
    #
    #   Create calibration object against the given data model's settings
    #
    def __init__(self, data_model: DataModel):
        self._data_model = data_model

    def calibrate_images(self, file_data: [ndarray],
                         sample_file: FileDescriptor,
                         console: Console,
                         session_controller: SessionController) -> [ndarray]:
        calibration_type = self._data_model.get_precalibration_type()
        if calibration_type == Constants.CALIBRATION_NONE:
            return file_data
        elif calibration_type == Constants.CALIBRATION_PEDESTAL:
            return self.calibrate_with_pedestal(file_data,
                                                self._data_model.get_precalibration_pedestal(),
                                                console,
                                                session_controller)
        elif calibration_type == Constants.CALIBRATION_FIXED_FILE:
            return self.calibrate_with_file(file_data,
                                            self._data_model.get_precalibration_fixed_path(),
                                            console,
                                            session_controller)
        else:
            assert calibration_type == Constants.CALIBRATION_AUTO_DIRECTORY
            return self.calibrate_with_auto_directory(file_data,
                                                      self._data_model.get_precalibration_auto_directory(),
                                                      sample_file,
                                                      console,
                                                      session_controller)

    def calibrate_with_pedestal(self,
                                file_data: [ndarray],
                                pedestal: int,
                                console: Console,
                                session_controller: SessionController) -> [ndarray]:
        result = file_data.copy()
        console.message(f"Calibrate with pedestal = {pedestal}", 0)
        for index in range(len(result)):
            if session_controller.thread_cancelled():
                break
            reduced_by_pedestal: ndarray = result[index] - pedestal
            result[index] = reduced_by_pedestal.clip(0, 0xFFFF)
        return result

    def calibrate_with_file(self, file_data: [ndarray], calibration_file_path: str, console: Console,
                                session_controller: SessionController) -> [ndarray]:
        console.message(f"Calibrate with file: {calibration_file_path}", 0)
        result = file_data.copy()
        calibration_image = RmFitsUtil.fits_data_from_path(calibration_file_path)
        (calibration_x, calibration_y) = calibration_image.shape
        for index in range(len(result)):
            if session_controller.thread_cancelled():
                break
            (layer_x, layer_y) = result[index].shape
            if (layer_x != calibration_x) or (layer_y != calibration_y):
                raise MasterMakerExceptions.IncompatibleSizes
            difference = result[index] - calibration_image
            result[index] = difference.clip(0, 0xFFFF)
        return result

    def calibrate_with_auto_directory(self, file_data: [ndarray], auto_directory_path: str,
                                      sample_file: FileDescriptor, console: Console,
                                      session_controller: SessionController) -> [ndarray]:
        console.message(f"Selecting best calibration file from {auto_directory_path}", 0)
        calibration_file = self.get_best_calibration_file(auto_directory_path, sample_file,
                                                          session_controller)
        # Should never come back None because an exception will have handled failure
        assert calibration_file is not None
        if session_controller.thread_running():
            return self.calibrate_with_file(file_data, calibration_file, console, session_controller)
        else:
            return None

    #
    # Get the best matched calibration file in the auto directory.  Only BIAS files
    # of the correct size will be selected
    # If no suitable file, raise exception
    #
    #   Exceptions thrown:
    #       NoSuitableAutoBias

    def get_best_calibration_file(self, directory_path: str, sample_file: FileDescriptor,
                                                          session_controller: SessionController) -> Optional[str]:
        # Get all calibration files in the given directory
        all_descriptors = self.all_descriptors_from_directory(directory_path,
                                                              self._data_model.get_auto_directory_recursive())
        if session_controller.thread_cancelled():
            return None
        if len(all_descriptors) == 0:
            # No files in that directory, raise exception
            raise MasterMakerExceptions.AutoCalibrationDirectoryEmpty(directory_path)
        # Filter to Bias files if option and give exception if none
        if self._data_model.get_auto_directory_bias_only():
            all_descriptors = list((d for d in all_descriptors if d.get_type() == FileDescriptor.FILE_TYPE_BIAS))
            if len(all_descriptors) == 0:
                raise MasterMakerExceptions.AutoCalibrationNoBiasFiles

        # Get the subset that are the correct size and binning
        correct_size = self.filter_to_correct_size(all_descriptors, sample_file)
        if session_controller.thread_cancelled():
            return None
        if len(correct_size) == 0:
            # No files in that directory are the correct size
            raise MasterMakerExceptions.NoSuitableAutoBias

        # From the correct-sized files, find the one closest to the sample file temperature
        closest_match = self.closest_temperature_match(correct_size, sample_file.get_temperature())
        return closest_match.get_absolute_path()

    def all_descriptors_from_directory(self, directory_path: str,
                                       recursive: bool) -> [FileDescriptor]:
        paths: [str] = SharedUtils.files_in_directory(directory_path, recursive)
        descriptors = RmFitsUtil.make_file_descriptions(paths)
        return descriptors

    def filter_to_correct_size(self, all_descriptors: [FileDescriptor], sample_file: FileDescriptor) \
            -> [FileDescriptor]:
        x_dimension = sample_file.get_x_dimension()
        y_dimension = sample_file.get_y_dimension()
        binning = sample_file.get_binning()
        d: FileDescriptor
        filtered = [d for d in all_descriptors
                    if d.get_x_dimension() == x_dimension
                    and d.get_y_dimension() == y_dimension
                    and d.get_binning() == binning]
        return filtered

    def closest_temperature_match(self, descriptors: [FileDescriptor],
                                  target_temperature: float) -> FileDescriptor:
        best_file_so_far: FileDescriptor = FileDescriptor("dummy-not-used")
        best_difference_so_far = sys.float_info.max
        for descriptor in descriptors:
            this_difference = abs(descriptor.get_temperature() - target_temperature)
            if this_difference < best_difference_so_far:
                best_difference_so_far = this_difference
                best_file_so_far = descriptor
        assert best_file_so_far is not None
        # console.message(f"Selected calibration file {best_file_so_far.get_name()} "
        #                 f"at temperature {best_file_so_far.get_temperature()}", +1, temp=True)
        return best_file_so_far
