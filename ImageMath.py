#
#   Class to do the math on FITS images to combine them in various ways
#
import sys
from typing import Optional

import numpy
from numpy import ma
from numpy.core.multiarray import ndarray

import MasterMakerExceptions
from Console import Console
from FileDescriptor import FileDescriptor
from RmFitsUtil import RmFitsUtil
from SessionController import SessionController


class ImageMath:

    # Combine the files in the given list using a simple mean (average)
    # Check, as reading, that they all have the same dimensions
    # Return  the mean data array

    @classmethod
    def combine_mean(cls, file_names: [str],
                     console: Console,
                     session_controller: SessionController) -> ndarray:
        """Combine FITS files in given list using simple mean.  Return an ndarray containing the combined data."""
        assert len(file_names) > 0  # Otherwise the combine button would have been disabled
        console.push_level()
        console.message("Combining by simple mean", +1)
        file_data: [ndarray] = RmFitsUtil.read_all_files_data(file_names)
        cls.check_cancellation(session_controller)
        mean_result = numpy.mean(file_data, axis=0)
        console.pop_level()
        return mean_result

    # Calculate the min-max clipped mean for the specified column.
    # See the explanation in the previous method or what we're doing.
    # We'll sort the list to more efficiently delete items - we don't need to search
    # the whole list for them, and we know where min and max values are

    # Example list:   [3, 8, 2, 1, 0, 4, 3, 2, 5, 3, 2, 9, 5, 1, 0, 3, 8, 4, 9, 2]
    @classmethod
    def calc_mm_clipped_mean(cls, column: numpy.array,
                             number_dropped_values: int, console: Console,
                             session_controller: SessionController) -> int:
        console.push_level()
        clipped_list = sorted(column.tolist())
        # Example List is now [0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 8, 8, 9, 9]

        # Drop all the instances of the minimum from the list
        drop = number_dropped_values
        while (drop > 0) and (len(clipped_list) > 0):
            cls.check_cancellation(session_controller)
            drop -= 1
            minimum_value = clipped_list[0]  # 0 in example
            # Find the last occurrence of this value in the sorted list
            index_past = numpy.searchsorted(clipped_list, minimum_value, side="right")  # example: 2
            if index_past == len(clipped_list):
                clipped_list = []  # We've deleted the whole list
            else:
                clipped_list = clipped_list[index_past:]

        # Drop all the instances of the maximum from the list
        # Eg. now [1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 8, 8, 9, 9]
        drop = number_dropped_values
        while (drop > 0) and (len(clipped_list) > 0):
            cls.check_cancellation(session_controller)
            drop -= 1
            maximum_value = clipped_list[-1]  # 9 in example
            # Find the last occurrence of this value in the sorted list
            first_index = numpy.searchsorted(clipped_list, maximum_value, side="left")  # example: 16
            if first_index == 0:
                clipped_list = []
            else:
                # Remember, python : ranges automatically omit the last element, so no "minus one"
                clipped_list = clipped_list[0:first_index]
                # Now [1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 8, 8]

        cls.check_cancellation(session_controller)
        if len(clipped_list) == 0:
            # Oops.  We've deleted the whole list, now how are we going to find a mean?
            # First, try reducing the number of dropped values
            # print("Min/Max clipping emptied list")
            if number_dropped_values > 1:
                # print("   Try reducing number of dropped values")
                result_mean = cls.calc_mm_clipped_mean(column, number_dropped_values - 1, console,
                                                       session_controller)
            else:
                # Even dropping only 1 value we emptied the list.  Just mean the whole thing.
                # print("   Dropped values at minimum.  Mean column without clipping.")
                result_mean = numpy.mean(column)
        else:
            # We have data left after the min/max clipping.  Calculate its mean
            # print(f"List of {len(column)} values reduced to {len(clipped_list)} values, calc mean")
            result_mean = numpy.mean(clipped_list)
        console.pop_level()
        return result_mean

    # Min-max clipped mean, version 1.  Still uses brute-force nested loop to visit every
    # cell in the 2-d image space and process columns individually.  However, it uses numpy
    # masked array to do the column calculations rather than editing the list of values.
    # @classmethod
    # def min_max_clip_version_1(cls, file_data: ndarray, number_dropped_values: int,
    #                            progress_dots: bool, console,
    #                            session_controller: SessionController) -> ndarray:
    #     console.push_level()
    #     console.message(f"Using min-max clip version 1: masked array per column", +1)
    #     (x_dimension, y_dimension) = file_data[0].shape
    #     # Set up the output array and then fill the columns one at a time
    #     # We'll put a "dot" on the screen every "n" items as a progress indicator
    #     # and a newline after the dots every 100 dots
    #     columns_processed = 0
    #     blip_every_column_count = 10000
    #     dots_printed = 0
    #     result = numpy.zeros(shape=(x_dimension, y_dimension))
    #     if progress_dots:
    #         console.message(f"Processing {x_dimension * y_dimension:,} columns. "
    #                         f"Each blip below is {blip_every_column_count:,}.", +1)
    #     for x_index in range(x_dimension):
    #         for y_index in range(y_dimension):
    #             # Do the "dot" progress indicator
    #             columns_processed += 1
    #             if progress_dots and (columns_processed % blip_every_column_count == 0):
    #                 print(".", end="", flush=True)
    #                 dots_printed += 1
    #                 if dots_printed == 100:
    #                     print("", end="\n", flush=True)
    #                     dots_printed = 0
    #             # Fill in the processed mean at this column
    #             column = file_data[:, x_index, y_index]
    #             min_max_clipped_mean: int = round(cls.calc_mm_clipped_mean_with_mask(column, number_dropped_values,
    #                                                                                  console))
    #             result[x_index, y_index] = min_max_clipped_mean
    #     if dots_printed != 100:
    #         print("", flush=True)
    #     console.pop_level()
    #     return result

    # Calculate the min-max clipped mean for the specified column.
    # See the explanation in the previous method or what we're doing.
    # This version uses a numpy masked array to mask away the min and max values
    # and then do the mean on what is left.
    # I like the elegance of this method, but it's slow, because it searches the
    # column 4n times (where n is the number of dropped min-max values);  once for
    # the minimum, again for the maximum, and again to find occurrences of each.
    # This makes me wonder if another version that locates all of the indices of
    # min and max on a single pass through the array would be worth while.
    # We'll try that, as optimization option 2

    # @classmethod
    # def calc_mm_clipped_mean_with_mask(cls, column: numpy.array, number_dropped_values: int, console: Console):
    #
    #     masked_array = ma.MaskedArray(column)
    #
    #     # Mask the minimum and maximum values
    #     drop = number_dropped_values
    #     while drop > 0:
    #         drop -= 1
    #         min_value = masked_array.min()  # Minimum value in the list
    #         max_value = masked_array.max()  # Max in list
    #         indices_to_mask = numpy.where((masked_array == min_value) | (masked_array == max_value))[0]
    #         masked_array[indices_to_mask] = ma.masked
    #
    #     # Calculate its mean.  If no values are left, try dropping fewer.
    #     # This will degrade to dropping none if necessary, so there will always be an answer
    #
    #     masked_mean = masked_array.mean()
    #     if ma.is_masked(masked_mean):
    #         return cls.calc_mm_clipped_mean_with_mask(column, number_dropped_values - 1, console)
    #     else:
    #         return masked_mean

    # Min-max clipped mean, version 2.  Still uses brute-force nested loop to visit every
    # cell in the 2-d image space and process columns individually.  However, it uses numpy
    # masked array to do the column calculations rather than editing the list of values.
    # Different from version 1: the min and max values are located in a single pass through
    # the array (per dropped value) rather than using the min and max functions.

    # @classmethod
    # def min_max_clip_version_2(cls, file_data: ndarray, number_dropped_values: int,
    #                            progress_dots: bool, console: Console) -> ndarray:
    #     console.push_level()
    #     console.message(f"Using min-max clip version 2: masked array per column, single pass", +1)
    #     (x_dimension, y_dimension) = file_data[0].shape
    #     # Set up the output array and then fill the columns one at a time
    #     # We'll put a "dot" on the screen every "n" items as a progress indicator
    #     # and a newline after the dots every 100 dots
    #     columns_processed = 0
    #     blip_every_column_count = 10000
    #     dots_printed = 0
    #     result = numpy.zeros(shape=(x_dimension, y_dimension))
    #     if progress_dots:
    #         console.message(f"Processing {x_dimension * y_dimension:,} columns. "
    #                         f"Each blip below is {blip_every_column_count:,}.", +1)
    #     for x_index in range(x_dimension):
    #         for y_index in range(y_dimension):
    #             # Do the "dot" progress indicator
    #             columns_processed += 1
    #             if progress_dots and (columns_processed % blip_every_column_count == 0):
    #                 print(".", end="", flush=True)
    #                 dots_printed += 1
    #                 if dots_printed == 100:
    #                     print("", end="\n", flush=True)
    #                     dots_printed = 0
    #             # Fill in the processed mean at this column
    #             column = file_data[:, x_index, y_index]
    #             min_max_clipped_mean: int = round(cls.calc_mm_clipped_mean_with_mask_single_pass(column,
    #                                                                                              number_dropped_values,
    #                                                                                              console))
    #             result[x_index, y_index] = min_max_clipped_mean
    #     if dots_printed != 100:
    #         print("", flush=True)
    #     console.pop_level()
    #     return result

    # Calculate the min-max clipped mean for the specified column.
    # See the explanation in the previous method or what we're doing.
    # This version uses a numpy masked array to mask away the min and max values
    # and then do the mean on what is left.
    # This uses a masked array for the column, same as version 1, but it doesn't
    # use the min, max, and where functions to find the extremes.  Instead it locates
    # those manually on a single pass through the array

    # @classmethod
    # def calc_mm_clipped_mean_with_mask_single_pass(cls, column: array, number_dropped_values: int, console: Console):
    #
    #     masked_array = ma.MaskedArray(column)
    #
    #     # Mask the minimum and maximum values
    #     drop = number_dropped_values
    #     while drop > 0:
    #         drop -= 1
    #         # Make one pass through the array and keep track of the value and location
    #         # of the minimum and maximum values
    #         min_value = 0xffff + 1  # Minimum found so far (pixels are 16-bit unsigned)
    #         max_value = -1  # Maximum found so far
    #         min_locations: [int] = []  # Indices where minimum found
    #         max_locations: [int] = []  # Indices where maximum found
    #         for index in range(len(column)):
    #             this_value = masked_array[index]
    #             # Ignore any values that were masked in previous pass
    #             if not ma.is_masked(this_value):
    #                 # Minimum so far?
    #                 if this_value < min_value:
    #                     # A new minimum.  Remember the value and start a new locations list
    #                     min_value = this_value
    #                     min_locations = [index]
    #                 elif this_value == min_value:
    #                     # Another instance of the minimum so far; remember location
    #                     min_locations.append(index)
    #                 # Maximum so far?
    #                 if this_value > max_value:
    #                     # A new maximum.  Remember the value and start a new locations list
    #                     max_value = this_value
    #                     max_locations = [index]
    #                 elif this_value == max_value:
    #                     # Another instance of the maximum so far; remember location
    #                     max_locations.append(index)
    #         # Mask the minimum and maximums just found
    #         masked_array[min_locations] = ma.masked
    #         masked_array[max_locations] = ma.masked
    #
    #     # Calculate mean.  If no values are left, try dropping fewer.
    #     # This will degrade to dropping none if necessary, so there will always be an answer
    #
    #     masked_mean = masked_array.mean()
    #     if ma.is_masked(masked_mean):
    #         return cls.calc_mm_clipped_mean_with_mask_single_pass(column, number_dropped_values - 1, console)
    #     else:
    #         return masked_mean

    # Min-max clipped mean, version 3.  Still uses brute-force nested loop to visit every
    # cell in the 2-d image space and process columns individually.  For the processing of the
    # columns, we combine methods (0) and (1) - using a sorted column to directly index the list
    # for minimum and maximum values, then using that information to mask the array

    # @classmethod
    # def min_max_clip_version_3(cls, file_data: ndarray, number_dropped_values: int,
    #                            progress_dots: bool, console: Console) -> ndarray:
    #     console.push_level()
    #     console.message(f"Using min-max clip version 3: masked array per column, sorted columns", +1)
    #     (x_dimension, y_dimension) = file_data[0].shape
    #     # Set up the output array and then fill the columns one at a time
    #     # We'll put a "dot" on the screen every "n" items as a progress indicator
    #     # and a newline after the dots every 100 dots
    #     columns_processed = 0
    #     blip_every_column_count = 10000
    #     dots_printed = 0
    #     result = numpy.zeros(shape=(x_dimension, y_dimension))
    #     if progress_dots:
    #         console.message(f"Processing {x_dimension * y_dimension:,} columns. "
    #                         f"Each blip below is {blip_every_column_count:,}.", +1)
    #     for x_index in range(x_dimension):
    #         for y_index in range(y_dimension):
    #             # Do the "dot" progress indicator
    #             columns_processed += 1
    #             if progress_dots and (columns_processed % blip_every_column_count == 0):
    #                 print(".", end="", flush=True)
    #                 dots_printed += 1
    #                 if dots_printed == 100:
    #                     print("", end="\n", flush=True)
    #                     dots_printed = 0
    #             # Fill in the processed mean at this column
    #             column = file_data[:, x_index, y_index]
    #             min_max_clipped_mean: int =
    #               round(cls.calc_mm_clipped_mean_sorted_masked(column, number_dropped_values,
    #                                                                                      console))
    #             result[x_index, y_index] = min_max_clipped_mean
    #     if dots_printed != 100:
    #         print("", flush=True)
    #     console.pop_level()
    #     return result

    # Calculate the min-max clipped mean for the specified column.
    # See the explanation in the previous method or what we're doing.
    # We'll sort the list to more efficiently delete items - we don't need to search
    # the whole list for them, and we know where min and max values are

    # Example array:   [3, 8, 2, 1, 0, 4, 3, 2, 5, 3, 2, 9, 5, 1, 0, 3, 8, 4, 9, 2]
    # @classmethod
    # def calc_mm_clipped_mean_sorted_masked(cls, column: numpy.array,
    #                                        number_dropped_values: int, console: Console) -> int:
    #     # print(f"calc_mm_clipped_mean({column},{number_dropped_values})")
    #     masked_array = ma.masked_array(numpy.sort(column))
    #     # Example array is now [0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 8, 8, 9, 9]
    #
    #     # Mask all the instances of the minimum
    #     drop = number_dropped_values
    #     while drop > 0:
    #         drop -= 1
    #         # Since we sorted the list, the first unmasked value is the minimum
    #         edges = ma.flatnotmasked_edges(masked_array)
    #         if edges is not None:
    #             index_of_min = edges[0]
    #             min_value = masked_array[index_of_min]
    #             # Starting from here, mask every instance of this value
    #             # Since the list is sorted, exit the search as soon as the value changes
    #             for index in range(index_of_min, len(column)):
    #                 if masked_array[index] != min_value or ma.is_masked(masked_array[index]):
    #                     break
    #                 masked_array[index] = ma.masked
    #
    #     # Mask all the instances of the maximum
    #     # Eg. now [--, --, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 8, 8, 9, 9]
    #     drop = number_dropped_values
    #     while drop > 0:
    #         drop -= 1
    #         # Since we sorted the list, the last unmasked value is the maximum
    #         edges = ma.flatnotmasked_edges(masked_array)
    #         if edges is not None:
    #             index_of_max = edges[1]
    #             max_value = masked_array[index_of_max]
    #             # Starting from the max, work backward and mask every instance of this value
    #             # Since the list is sorted, exit the search as soon as the value changes
    #             for index in reversed(range(0, index_of_max + 1)):
    #                 if masked_array[index] != max_value or ma.is_masked(masked_array[index]):
    #                     break
    #                 masked_array[index] = ma.masked
    #
    #     # Calculate mean.  If no values are left, try dropping fewer.
    #     # This will degrade to dropping none if necessary, so there will always be an answer
    #
    #     masked_mean = masked_array.mean()
    #     if ma.is_masked(masked_mean):
    #         return cls.calc_mm_clipped_mean_sorted_masked(column, number_dropped_values - 1, console)
    #     else:
    #         return masked_mean

    # Min-max clipped mean, version 4.  This is a completely different approach than options 0-3 above.
    # Here we will not process all n*m cells individually.  Instead we will use masking on the entire matrix
    # in matrix operations, then do a matrix-mean on the result.
    #
    #   We don't use the "progress dots" parameter since there is no significant iteration happening
    #
    #   Reminder:  file_data is a 3-dimensional array.  The first dimension is a layer per input file,
    #       and the next two dimensions is the image data for that file.  So we are finding minimum
    #       and maximum values down the first (zeroth) dimension.  We'll call those "columns"
    #
    #   This algorithm can produce different results than the cell-by-cell methods above in the case where
    #   a column has no data left after eliminating the minimums and maximums; because in this algorithm the entire
    #   matrix is re-calculated with fewer dropped points, while in the above methods only the offending columns
    #   are recalculated.  This case is rare, and I'm leaving it since it is so much faster.

    # @classmethod
    # def min_max_clip_version_4(cls, file_data: ndarray, number_dropped_values: int, console: Console):
    #     console.push_level()
    #     console.message(f"Using min-max clip version 4: pure masked-array matrix operation", +1)
    #     masked_array = ma.MaskedArray(file_data)
    #     drop_counter = number_dropped_values
    #     while drop_counter > 0:
    #         drop_counter -= 1
    #         # Find the minimums in all columns.  This will give a 2d matrix the same size as the images
    #         # with the column-minimum in each position
    #         minimum_values = masked_array.min(axis=0)
    #
    #         # Now compare that matrix of minimums down the layers, so we get Trues where
    #         # each minimum exists in its column (minimums might exist more than once, and
    #         # we want to find all of them)
    #         masked_array = ma.masked_where(masked_array == minimum_values, masked_array)
    #
    #         # Now find and mask the maximums, same approach
    #         maximum_values = masked_array.max(axis=0)
    #         masked_array = ma.masked_where(masked_array == maximum_values, masked_array)
    #
    #     masked_means = numpy.mean(masked_array, axis=0)
    #     # If the means matrix contains any masked values, that means that in that column the clipping
    #     # eliminated *all* the data.  This is not ok (and also rare) so we'll repeat with a smaller
    #     # number of clipped values.  This will degenerate to no clipping if the problem persists, and
    #     # ends up being a simple mean.
    #     if ma.is_masked(masked_means):
    #         console.message("Means array still contains masked values", +1)
    #         result = cls.min_max_clip_version_4(file_data, number_dropped_values - 1, console)
    #     else:
    #         result = masked_means.round()
    #     console.pop_level()
    #     return result

    # Min-max clipped mean, version 5.  Minor modification of version-4.  It still uses full matrix operations
    #   to calculate the mean.
    #
    #   However, method (4) can produce different results than the cell-by-cell methods above in the case where
    #   a column has no data left after eliminating the minimums and maximums; because in that algorithm the entire
    #   matrix is re-calculated with fewer dropped points, while in the above methods only the offending columns
    #   are recalculated.
    #
    #   This method, (5), is designed to produce identical results to (0) through (3) (and different from 4).
    #   If columns are entirely masked, only those columns are re-calculated with a lower drop quotient, not
    #   the entire matrix.

    @classmethod
    def min_max_clip_version_5(cls, file_data: ndarray, number_dropped_values: int,
                               console: Console, session_controller: SessionController):
        console.push_level()
        console.message(f"Using min-max clip with {number_dropped_values} iterations", +1)
        masked_array = ma.MaskedArray(file_data)
        drop_counter = 1
        while drop_counter <= number_dropped_values:
            cls.check_cancellation(session_controller)
            console.push_level()
            console.message(f"Iteration {drop_counter} of {number_dropped_values}.", +1)
            drop_counter += 1
            # Find the minimums in all columns.  This will give a 2d matrix the same size as the images
            # with the column-minimum in each position
            minimum_values = masked_array.min(axis=0)
            cls.check_cancellation(session_controller)

            # Now compare that matrix of minimums down the layers, so we get Trues where
            # each minimum exists in its column (minimums might exist more than once, and
            # we want to find all of them)
            masked_array = ma.masked_where(masked_array == minimum_values, masked_array)
            cls.check_cancellation(session_controller)
            console.message("Masked minimums.", +1, temp=True)

            # Now find and mask the maximums, same approach
            maximum_values = masked_array.max(axis=0)
            masked_array = ma.masked_where(masked_array == maximum_values, masked_array)
            cls.check_cancellation(session_controller)
            console.message("Masked maximums.", +1, temp=True)
            console.pop_level()

        console.message(f"Calculating mean of remaining data.", 0)
        masked_means = numpy.mean(masked_array, axis=0)
        cls.check_cancellation(session_controller)
        # If the means matrix contains any masked values, that means that in that column the clipping
        # eliminated *all* the data.  We will find the offending columns and re-calculate those with
        # fewer dropped extremes.  This should exactly reproduce the results of the cell-by-cell methods
        if ma.is_masked(masked_means):
            console.message("Means array still contains masked values; reducing drops for those columns.", 0)
            #  Get the mask, and get a 2D matrix showing which columns were entirely masked
            the_mask = masked_array.mask
            eliminated_columns_map = ndarray.all(the_mask, axis=0)
            masked_coordinates = numpy.where(eliminated_columns_map)
            x_coordinates = masked_coordinates[0]
            y_coordinates = masked_coordinates[1]
            assert len(x_coordinates) == len(y_coordinates)
            repairs = len(x_coordinates)
            cp = "s" if repairs > 1 else ""
            np = "" if repairs > 1 else "s"
            console.message(f"{repairs} column{cp} need{np} repair.", +1)
            for index in range(repairs):
                cls.check_cancellation(session_controller)
                # print(".", end="\n" if (index > 0) and (index % 50 == 0) else "")
                column_x = x_coordinates[index]
                column_y = y_coordinates[index]
                column = file_data[:, column_x, column_y]
                min_max_clipped_mean: int = round(cls.calc_mm_clipped_mean(column, number_dropped_values - 1,
                                                                           console, session_controller))
                masked_means[column_x, column_y] = min_max_clipped_mean
            # We've replaced the problematic columns, now the mean should calculate cleanly
            assert not ma.is_masked(masked_means)
        console.pop_level()
        return masked_means.round()

    # Combine given files using "sigma clip"
    #
    # In the following explanation, "column" means all of the points at a given image (x,y) coordinate,
    # across all the provided files.  Imagine that 20 images are given - then one "column" would be the 20 values
    # at the (0,0) coordinate in all 20 images, the next column would be the 20 values from the images' (0,1)
    # coordinates, and so on.  So for n x m sized images, there are n*m columns of 20 values each.
    #
    # This combination method uses a basic mean of the data, except each column is first pre-processed by
    # removing all the points that deviate from the column mean by more than a given amount.  The amount of
    # deviation is measured as "sigma" - the ratio of a given data value to the standard deviation of all
    # the data.  So, for example, clipping with "sigma 2.5" means we remove all data that is more than
    # 2.5 times the standard deviation above or below the sample mean
    #
    # In the min-max clipping above, eliminating values in a column, could, in rare circumstances,
    # eliminate *all* the data in the column.  That would be very rare with sigma clipping and the code
    # will report if it happens and then, for now, resort to brute-force repairs on the affected columns
    # using the "min-max" method above.
    #
    # We assume the algorithm analysis done for the min-max case above would apply here too, so we are just
    # jumping to "algorithm 5" - the matrix math with brute-force column repair
    #
    #   Algorithm for this method:
    #   For each column:
    #       Calculate mean and population standard deviation (stdev) of all data in column
    #       Calculate Z-score of each datum in column.
    #           Z-score = abs(datum - mean)/stddev
    #       Reject (mask) any data where Z-Score > given threshold
    #       Calculate mean of remaining data
    #

    @classmethod
    def combine_sigma_clip(cls, file_names: [str], sigma_threshold: float,
                           console: Console,
                           session_controller: SessionController) -> Optional[ndarray]:
        console.push_level()
        console.message(f"Combine by sigma-clipped mean, z-score threshold {sigma_threshold}", +1)
        file_data = numpy.asarray(RmFitsUtil.read_all_files_data(file_names))

        console.message("Calculating unclipped means", +1)
        column_means = numpy.mean(file_data, axis=0)
        cls.check_cancellation(session_controller)
        console.message("Calculating standard deviations", 0)
        column_stdevs = numpy.std(file_data, axis=0)
        cls.check_cancellation(session_controller)
        console.message("Calculating z-scores", 0)

        # Now what we'd like to do is just:
        #    z_scores = abs(file_data - column_means) / column_stdevs
        # Unfortunately, standard deviations can be zero, so that simplistic
        # statement would generate division-by-zero errors.
        # Std for a column would be zero if all the values in the column were identical.
        # In that case we wouldn't want to eliminate any anyway, so we'll set the
        # zero stdevs to a large number, which causes the z-scores to be small, which
        # causes no values to be eliminated.
        column_stdevs[column_stdevs == 0.0] = sys.float_info.max
        z_scores = abs(file_data - column_means) / column_stdevs
        cls.check_cancellation(session_controller)

        console.message("Eliminated data outside threshold", 0)
        exceeds_threshold = z_scores > sigma_threshold
        cls.check_cancellation(session_controller)

        # Calculate and display how much data we are ignoring
        dimensions = exceeds_threshold.shape
        total_pixels = dimensions[0] * dimensions[1] * dimensions[2]
        number_masked = numpy.count_nonzero(exceeds_threshold)
        percentage_masked = 100.0 * number_masked / total_pixels
        console.message(f"Discarded {number_masked:,} pixels of {total_pixels:,} "
                        f"({percentage_masked:.3f}% of data)", +1)

        masked_array = ma.masked_array(file_data, exceeds_threshold)
        cls.check_cancellation(session_controller)

        console.message("Calculating adjusted means", -1)
        masked_means = ma.mean(masked_array, axis=0)
        cls.check_cancellation(session_controller)

        # If the means matrix contains any masked values, that means that in that column the clipping
        # eliminated *all* the data.  We will find the offending columns and re-calculate those using
        # simple min-max clipping.
        if ma.is_masked(masked_means):
            console.message("Means array still contains masked values; min-max clipping those columns.", 0)
            #  Get the mask, and get a 2D matrix showing which columns were entirely masked
            eliminated_columns_map = ndarray.all(exceeds_threshold, axis=0)
            masked_coordinates = numpy.where(eliminated_columns_map)
            x_coordinates = masked_coordinates[0]
            y_coordinates = masked_coordinates[1]
            assert len(x_coordinates) == len(y_coordinates)
            for index in range(len(x_coordinates)):
                cls.check_cancellation(session_controller)
                column_x = x_coordinates[index]
                column_y = y_coordinates[index]
                column = file_data[:, column_x, column_y]
                min_max_clipped_mean: int = round(cls.calc_mm_clipped_mean(column, 2, console, session_controller))
                masked_means[column_x, column_y] = min_max_clipped_mean
            # We've replaced the problematic columns, now the mean should calculate cleanly
            assert not ma.is_masked(masked_means)
        console.pop_level()
        result = masked_means.round().filled()
        return result

    @classmethod
    def combine_median(cls, file_names: [str],
                       console: Console,
                       session_controller: SessionController) -> ndarray:
        assert len(file_names) > 0  # Otherwise the combine button would have been disabled
        console.push_level()
        console.message("Combine by simple Median", +1)
        file_data = RmFitsUtil.read_all_files_data(file_names)
        cls.check_cancellation(session_controller)
        median_result = numpy.median(file_data, axis=0)
        console.pop_level()
        return median_result

    # Combine given files using "min-max clip"
    # In the following explanation, "column" means all of the points at a given image (x,y) coordinate,
    # across all the provided files.  Imagine that 20 images are given - then one "column" would be the 20 values
    # at the (0,0) coordinate in all 20 images, the next column would be the 20 values from the images' (0,1)
    # coordinates, and so on.  So for n x m sized images, there are n*m columns of 20 values each.
    #
    # This combination method uses a basic mean of the data, except each column is first pre-processed by
    # removing all the points at the column's minimum value, and all the points at the column's maximum
    # value.  This can be repeated more than once - the number of repetitions is given.  Then the remaining
    # points in the column are combined with a simple mean.  The idea is that the min/max will remove dead and hot
    # pixels, so the mean on the rest will not include those artifacts.
    #
    # Eliminating min and max values in a column, could, in rare circumstances, eliminate *all* the data in the
    # column.  If that happens we reduce the number of dropped points for that column until data remains to mean.

    # Note that, because the clipping eliminates points on a column-by-column basis, the number of points actually
    # surviving for combination will vary.  There are simple slow ways, and complex fast ways, to handle this.
    #
    #   The following versions were all tried, in order, and timed, ending up at "optimization 5" which is the
    #   one in use.  The other ones are left here for education or interest.
    #
    #   Optimization 0:     This initial version just loops over each image cell and calculates the mean of each column
    #                       separately.  Slow, but it works and is easy to understand what's happening.
    #   Optimization 1:     Keep the x,y loop but used masked array to calculate clipped mean on the column
    #   Optimization 2:     Same as (1) but manually locates min and max values on a single pass thru column
    #
    #   Comment added after initial testing.  Surprised so far, method [0] still fastest by a long shot.
    #                       The low cost of the very efficient quicksort allows the benefits of direct
    #                       indexing for min and max values to swamp the results.
    #
    #   Optimization 3:     Use the sorted-array indexing of option (0) and the masked array of (1a).
    #                       Result: 2nd-best.  Better than (1) or (2) but still doesn't beat (0)
    #   Optimization 4:     Convert the entire 3-D structure to a masked array.  The masking logic is complex,
    #                       but then the mean calculation is simple.  Most important, there is no
    #                       nested loop visiting all n*m cells.  However, this algorithm gives a different result
    #                       than the others in the case where *all* the values in a column are eliminated, because
    #                       it recalculates the entire matrix with a smaller drop-quotient, rather than just that column
    #   Optimization 5:     Like (4), but recalculates individual columns that fail through complete elimination,
    #                       so generates identical results to options (0) through (3)

    @classmethod
    def combine_min_max_clip(cls, file_names: [str], number_dropped_values: int,
                             console: Console,
                             session_controller: SessionController) -> Optional[ndarray]:
        """Combine FITS files in given list using min/max-clipped mean.
        Return an ndarray containing the combined data."""
        success: bool
        assert len(file_names) > 0  # Otherwise the combine button would have been disabled
        # Get the data to be processed
        file_data_list: [ndarray] = RmFitsUtil.read_all_files_data(file_names)
        cls.check_cancellation(session_controller)
        file_data = numpy.asarray(file_data_list)

        # Do the math using each algorithm, and display how long it takes

        # time_before_0 = datetime.now()
        # result0 = cls.min_max_clip_version_0(file_data, number_dropped_values, progress_dots)
        # time_after_0 = datetime.now()
        # duration_0 = time_after_0 - time_before_0
        #
        # time_before_1 = datetime.now()
        # result1 = cls.min_max_clip_version_1(file_data, number_dropped_values, progress_dots)
        # time_after_1 = datetime.now()
        # duration_1 = time_after_1 - time_before_1
        #
        # time_before_2 = datetime.now()
        # result2 = cls.min_max_clip_version_2(file_data, number_dropped_values, progress_dots)
        # time_after_2 = datetime.now()
        # duration_2 = time_after_2 - time_before_2
        #
        # time_before_3 = datetime.now()
        # result3 = cls.min_max_clip_version_3(file_data, number_dropped_values, progress_dots)
        # time_after_3 = datetime.now()
        # duration_3 = time_after_3 - time_before_3
        #
        # time_before_4 = datetime.now()
        # result4 = cls.min_max_clip_version_4(file_data, number_dropped_values)
        # time_after_4 = datetime.now()
        # duration_4 = time_after_4 - time_before_4
        #
        # time_before_5 = datetime.now()
        # result5 = cls.min_max_clip_version_5(file_data, number_dropped_values)
        # time_after_5 = datetime.now()
        # duration_5 = time_after_5 - time_before_5
        #
        # print(f"Method 0 time: {duration_0}")
        # print(f"Method 1 time: {duration_1}")
        # print(f"Method 2 time: {duration_2}")
        # print(f"Method 3 time: {duration_3}")
        # print(f"Method 4 time: {duration_4}")
        # print(f"Method 5 time: {duration_5}")
        #
        # # Also ensure that the different algorithm versions produced exactly the same result
        # # Using method-0 as the reference
        # cls.compare_results(result0, result1, "1")
        # cls.compare_results(result0, result2, "2")
        # cls.compare_results(result0, result3, "3")
        # cls.compare_results(result0, result4, "4", dump=False)
        # cls.compare_results(result0, result5, "5")
        #
        # return result0
        result5 = cls.min_max_clip_version_5(file_data, number_dropped_values, console,
                                             session_controller)
        cls.check_cancellation(session_controller)
        result = result5.filled()
        return result

    @classmethod
    def compare_results(cls, reference: ndarray, comparator: ndarray, version: str, console: Console, dump=True):
        console.push_level()
        assert reference.shape == comparator.shape
        if numpy.array_equal(reference, comparator):
            console.message(f"Version {version} results identical", +1)
        else:
            console.message(f"Version {version} results are different", +1)
            if dump:
                (rows, columns) = reference.shape
                console.message("Reference array:", 0)
                for row_index in range(rows):
                    this_column = reference[row_index, ].tolist()
                    console.message(str(this_column), +1, temp=True)
                console.message(f"Version {version} array:", 0)
                for row_index in range(rows):
                    this_column = comparator[row_index, ].tolist()
                    print(str(this_column))
        console.pop_level()

    # Min-max clipped mean, version 0.  Simple algorithm, brute-force calculating the mean
    # across columns of each cell, one at a time.
    # @classmethod
    # def min_max_clip_version_0(cls, file_data: ndarray, number_dropped_values: int,
    #                            console: Console) -> ndarray:
    #     console.push_level()
    #     console.message(f"Using min-max clip version 0: simple slow algorithm", +1)
    #     (x_dimension, y_dimension) = file_data[0].shape
    #     # Set up the output array and then fill the columns one at a time
    #     # We'll put a "dot" on the screen every "n" items as a progress indicator
    #     # and a newline after the dots every 100 dots
    #     columns_processed = 0
    #     result = numpy.zeros(shape=(x_dimension, y_dimension))
    #     for x_index in range(x_dimension):
    #         for y_index in range(y_dimension):
    #             # Do the "dot" progress indicator
    #             columns_processed += 1
    #             # Fill in the processed mean at this column
    #             column = file_data[:, x_index, y_index]
    #             min_max_clipped_mean: int = round(cls.calc_mm_clipped_mean(column, number_dropped_values, console))
    #             result[x_index, y_index] = min_max_clipped_mean
    #     console.pop_level()
    #     return result

    @classmethod
    def mean_exposure_and_temperature(cls, file_descriptors: [FileDescriptor]) -> (float, float):
        total_exposure = 0.0
        total_temperature = 0.0
        assert len(file_descriptors) > 0
        for descriptor in file_descriptors:
            total_exposure += descriptor.get_exposure()
            total_temperature += descriptor.get_temperature()
        return (total_exposure / len(file_descriptors)), (total_temperature / len(file_descriptors))

    @classmethod
    def check_cancellation(cls, session_controller: SessionController):
        if session_controller.thread_cancelled():
            raise MasterMakerExceptions.SessionCancelled
