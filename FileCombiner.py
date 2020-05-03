#
#   Object for combining FITS files using different algorithms
#
from itertools import groupby
from typing import Callable

import numpy
from sklearn.cluster import MeanShift

import MasterMakerExceptions
from Console import Console
from Constants import Constants
from DataModel import DataModel
from FileDescriptor import FileDescriptor
from ImageMath import ImageMath
from RmFitsUtil import RmFitsUtil
from SessionController import SessionController
from SharedUtils import SharedUtils


class FileCombiner:

    def __init__(self, session_controller: SessionController,
                 file_moved_callback: Callable[[str], None]):
        self.callback_method = file_moved_callback
        self._session_controller = session_controller

    # Process one set of files.  Output to the given path, if provided.  If not provided, prompt the user for it.
    
    def original_non_grouped_processing(self, selected_files: [FileDescriptor],
                                        data_model: DataModel,
                                        output_file: str,
                                        console: Console):
        console.push_level()
        console.message("Using single-file processing", +1)
        # We'll use the first file in the list as a sample for things like image size
        assert len(selected_files) > 0
        # Confirm that these are all bias frames, and can be combined (same binning and dimensions)
        if FileCombiner.all_compatible_sizes(selected_files):
            self.check_cancellation()
            if data_model.get_ignore_file_type() or FileCombiner.all_of_type(selected_files,
                                                                             FileDescriptor.FILE_TYPE_BIAS):
                # Get (most common) filter name in the set
                # Since these are bias frames, the filter is meaningless, but we need the value
                # for the shared "create file" routine
                filter_name = SharedUtils.most_common_filter_name(selected_files)

                # Do the combination
                self.combine_files(selected_files, data_model, filter_name, output_file, console)
                self.check_cancellation()
                # Files are combined.  Put away the inputs?
                substituted_folder_name = SharedUtils.substitute_date_time_filter_in_string(
                    data_model.get_disposition_subfolder_name())
                self.handle_input_files_disposition(data_model.get_input_file_disposition(),
                                                    substituted_folder_name,
                                                    selected_files, console)
            else:
                raise MasterMakerExceptions.NotAllBiasFrames
        else:
            raise MasterMakerExceptions.IncompatibleSizes
        console.message("Combining complete", 0)
        console.pop_level()

    #
    #   Process the given selected files in groups by size, exposure, or temperature (or any combination)
    #
    #   Exceptions thrown:
    #       NoGroupOutputDirectory      Output directory does not exist and unable to create it
    
    def process_groups(self, data_model: DataModel,
                       selected_files: [FileDescriptor],
                       output_directory: str,
                       console: Console):
        console.push_level()
        self.check_cancellation()
        temperature_bandwidth = data_model.get_temperature_group_bandwidth()
        disposition_folder = data_model.get_disposition_subfolder_name()
        substituted_folder_name = SharedUtils.substitute_date_time_filter_in_string(disposition_folder)
        console.message("Process groups into output directory: " + output_directory, +1)
        if not SharedUtils.ensure_directory_exists(output_directory):
            raise MasterMakerExceptions.NoGroupOutputDirectory(output_directory)
        minimum_group_size = data_model.get_minimum_group_size() \
            if data_model.get_ignore_groups_fewer_than() else 0

        #  Process size groups, or all sizes if not grouping
        groups_by_size = self.get_groups_by_size(selected_files, data_model.get_group_by_size())
        grouping_by_size = data_model.get_group_by_size()
        grouping_by_temperature = data_model.get_group_by_temperature()
        for size_group in groups_by_size:
            console.push_level()
            self.check_cancellation()
            # Message about this group only if this grouping was requested
            if len(size_group) < minimum_group_size:
                if grouping_by_size:
                    console.message(f"Ignoring one size group: {len(size_group)} "
                                    f"files {size_group[0].get_size_key()}", +1)
            else:
                if grouping_by_size:
                    console.message(f"Processing one size group: {len(size_group)} "
                                    f"files {size_group[0].get_size_key()}", +1)
                # Within this size group, process temperature groups, or all temperatures if not grouping
                groups_by_temperature = \
                    self.get_groups_by_temperature(size_group,
                                                   data_model.get_group_by_temperature(),
                                                   temperature_bandwidth)
                for temperature_group in groups_by_temperature:
                    console.push_level()
                    self.check_cancellation()
                    (mean_exposure, mean_temperature) = ImageMath.mean_exposure_and_temperature(temperature_group)
                    if len(temperature_group) < minimum_group_size:
                        if grouping_by_temperature:
                            console.message(f"Ignoring one temperature group: {len(temperature_group)} "
                                            f"files with mean temperature {mean_temperature:.1f}", +1)
                    else:
                        if grouping_by_temperature:
                            console.message(f"Processing one temperature group: {len(temperature_group)} "
                                            f"files with mean temperature {mean_temperature:.1f} "
                                            f"({temperature_bandwidth} bandwidth)", +1)
                        # Now we have a list of descriptors, grouped as appropriate, to process
                        self.process_one_group(data_model, temperature_group,
                                               output_directory,
                                               data_model.get_master_combine_method(),
                                               substituted_folder_name,
                                               console)
                    console.pop_level()
            console.pop_level()
        console.message("Group combining complete", 0)
        console.pop_level()

    # Process one group of files, output to the given directory
    #
    #   Exceptions thrown:
    #       NotAllBiasFrames        The given files are not all bias frames
    #       IncompatibleSizes       The given files are not all the same dimensions
    
    def process_one_group(self,
                          data_model: DataModel,
                          descriptor_list: [FileDescriptor],
                          output_directory: str,
                          combine_method: int,
                          disposition_folder_name,
                          console: Console):
        assert len(descriptor_list) > 0
        sample_file: FileDescriptor = descriptor_list[0]
        console.push_level()
        self.describe_group(data_model, len(descriptor_list), sample_file, console)

        # Make up a file name for this group's output, into the given directory
        file_name = SharedUtils.get_file_name_portion(combine_method, sample_file,
                                                      data_model.get_sigma_clip_threshold(),
                                                      data_model.get_min_max_number_clipped_per_end())
        output_file = f"{output_directory}/{file_name}"

        # Confirm that these are all bias frames, and can be combined (same binning and dimensions)
        if self.all_compatible_sizes(descriptor_list):
            if data_model.get_ignore_file_type() \
                    or FileCombiner.all_of_type(descriptor_list, FileDescriptor.FILE_TYPE_BIAS):
                # Get (most common) filter name in the set
                # Since these are bias frames, the filter is meaningless, but we need the value
                # for the shared "create file" routine
                filter_name = SharedUtils.most_common_filter_name(descriptor_list)

                # Do the combination
                self.combine_files(descriptor_list, data_model, filter_name,
                                   output_file, console)
                self.check_cancellation()
                # Files are combined.  Put away the inputs?
                # Return list of any that were moved, in case the UI needs to be adjusted
                self.handle_input_files_disposition(data_model.get_input_file_disposition(),
                                                    disposition_folder_name,
                                                    descriptor_list, console)
            else:
                raise MasterMakerExceptions.NotAllBiasFrames
        else:
            raise MasterMakerExceptions.IncompatibleSizes
        console.pop_level()

    # Move the given files if the given disposition type requests it.
    # Return a list of any files that were moved so the UI can be adjusted if necessary
    
    def handle_input_files_disposition(self,
                                       disposition_type: int,
                                       sub_folder_name: str,
                                       descriptors: [FileDescriptor],
                                       console: Console):
        if disposition_type == Constants.INPUT_DISPOSITION_NOTHING:
            # User doesn't want us to do anything with the input files
            return
        else:
            assert (disposition_type == Constants.INPUT_DISPOSITION_SUBFOLDER)
            console.message("Moving processed files to " + sub_folder_name, 0)
            # User wants us to move the input files into a sub-folder
            for descriptor in descriptors:
                self.check_cancellation()
                if SharedUtils.dispose_one_file_to_sub_folder(descriptor, sub_folder_name):
                    # Successfully moved the file;  tell the user interface
                    self.callback_method(descriptor.get_absolute_path())

    # Determine if all the files in the list are of the given type

    @classmethod
    def all_of_type(cls, selected_files: [FileDescriptor], type_code: int):
        for descriptor in selected_files:
            if descriptor.get_type() != type_code:
                return False
        return True

    # Confirm that the given list of files are combinable by being compatible sizes
    # This means their x,y dimensions are the same and their binning is the same

    @classmethod
    def all_compatible_sizes(cls, selected_files: [FileDescriptor]):
        if len(selected_files) == 0:
            return True
        (x_dimension, y_dimension) = selected_files[0].get_dimensions()
        binning = selected_files[0].get_binning()
        for descriptor in selected_files:
            (this_x, this_y) = descriptor.get_dimensions()
            if this_x != x_dimension or this_y != y_dimension or descriptor.get_binning() != binning:
                return False
        return True

    # Determine if all the files in the list have the same filter name
    
    def all_same_filter(self, selected_files: [FileDescriptor]) -> bool:
        if len(selected_files) == 0:
            return True
        filter_name = selected_files[0].get_filter_name()
        for descriptor in selected_files:
            if descriptor.get_filter_name() != filter_name:
                return False
        return True

    # Determine if all the dimensions are OK to proceed.
    #   All selected files must be the same size and the same binning
    #
    @classmethod
    def validate_file_dimensions(cls, descriptors: [FileDescriptor]) -> bool:
        # Get list of paths of selected files
        if len(descriptors) > 0:

            # Get binning and dimension of first to use as a reference
            assert len(descriptors) > 0
            reference_file: FileDescriptor = descriptors[0]
            reference_binning = reference_file.get_binning()
            reference_x_size = reference_file.get_x_dimension()
            reference_y_size = reference_file.get_y_dimension()

            # Check all files in the list against these specifications
            descriptor: FileDescriptor
            for descriptor in descriptors:
                if descriptor.get_binning() != reference_binning:
                    return False
                if descriptor.get_x_dimension() != reference_x_size:
                    return False
                if descriptor.get_y_dimension() != reference_y_size:
                    return False

        return True

    # Given list of file descriptors, return a list of lists, where each outer list is all the
    # file descriptors with the same size (dimensions and binning)

    def get_groups_by_size(self, selected_files: [FileDescriptor], is_grouped: bool) -> [[FileDescriptor]]:
        if is_grouped:
            descriptors_sorted = sorted(selected_files, key=FileDescriptor.get_size_key)
            descriptors_grouped = groupby(descriptors_sorted, FileDescriptor.get_size_key)
            result: [[FileDescriptor]] = []
            for key, sub_group in descriptors_grouped:
                sub_list = list(sub_group)
                result.append(sub_list)
            return result
        else:
            return [selected_files]   # One group with all the files

    # Given list of file descriptors, return a list of lists, where each outer list is all the
    # file descriptors with the same temperature within a given tolerance
    # Note that, because of the "tolerance" comparison, this is a clustering analysis, not
    # a simple python "groupby", which assumes the values are exact.
    #
    # For this simple 1-dimensional clustering we can use the MeanShift function from
    # the machine learning package, sklearn
    #

    def get_groups_by_temperature(self,
                                  selected_files: [FileDescriptor],
                                  is_grouped: bool,
                                  bandwidth: float) -> [[FileDescriptor]]:
        if is_grouped:
            # We'll get the indices of the temperature clusters, then use those indices
            # on the file descriptors
            result_array: [[FileDescriptor]] = []
            temperatures: [float] = [file.get_temperature() for file in selected_files]
            data_to_cluster = numpy.array(temperatures).reshape(-1, 1)
            mean_shift = MeanShift(bandwidth=bandwidth)
            mean_shift.fit(data_to_cluster)
            arbitrary_cluster_labels = mean_shift.labels_
            # cluster_labels is an array of integers, with each "cluster" having the same integer label
            unique_labels = numpy.unique(arbitrary_cluster_labels)
            # So if we gather the unique label values, that is gathering the clusters
            for label in unique_labels:
                # Flag the items in this cluster
                cluster_membership: [bool] = arbitrary_cluster_labels == label
                # Get the indices of the items in this cluster
                member_indices: [int] = numpy.where(cluster_membership)[0].tolist()
                # Get the descriptors in this cluster and add to the output array
                this_cluster_descriptors: [FileDescriptor] = [selected_files[i] for i in member_indices]
                result_array.append(this_cluster_descriptors)

            # The groups array is in arbitrary order - determined by the clustering algorithm
            # We'd like to have it in a predictable order.  Sort by first temperature in each group
            result_array.sort(key=lambda g: g[0].get_temperature())
            return result_array

        else:
            return [selected_files]   # One group with all the files

    # Combine the given files, output to the given output file
    # Use the combination algorithm given by the radio buttons on the main window
    
    def combine_files(self, input_files: [FileDescriptor],
                      data_model: DataModel,
                      filter_name: str,
                      output_path: str,
                      console: Console):
        console.push_level()
        substituted_file_name = SharedUtils.substitute_date_time_filter_in_string(output_path)
        file_names = [d.get_absolute_path() for d in input_files]
        combine_method = data_model.get_master_combine_method()
        # Get info about any precalibration that is to be done
        assert len(input_files) > 0
        binning: int = input_files[0].get_binning()
        (mean_exposure, mean_temperature) = ImageMath.mean_exposure_and_temperature(input_files)
        if combine_method == Constants.COMBINE_MEAN:
            mean_data = ImageMath.combine_mean(file_names, console, self._session_controller)
            self.check_cancellation()
            RmFitsUtil.create_combined_fits_file(substituted_file_name, mean_data,
                                                 FileDescriptor.FILE_TYPE_BIAS,
                                                 "Bias Frame",
                                                 mean_exposure, mean_temperature, filter_name, binning,
                                                 "Master Bias MEAN combined")
        elif combine_method == Constants.COMBINE_MEDIAN:
            median_data = ImageMath.combine_median(file_names, console, self._session_controller)
            self.check_cancellation()
            RmFitsUtil.create_combined_fits_file(substituted_file_name, median_data,
                                                 FileDescriptor.FILE_TYPE_BIAS,
                                                 "Bias Frame",
                                                 mean_exposure, mean_temperature, filter_name, binning,
                                                 "Master Bias MEDIAN combined")
        elif combine_method == Constants.COMBINE_MINMAX:
            number_dropped_points = data_model.get_min_max_number_clipped_per_end()
            min_max_clipped_mean = ImageMath.combine_min_max_clip(file_names, number_dropped_points,
                                                                  console, self._session_controller)
            self.check_cancellation()
            assert min_max_clipped_mean is not None
            RmFitsUtil.create_combined_fits_file(substituted_file_name, min_max_clipped_mean,
                                                 FileDescriptor.FILE_TYPE_BIAS,
                                                 "Bias Frame",
                                                 mean_exposure, mean_temperature, filter_name, binning,
                                                 f"Master Bias Min/Max Clipped "
                                                 f"(drop {number_dropped_points}) Mean combined")
        else:
            assert combine_method == Constants.COMBINE_SIGMA_CLIP
            sigma_threshold = data_model.get_sigma_clip_threshold()
            sigma_clipped_mean = ImageMath.combine_sigma_clip(file_names, sigma_threshold,
                                                              console, self._session_controller)
            self.check_cancellation()
            assert sigma_clipped_mean is not None
            RmFitsUtil.create_combined_fits_file(substituted_file_name, sigma_clipped_mean,
                                                 FileDescriptor.FILE_TYPE_BIAS,
                                                 "Bias Frame",
                                                 mean_exposure, mean_temperature, filter_name, binning,
                                                 f"Master Bias Sigma Clipped "
                                                 f"(threshold {sigma_threshold}) Mean combined")
        console.pop_level()

    def describe_group(self, data_model: DataModel, number_files: int, sample_file: FileDescriptor, console: Console):
        binning = sample_file.get_binning()
        temperature = sample_file.get_temperature()
        processing_message = ""
        if data_model.get_group_by_size():
            processing_message += f"binned {binning} x {binning}"
        if data_model.get_group_by_temperature():
            if len(processing_message) > 0:
                processing_message += ","
            processing_message += f" at {temperature} degrees."
        console.message(f"Processing {number_files} files {processing_message}", +1)

    def check_cancellation(self):
        if self._session_controller.thread_cancelled():
            raise MasterMakerExceptions.SessionCancelled
