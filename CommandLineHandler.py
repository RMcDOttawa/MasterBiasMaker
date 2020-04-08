#
#   Class used to handle processing when the program is running in pure command line mode
#   (i.e. no GUI interface).
#

import os
from datetime import datetime
import numpy
from CommandLineParameters import CommandLineParameters
from Constants import Constants
from FileDescriptor import FileDescriptor
from Preferences import Preferences
from RmFitsUtil import RmFitsUtil
from SharedUtils import SharedUtils


class CommandLineHandler:

    def __init__(self, args, preferences: Preferences):
        self._args = args
        self._preferences: Preferences = preferences

    def execute(self):
        """Execute the program with the options specified on the command line, no GUI"""
        command_parameters: CommandLineParameters
        (inputs_valid, command_parameters) = self.validate_inputs()
        if inputs_valid:
            if self.process_files(command_parameters):
                print("Successful completion")

    # Make sure the command-line inputs are valid.  Return all the parameters needed
    # to run the combination.  Where parameters aren't specified in the command line,
    # use appropriate values from the predefined preferences instead
    # Check the following:
    #   -   One or more input files, and all files exist
    #   -   If a bias file is specified, it exists
    #   -   If a pedestal value is specified, it is > 0
    #   -   If a min-max clip value is specified, it is > 0
    #   -   If a sigma threshold is specified, it is > 0

    def validate_inputs(self) -> (bool, CommandLineParameters):
        """Validate command-line arguments and consolidate them with preferences for any missing settings"""
        parameters = CommandLineParameters()
        valid = True
        args = self._args

        # File names
        if len(args.filenames) > 0:
            for file_name in args.filenames:
                if os.path.isfile(file_name):
                    # This file is OK, we're good here
                    pass
                else:
                    print(f"File does not exist: {file_name}")
                    valid = False
            parameters.set_file_names(args.filenames)
        else:
            print("No file names given")
            valid = False

        # Pre-calibration method and related info

        precalibration_type: int
        if args.noprecal:
            precalibration_type = Constants.CALIBRATION_NONE
        elif args.pedestal is not None:
            precalibration_type = Constants.CALIBRATION_PEDESTAL
            if args.pedestal > 0:
                parameters.set_pedestal(args.pedestal)
            else:
                print(f"Pedestal value must be greater than zero, not {args.pedestal}")
                valid = False
        elif args.bias is not None:
            precalibration_type = Constants.CALIBRATION_FIXED_FILE
            if os.path.isfile(args.bias):
                parameters.set_fixed_calibration_file(args.bias)
            else:
                print(f"Calibration file does not exist: {args.bias}")
                valid = False
        else:
            # Nothing in the command line, use preferences.
            precalibration_type = self._preferences.get_precalibration_type()
            parameters.set_pedestal(self._preferences.get_precalibration_pedestal())
            parameters.set_fixed_calibration_file(self._preferences.get_precalibration_fixed_path())
            if precalibration_type == Constants.CALIBRATION_PROMPT:
                print("No precalibration method specified.  Preferences says \"prompt user\""
                      " but that method is not allowed unless running the GUI")
                valid = False
        parameters.set_pre_calibration_type(precalibration_type)

        # Master frame combination algorithm and parameters
        combination_type: int
        if args.mean:
            combination_type = Constants.COMBINE_MEAN
        elif args.median:
            combination_type = Constants.COMBINE_MEDIAN
        elif args.minmax is not None:
            combination_type = Constants.COMBINE_MINMAX
            if args.minmax >= 1:
                parameters.set_min_max_drop(args.minmax)
            else:
                print(f"Min-Max clipping argument must be > 0, not {args.minmax}")
                valid = False
        elif args.sigma is not None:
            combination_type = Constants.COMBINE_SIGMA_CLIP
            if args.sigma > 0:
                parameters.set_sigma_threshold(args.sigma)
            else:
                print(f"Sigma clipping threshold must be > 0, not {args.sigma}")
                valid = False
        else:
            # Nothing in the command line, get combination method from preferences
            print("Using combine method from preferences")
            combination_type = self._preferences.get_master_combine_method()
            parameters.set_min_max_drop(self._preferences.get_min_max_number_clipped_per_end())
            parameters.set_sigma_threshold(self._preferences.get_sigma_clip_threshold())
        parameters.set_combine_method(combination_type)

        # Insist on same file type and same filter name in all files?
        if args.ignoretype:
            parameters.set_ignore_fits_type(True)
        if args.ignorefilter:
            parameters.set_ignore_filter_type(True)

        # What to do with input files after a successful run
        if args.moveinputs is not None:
            parameters.set_disposition_move(True)
            parameters.set_disposition_folder(args.moveinputs)

        # Where should output files go?
        if args.output is not None:
            parameters.set_output_path(args.output)

        return valid, parameters

    #   The main processing method that combines the files using the selected algorithm

    def process_files(self, parameters: CommandLineParameters) -> bool:
        """Process all the files listed in the command line, with the given combination settings"""
        success = True
        file_descriptors = self.get_file_descriptors(parameters.get_file_names())
        # check sizes are all the same
        if RmFitsUtil.all_compatible_sizes(file_descriptors):
            # check types are all flat
            if parameters.get_ignore_fits_type() \
                    or RmFitsUtil.all_of_type(file_descriptors, FileDescriptor.FILE_TYPE_FLAT):
                # check filter names are all the same
                if parameters.get_ignore_filter_type() \
                        or RmFitsUtil.all_same_filter(file_descriptors):
                    output_filter_name = self.get_output_filter_name(file_descriptors)
                    output_file_path = self.make_output_path(parameters, file_descriptors, output_filter_name)
                    self.write_combined_files(parameters, output_file_path, output_filter_name)
                    self.input_file_disposition(parameters, file_descriptors, output_filter_name)
                else:
                    print("Files do not all have same filter name. (Use -f to suppress this check.)")
                    success = False
            else:
                print("Files are not all flats.  (Use -t option to suppress this check.)")
                success = False
        else:
            print("Files are not all the same image dimensions, aborting.")
            success = False
        return success

    # Get list of file descriptors for the given file names

    def get_file_descriptors(self, file_names: [str]) -> [FileDescriptor]:
        """Change list of file names into list of file descriptors including FITS file metadata"""
        result: [FileDescriptor] = []
        for file_name in file_names:
            descriptor = RmFitsUtil.make_file_descriptor(file_name)
            result.append(descriptor)
        return result

    # Make output file name.
    # If file name is specified on command line, use that.
    # Otherwise make up a file name and a path that places it in the same
    # location as the first input file.

    def make_output_path(self,
                         parameters: CommandLineParameters,
                         file_descriptors: [FileDescriptor],
                         filter_name: str) -> str:
        """Create a suitable output file name, fully-qualified"""
        if parameters.get_output_path() == "":
            return self.create_output_path(file_descriptors[0], filter_name)
        else:
            return parameters.get_output_path()

    #
    # Get the filter name to use in the created FITs file.  We'll use the most common
    # filter from the input files (which hopefully have all the same filter)
    #
    def get_output_filter_name(self, file_descriptors: [FileDescriptor]) -> str:
        """Get a filter name suitable to use in the output file metadata"""
        return SharedUtils.most_common_filter_name(file_descriptors)

    #
    #   Create a combined master flat file usign the given algorithm and write it to the output file
    #
    def write_combined_files(self,
                             parameters: CommandLineParameters,
                             output_file_path: str,
                             output_filter_name: str):
        """Combine files to a master flat, written to the given-named output file"""
        pre_calibrate: bool
        pedestal_value: int
        calibration_image: numpy.ndarray
        combination_method = parameters.get_combine_method()
        file_names = parameters.get_file_names()
        (pre_calibrate, pedestal_value, calibration_image) = self.get_precalibration_info(parameters)

        if combination_method == Constants.COMBINE_MEAN:
            mean_data = RmFitsUtil.combine_mean(file_names, pre_calibrate, pedestal_value, calibration_image)
            if mean_data is not None:
                (mean_exposure, mean_temperature) = \
                    RmFitsUtil.mean_exposure_and_temperature(parameters.get_file_names())
                RmFitsUtil.create_combined_fits_file(output_file_path, mean_data,
                                                     mean_exposure, mean_temperature, output_filter_name,
                                                     "Master flat MEAN combined")
        elif combination_method == Constants.COMBINE_MEDIAN:
            median_data = RmFitsUtil.combine_median(file_names, pre_calibrate, pedestal_value, calibration_image)
            if median_data is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(output_file_path, median_data,
                                                     mean_exposure, mean_temperature, output_filter_name,
                                                     "Master flat MEDIAN combined")
        elif combination_method == Constants.COMBINE_MINMAX:
            number_dropped_points = parameters.get_min_max_drop()
            min_max_clipped_mean = RmFitsUtil.combine_min_max_clip(file_names, number_dropped_points,
                                                                   pre_calibrate, pedestal_value, calibration_image)
            if min_max_clipped_mean is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(output_file_path, min_max_clipped_mean,
                                                     mean_exposure, mean_temperature, output_filter_name,
                                                     f"Master flat Min/Max Clipped "
                                                     f"(drop {number_dropped_points}) Mean combined")
        else:
            assert combination_method == Constants.COMBINE_SIGMA_CLIP
            sigma_threshold = parameters.get_sigma_threshold()
            sigma_clipped_mean = RmFitsUtil.combine_sigma_clip(file_names, sigma_threshold,
                                                               pre_calibrate, pedestal_value, calibration_image)
            if sigma_clipped_mean is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(output_file_path, sigma_clipped_mean,
                                                     mean_exposure, mean_temperature, output_filter_name,
                                                     f"Master flat Sigma Clipped "
                                                     f"(threshold {sigma_threshold}) Mean combined")

    #   Get the pre-calibration info for the combine routines
    #   (pre_calibrate, pedestal_value, calibration_image) = self.get_precalibration_info()

    def get_precalibration_info(self, parameters: CommandLineParameters):
        """Consolidate information about precalibration to a single object for easy reference"""
        pre_calibration: bool
        pedestal_value = None
        image_data = None
        calibration_type = parameters.get_pre_calibration_type()

        if calibration_type == Constants.CALIBRATION_PEDESTAL:
            pre_calibration = True
            pedestal_value = parameters.get_pedestal()
        elif calibration_type == Constants.CALIBRATION_FIXED_FILE:
            pre_calibration = True
            image_data = RmFitsUtil.fits_data_from_path(parameters.get_fixed_calibration_file())
        else:
            assert calibration_type == Constants.CALIBRATION_NONE
            pre_calibration = False
        return pre_calibration, pedestal_value, image_data

    # Create a file name for the output file
    #   of the form MASTER-FLAT-yyyy-mm-dd-hh-mm-FLAT-temp-x-y-bin-filter.fit

    def create_output_path(self, sample_input_file: FileDescriptor, filter_name: str):
        """Create an output file name in the case where one wasn't specified"""
        # Get directory of sample input file
        directory_prefix = os.path.dirname(sample_input_file.get_absolute_path())

        # Get other components of name
        now = datetime.now()
        date_time_string = now.strftime("%Y-%m-%d-%H-%M")
        temperature = f"{sample_input_file.get_temperature():.1f}"
        dimensions = f"{sample_input_file.get_x_dimension()}x{sample_input_file.get_y_dimension()}"
        binning = f"{sample_input_file.get_binning()}x{sample_input_file.get_binning()}"

        # Make name
        file_path = f"{directory_prefix}/MASTER-FLAT-{date_time_string}-{temperature}-{dimensions}" \
                    f"-{binning}-{filter_name}.fit"
        return file_path

    # Check if the user wanted us to move the input files after combining them.
    # If so, move them to the named subdirectory

    def input_file_disposition(self, parameters: CommandLineParameters,
                               descriptors: [FileDescriptor],
                               filter_name: str):
        """Dispose of input files if so requested"""
        if parameters.get_disposition_move():
            # User wants us to move the input files into a sub-folder
            SharedUtils.dispose_files_to_sub_folder(descriptors, parameters.get_disposition_folder(), filter_name)
