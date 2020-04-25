#
#   Class used to handle processing when the program is running in pure command line mode
#   (i.e. no GUI interface).
#

import os
from datetime import datetime

import MasterMakerExceptions
from ConsoleSimplePrint import ConsoleSimplePrint
from Constants import Constants
from DataModel import DataModel
from FileCombiner import FileCombiner
from FileDescriptor import FileDescriptor
from RmFitsUtil import RmFitsUtil
from SessionController import SessionController


class CommandLineHandler:

    def __init__(self, args, data_model: DataModel):
        self._args = args
        self._data_model: DataModel = data_model

    def execute(self):
        """Execute the program with the options specified on the command line, no GUI"""
        valid: bool
        file_names: [str]
        single_output_path: str
        (valid, single_output_path, file_names) = self.validate_inputs()
        if valid:
            groups_output_directory = self._args.outputdirectory
            if self.process_files(file_names, single_output_path, groups_output_directory):
                print("Successful completion")

    # Make sure the command-line inputs are valid.  Fill in any give parameters into the existing
    # data model (which is already set up with defaults).
    # Check the following:
    #   -   One or more input files, and all files exist
    #   -   If a min-max clip value is specified, it is > 0
    #   -   If a sigma threshold is specified, it is > 0
    #   -   If -gt used, threshold is 0 to 100
    #   -   If -mg used, group size is > 0
    #   Returns:  validity flag, output path if specified, array of file names

    def validate_inputs(self) -> (bool, [str]):
        """Validate command-line arguments and consolidate them with preferences for any missing settings"""
        valid = True
        args = self._args
        file_names = []
        output_path = ""

        # File names
        if len(args.filenames) > 0:
            for file_name in args.filenames:
                if os.path.isfile(file_name):
                    # This file is OK, we're good here
                    pass
                else:
                    print(f"File does not exist: {file_name}")
                    valid = False
            file_names = args.filenames
        else:
            print("No file names given")
            valid = False

        # Master frame combination algorithm and parameters
        if args.mean:
            print(f"   Setting MEAN combination")
            self._data_model.set_master_combine_method(Constants.COMBINE_MEAN)
        elif args.median:
            print(f"   Setting MEDIAN combination")
            self._data_model.set_master_combine_method(Constants.COMBINE_MEDIAN)
        elif args.minmax is not None:
            self._data_model.set_master_combine_method(Constants.COMBINE_MINMAX)
            if args.minmax >= 1:
                print(f"   Setting MIN-MAX combination, clipping {args.minmax} extremes")
                self._data_model.set_min_max_number_clipped_per_end(args.minmax)
            else:
                print(f"Min-Max clipping argument must be > 0, not {args.minmax}")
                valid = False
        elif args.sigma is not None:
            self._data_model.set_master_combine_method(Constants.COMBINE_SIGMA_CLIP)
            if args.sigma > 0:
                print(f"   Setting SIGMA combination, z-threshold = {args.sigma}")
                self._data_model.set_sigma_clip_threshold(args.sigma)
            else:
                print(f"Sigma clipping threshold must be > 0, not {args.sigma}")
                valid = False

        # Insist on same file type in all files?
        if args.ignoretype:
            print(f"   Ignoring file types")
            self._data_model.set_ignore_file_type(True)

        # What to do with input files after a successful run
        if args.moveinputs is not None:
            self._data_model.set_input_file_disposition(Constants.INPUT_DISPOSITION_SUBFOLDER)
            self._data_model.set_disposition_subfolder_name(args.moveinputs)
            print(f"   After processing move files to {args.moveinputs}")

        # Where should output files go?
        if args.output is not None:
            print(f"   Output path: {args.output}")
            output_path = args.output

        # Grouping   gs   ge <threshold>   gt <threshold>  mg <minimum>
        #   -   If -ge used, threshold is 0 to 100
        #   -   If -gt used, threshold is 0 to 100
        #   -   If -mg used, group size is > 0
        if args.groupsize:
            print("   Group files by size")
            self._data_model.set_group_by_size(True)
        if args.groupexposure is not None:
            self._data_model.set_group_by_exposure(True)
            tolerance = float(args.groupexposure)
            if 0 <= tolerance <= 100:
                print(f"   Group files by exposure with tolerance {tolerance}%")
                self._data_model.set_exposure_group_tolerance(tolerance / 100.0)
            else:
                print("-ge tolerance must be between 0 and 100")
                valid = False
        if args.grouptemperature is not None:
            self._data_model.set_group_by_temperature(True)
            tolerance = float(args.grouptemperature)
            if 0 <= tolerance <= 100:
                print(f"   Group files by temperature with tolerance {tolerance}%")
                self._data_model.set_temperature_group_tolerance(tolerance / 100.0)
            else:
                print("-gt tolerance must be between 0 and 100")
                valid = False
        if args.minimumgroup is not None:
            self._data_model.set_ignore_groups_fewer_than(True)
            minimum_size = int(args.minimumgroup)
            if minimum_size > 0:
                print(f"   Ignore groups smaller than {minimum_size}")
                self._data_model.set_minimum_group_size(minimum_size)
            else:
                print(f"   Minimum group size must be > 0, not {minimum_size}")
                valid = False

        # If any of the grouping options are in use, then the output directory is mandatory
        if self._data_model.get_group_by_temperature() or self._data_model.get_group_by_exposure() \
                or self._data_model.get_group_by_size():
            if args.outputdirectory is None:
                print("If any of the group-by options are used, then the output directory option is mandatory")
                valid = False

        return valid, output_path, file_names

    #   The main processing method that combines the files using the selected algorithm

    def process_files(self, file_names: [str], output_path: str, groups_output_directory: str) -> bool:
        """Process all the files listed in the command line, with the given combination settings"""
        success = True
        file_descriptors = RmFitsUtil.make_file_descriptions(file_names)
        # check types are all bias
        if self._data_model.get_ignore_file_type() \
                or FileCombiner.all_of_type(file_descriptors, FileDescriptor.FILE_TYPE_BIAS):
            output_file_path = self.make_output_path(output_path, file_descriptors)
            self.run_combination_session(file_descriptors, output_file_path, groups_output_directory)
        else:
            print("Files are not all Bias files.  (Use -t option to suppress this check.)")
            success = False
        return success

    def run_combination_session(self, descriptors: [FileDescriptor], output_path: str, output_directory: str):
        # Create a console output object.  This is passed in to the various math routines
        # to allow them to output progress.  We use this indirect method of getting progress
        # so that it can go to the console window in this case, but the same worker code can send
        # progress lines to the standard system output when being run from the command line
        console = ConsoleSimplePrint()
        console.message("Starting session", 0)
        file_combiner = FileCombiner(self.file_moved_callback)
        # A "session controller" is necessary, but has an interesting effect only in the GUI version
        # In our command-line case we'll create it but its state will never change so it does nothing
        dummy_session_controller = SessionController()

        # Do the file combination - two methods depending on whether we are processing by groups
        try:
            # Are we using grouped processing?
            if self._data_model.get_group_by_exposure() \
                    or self._data_model.get_group_by_size() \
                    or self._data_model.get_group_by_temperature():
                file_combiner.process_groups(self._data_model, descriptors,
                                             output_directory,
                                             console, dummy_session_controller)
            else:
                # Not grouped, producing a single output file. Get output file location
                file_combiner.original_non_grouped_processing(descriptors, self._data_model,
                                                              output_path,
                                                              console, dummy_session_controller)
        except FileNotFoundError as exception:
            self.error_dialog("File not found", f"File \"{exception.filename}\" not found or not readable")
        except MasterMakerExceptions.NoGroupOutputDirectory as exception:
            self.error_dialog("Group Directory Missing",
                              f"The specified output directory \"{exception.get_directory_name()}\""
                              f" does not exist and could not be created.")
        except MasterMakerExceptions.NotAllBiasFrames:
            self.error_dialog("The selected files are not all Bias Frames",
                              "If you know the files are bias frames, they may not have proper FITS data "
                              "internally. Check the \"Ignore FITS file type\" box to proceed anyway.")
        except MasterMakerExceptions.IncompatibleSizes:
            self.error_dialog("The selected files can't be combined",
                              "To be combined into a master file, the files must have identical X and Y "
                              "dimensions, and identical Binning values.")
        except PermissionError as exception:
            self.error_dialog("Unable to write file",
                              f"The specified output file, "
                              f"\"{exception.filename}\","
                              f" cannot be written or replaced: \"permission error\"")

    # Make output file name.
    # If file name is specified on command line, use that.
    # Otherwise make up a file name and a path that places it in the same
    # location as the first input file.

    def make_output_path(self,
                         output_path_parameter,
                         file_descriptors: [FileDescriptor]) -> str:
        """Create a suitable output file name, fully-qualified"""
        if output_path_parameter == "":
            return self.create_output_path(file_descriptors[0], self._data_model.get_master_combine_method())
        else:
            return output_path_parameter

    # Create a file name for the output file
    #   of the form Bias-Mean-yyyymmddhhmm-temp-x-y-bin.fit
    @classmethod
    def create_output_path(cls, sample_input_file: FileDescriptor, combine_method: int):
        """Create an output file name in the case where one wasn't specified"""
        # Get directory of sample input file
        directory_prefix = os.path.dirname(sample_input_file.get_absolute_path())
        file_name = cls.get_file_name_portion(combine_method, sample_input_file)
        file_path = f"{directory_prefix}/{file_name}"
        return file_path

    @classmethod
    def get_file_name_portion(cls, combine_method, sample_input_file):
        # Get other components of name
        now = datetime.now()
        date_time_string = now.strftime("%Y%m%d-%H%M")
        temperature = f"{sample_input_file.get_temperature():.1f}"
        exposure = f"{sample_input_file.get_exposure():.3f}"
        dimensions = f"{sample_input_file.get_x_dimension()}x{sample_input_file.get_y_dimension()}"
        binning = f"{sample_input_file.get_binning()}x{sample_input_file.get_binning()}"
        method = Constants.combine_method_string(combine_method)
        file_name = f"BIAS-{method}-{date_time_string}-{exposure}s-{temperature}C-{dimensions}-{binning}.fit"

        return file_name

    def file_moved_callback(self, file_name_moved: str):
        print(f"file_moved_callback: {file_name_moved}")
        pass
        # We ignore the callback telling us a file was moved.  No UI needs to be updated

    #
    #   Error message from an exception.  Put it on the console
    #
    def error_dialog(self, short_message: str, long_message: str):
        print("*** ERROR *** " + short_message + ":\n   " + long_message)
