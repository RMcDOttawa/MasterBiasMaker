# Utilities to help program run on multiple OS - for now, windows and mac
# Helps locate resource files, end-running around the problems I've been having
# with the various native bundle packaging utilities that I can't get working
import os
import shutil
import sys
import glob
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

from Constants import Constants
from FileDescriptor import FileDescriptor
from Validators import Validators


class SharedUtils:
    VALID_FIELD_BACKGROUND_COLOUR = "white"
    _error_red = 0xFC  # These RGB values generate a medium red,
    _error_green = 0x84  # not too dark to read black text through
    _error_blue = 0x84
    ERROR_FIELD_BACKGROUND_COLOUR = f"#{_error_red:02X}{_error_green:02X}{_error_blue:02X}"

    @classmethod
    def valid_or_error_field_color(cls, validity: bool) -> QColor:
        """
        Return a QT colour for a form field that is valid (white) or in error (light red)
        :param validity:    Flag if valid or not
        :return:            QColour for field
        """
        if validity:
            result = QColor(Qt.white)
        else:
            result = QColor(cls._error_red, cls._error_green, cls._error_blue)
        return result

    # # Generate a file's full path, given the file name, and having the
    # # file reside in the same directory where the running program resides
    #

    @classmethod
    def background_validity_color(cls, field: QWidget, is_valid: bool):
        """
        set background colour of field if it has not passed validation
        :param field:       Field (QWidget) whose background to set
        :param is_valid:    Flag that field is valid
        """
        field_color = SharedUtils.VALID_FIELD_BACKGROUND_COLOUR \
            if is_valid else SharedUtils.ERROR_FIELD_BACKGROUND_COLOUR
        css_color_item = f"background-color:{field_color};"
        existing_style_sheet = field.styleSheet()
        field.setStyleSheet(existing_style_sheet + css_color_item)

    @classmethod
    def validate_folder_name(cls, proposed: str):
        """
        Validate the proposed file name.  It must be a legit system file name, except
        it can also contain the strings %d or %t or %f zero or more times each.  We'll
        just remove those temporarily for purposes of validation.
        :param proposed:    File name we're thinking of using
        :return:            Indicator that it's valid (syntactically, no availability test)
        """
        upper = proposed.upper()
        specials_removed = upper.replace("%D", "").replace("%T", "").replace("%F", "")
        return Validators.valid_file_name(specials_removed, 1, 31)

    # In given string, replace all occurrences of %d with date and %t with time
    # In YYYY-MM-DD  and HH-MM-SS formats

    @classmethod
    def substitute_date_time_filter_in_string(cls, output_path: str) -> str:
        """
        In given string, replace all occurrences of %d with date and %t with time
        In YYYY-MM-DD  and HH-MM-SS formats
        :param output_path:     String to be substituted
        :return:                String with substitutions made
        """
        now = datetime.now()
        year = now.strftime("%Y-%m-%d")
        time = now.strftime("%H-%M-%S")
        return output_path.replace("%d", year).replace("%D", year).replace("%t", time).replace("%T", time)

    @classmethod
    def most_common_filter_name(cls, descriptors: [FileDescriptor]) -> str:
        """
        Find the most common filter name in the given list of files
        :param descriptors:     List of files to check
        :return:                String of most common filter name
        """
        filter_counts: {str, int} = {}
        for descriptor in descriptors:
            name = descriptor.get_filter_name()
            if name in filter_counts:
                filter_counts[name] += 1
            else:
                filter_counts[name] = 1
        maximum_key = max(filter_counts, key=filter_counts.get)
        return maximum_key if maximum_key is not None else ""

    @classmethod
    def dispose_one_file_to_sub_folder(cls, descriptor, sub_folder_name) -> bool:
        """
        Move a file to a sub-folder of the given name in the same directory
        :param descriptor:          Descriptor of the file to be moved
        :param sub_folder_name:     Name of sub-directory to receive file
        :return:                    Boolean indicator of success
        """
        success = False
    # Get folder name with special values substituted
        subfolder_located_directory = cls.make_name_a_subfolder(descriptor, sub_folder_name)

        # Create the folder if it doesn't already exist (and make sure we're not clobbering a file)
        if cls.ensure_directory_exists(subfolder_located_directory):
            source_path = descriptor.get_absolute_path()
            source_name = descriptor.get_name()
            destination_path = cls.unique_destination_file(subfolder_located_directory, source_name)
            result = shutil.move(source_path, destination_path)
            success = result == destination_path
        return success

    # Given a desired sub-directory name, make it a sub-directory of the location of the input files
    # by putting the path to a sample input file on the front of the name

    @classmethod
    def make_name_a_subfolder(cls, sample_input_file: FileDescriptor, sub_directory_name: str) -> str:
        parent_path = os.path.dirname(sample_input_file.get_absolute_path())
        """
        Given a desired sub-directory name, make it a sub-directory of the location of the input files
        by putting the path to a sample input file on the front of the name
        :param sample_input_file:       Desc of file that locates the base directory
        :param sub_directory_name:      Name of subdirectory to be created
        :return:                        Full absolute path of subdirectory under location of desc
        """
        return os.path.join(parent_path, sub_directory_name)

    # Make sure the given directory exists, as a directory.
    #   - No non-directory file of that name (fail if so)
    #   - If directory already exists as a directory, all good; succeed
    #   - If no such directory exists, create it

    @classmethod
    def ensure_directory_exists(cls, directory_name) -> bool:
        """
        Make sure the given directory exists, as a directory.
          - No non-directory file of that name (fail if so)
          - If directory already exists as a directory, all good; succeed
          - If no such directory exists, create it

        :param directory_name:      Name of directory to be verified or created
        :return:                    Boolean indicator of success
        """
        success: bool
        if os.path.exists(directory_name):
            # There is something there with this name.  That's OK if it's a directory.
            if os.path.isdir(directory_name):
                # The directory exists, this is OK, no need to create it
                success = True
            else:
                # A file exists that conflicts with the desired directory
                # Display an error and fail
                print("A file (not a directory) already exists with the name and location "
                      "you specified. Choose a different name or location.")
                success = False
        else:
            # Nothing of that name exists.  Make a directory
            os.mkdir(directory_name)
            success = True

        return success

    # Create a file name for the output file
    #   of the form Bias-Mean-yyyymmddhhmm-temp-x-y-bin.fit

    @classmethod
    def create_output_path(cls, sample_input_file: FileDescriptor, combine_method: int,
                                              sigma_threshold, min_max_clipped):
        """
        Create a file name for the output file of the form Flat-Mean-yyyymmddhhmm-temp-x-y-bin.fit
        :param sample_input_file:       Descriptor of file providing metadata
        :param combine_method:          Combine method used to create output
        :param sigma_threshold:         Sigma threshold if sigma-clip used
        :param min_max_clipped:         Clipping count if min-max-clip used
        :return:                        String of created file name
        """
        # Get directory of sample input file
        directory_prefix = os.path.dirname(sample_input_file.get_absolute_path())
        file_name = cls.get_file_name_portion(combine_method, sample_input_file,
                                              sigma_threshold, min_max_clipped)
        file_path = f"{directory_prefix}/{file_name}"
        return file_path

    @classmethod
    def get_file_name_portion(cls, combine_method, sample_input_file,
                                              sigma_threshold, min_max_clipped):
        """
        Make up the file name portion of a name for a file with given metadata
        :param combine_method:      How were inputs combined to make this file?
        :param sample_input_file:   Sample of the input files for their metadata
        :param sigma_threshold:     Sigma threshold if sigma clip was used
        :param min_max_clipped:     Min-Max drop count if min-max was used
        :return:                    String of file name (not full path, just name)
        """
        # Get other components of name
        now = datetime.now()
        date_time_string = now.strftime("%Y%m%d-%H%M")
        temperature = f"{sample_input_file.get_temperature():.1f}"
        exposure = f"{sample_input_file.get_exposure():.3f}"
        # dimensions = f"{sample_input_file.get_x_dimension()}x{sample_input_file.get_y_dimension()}"
        # Removed dimensions from file name - cluttered and not needed with binning included
        binning = f"{sample_input_file.get_binning()}x{sample_input_file.get_binning()}"
        method = Constants.combine_method_string(combine_method)
        if combine_method == Constants.COMBINE_SIGMA_CLIP:
            method += str(sigma_threshold)
        elif combine_method == Constants.COMBINE_MINMAX:
            method += str(min_max_clipped)
        file_name = f"BIAS-{method}-{date_time_string}-{exposure}s-{temperature}C-{binning}.fit"

        return file_name

    @classmethod
    def create_output_directory(cls, sample_input_file: FileDescriptor, combine_method: int):
        """
        Create a suggested directory for the output files from group processing
        of the form Flat-Mean-Groups-yyyymmddhhmm

        :param sample_input_file:   Sample of combined input files, for metadata
        :param combine_method:      How were the input files combined
        :return:                    Suggested directory name incorporating metadata
        """
        # Get directory of sample input file
        directory_prefix = os.path.dirname(sample_input_file.get_absolute_path())

        # Get other components of name
        now = datetime.now()
        date_time_string = now.strftime("%Y%m%d-%H%M")
        method = Constants.combine_method_string(combine_method)

        # Make name
        file_path = f"{directory_prefix}/BIAS-{method}-Groups-{date_time_string}"
        return file_path

    @classmethod
    def unique_destination_file(cls, directory_path: str, file_name: str) -> str:
        """
        In case the disposition directory already existed and has files in it, ensure the
        given file would be unique in the directory, by appending a number to it if necessary
        :param directory_path:  Directory path where file will be placed
        :param file_name:       File name we'd like to use
        :return:                File name modified, if necessary, to be unique in directory
        """
        unique_counter = 0

        destination_path = os.path.join(directory_path, file_name)
        while os.path.exists(destination_path):
            unique_counter += 1
            if unique_counter > 5000:
                print("Unable to find a unique file name after 5000 tries.")
                sys.exit(1)
            destination_path = os.path.join(directory_path, str(unique_counter) + "-" + file_name)

        return destination_path

    # Determine if two values are the same within a given tolerance.
    # Careful - either value might be zero, so divide only after checking

    @classmethod
    def values_same_within_tolerance(cls, first_value: float, second_value: float, tolerance: float):
        """
        Determine if two values are the same within a given tolerance.
        :param first_value:         First of two values to be compared
        :param second_value:        Second of two values to be compared
        :param tolerance:           Percent tolerance, as a float between 0 and 1
        :return:
        """
        difference = abs(first_value - second_value)
        if first_value == 0.0:
            if second_value == 0.0:
                return True
            else:
                percent_difference = difference / abs(second_value)
        else:
            percent_difference = difference / abs(first_value)
        return percent_difference <= tolerance

    @classmethod
    def files_in_directory(cls, directory_path: str, recursive: bool) -> [str]:
        """
        Get list of all FITS file names in directory, optionally recursive into subdirectories
        :param directory_path:      Directory whose contents are to be listed
        :param recursive:           Should recursive descent be used?
        :return:                    List of names of files ending in .FIT or .FITS (case insensitive)
        """
        search_string = os.path.join(directory_path, "**")
        all_files = glob.glob(search_string, recursive=recursive)
        result_list = (f for f in all_files if f.lower().endswith(".fit") or f.lower().endswith(".fits"))
        # contents = os.listdir(directory_path)
        # result_list: [str] = []
        # for entry in contents:
        #     full_path = os.path.join(directory_path, entry)
        #     if os.path.isfile(full_path):  # Ignore subdirectories
        #         name_lower = full_path.lower()
        #         if name_lower.endswith(".fit") or name_lower.endswith(".fits"):  # Only FITS files
        #             result_list.append(full_path)
        return list(result_list)
