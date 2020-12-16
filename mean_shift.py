import math
import sys
import numpy

# This implementation of the Mean Shift clustering algorithm was written by Matt Nedrich
# and made freely available from his GitHub site.  Profound thanks to Matt.
#
# This, Matt's version is being used instead of the sklearn.cluster MeanShift class because sklearn
# doesn't work well with pyinstaller on windows systems - it generates a dependency on a multiprocessing
# dll but doesn't generate the correct dependency information to cause that dll to be included in the
# resulting executable.
#
# The following is the LICENSE text included with Matt's download for this software:

# The MIT License (MIT)
#
# Copyright (c) 2015 Matt Nedrich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Several separate .py files in the downloaded program were merged into this single file
# import point_grouper as pg
# import mean_shift_utils as ms_utils
# imported from mean_shift_utils
# import mean_shift_utils as ms_utils
# Imported from former point_grouper file:

# Comments in the methods below are author Matt's


def euclidean_dist(point_a: numpy.ndarray, point_b: numpy.ndarray) -> float:
    if len(point_a) != len(point_b):
        raise Exception("expected point dimensionality to match")
    total = float(0)
    for dimension in range(0, len(point_a)):
        total += (point_a[dimension] - point_b[dimension]) ** 2
    return math.sqrt(total)


def gaussian_kernel(distance: numpy.ndarray, bandwidth: float) -> numpy.ndarray:
    euclidean_distance = numpy.sqrt((distance ** 2).sum(axis=1))
    val = (1/(bandwidth*math.sqrt(2*math.pi))) * numpy.exp(-0.5 * (euclidean_distance / bandwidth) ** 2)
    return val


def multivariate_gaussian_kernel(distances, bandwidths):

    # Number of dimensions of the multivariate gaussian
    dim = len(bandwidths)

    # Covariance matrix
    cov = numpy.multiply(numpy.power(bandwidths, 2), numpy.eye(dim))

    # Compute Multivariate gaussian (vectorized implementation)
    exponent = -0.5 * numpy.sum(numpy.multiply(numpy.dot(distances, numpy.linalg.inv(cov)), distances), axis=1)
    val = (1 / numpy.power((2 * math.pi), (dim/2)) * numpy.power(numpy.linalg.det(cov), 0.5)) * numpy.exp(exponent)

    return val
# End of import from pointgrouper file


GROUP_DISTANCE_TOLERANCE = .1


class PointGrouper(object):
    def group_points(self, points: [[float]]) -> numpy.array:
        group_assignment = []
        groups = []
        group_index = 0
        for point in points:
            nearest_group_index = self._determine_nearest_group(point, groups)
            if nearest_group_index is None:
                # create new group
                groups.append([point])
                group_assignment.append(group_index)
                group_index += 1
            else:
                group_assignment.append(nearest_group_index)
                groups[nearest_group_index].append(point)
        return numpy.array(group_assignment)

    def _determine_nearest_group(self, point: [float], groups: [[[float]]]) -> int:
        nearest_group_index = None
        index = 0
        for group in groups:
            distance_to_group = self._distance_to_group(point, group)
            if distance_to_group < GROUP_DISTANCE_TOLERANCE:
                nearest_group_index = index
            index += 1
        return nearest_group_index

    def _distance_to_group(self, point: [float], group: [[float]]) -> float:
        min_distance = sys.float_info.max
        for pt in group:
            dist = euclidean_dist(point, pt)
            if dist < min_distance:
                min_distance = dist
        return min_distance
# end import from mean_shift_utils

# Original mean_shift file


MIN_DISTANCE = 0.000001


class MeanShift(object):
    def __init__(self, kernel=gaussian_kernel):
        if kernel == 'multivariate_gaussian':
            kernel = multivariate_gaussian_kernel
        self.kernel = kernel

    def cluster(self, points: numpy.ndarray, kernel_bandwidth: float, iteration_callback=None):
        if iteration_callback:
            iteration_callback(points, 0)
        shift_points = numpy.array(points)
        max_min_dist = 1
        iteration_number = 0

        still_shifting = [True] * points.shape[0]
        while max_min_dist > MIN_DISTANCE:
            # print max_min_dist
            max_min_dist = 0
            iteration_number += 1
            for i in range(0, len(shift_points)):
                if not still_shifting[i]:
                    continue
                p_new = shift_points[i]
                p_new_start = p_new
                p_new = self._shift_point(p_new, points, kernel_bandwidth)
                dist = euclidean_dist(p_new, p_new_start)
                if dist > max_min_dist:
                    max_min_dist = dist
                if dist < MIN_DISTANCE:
                    still_shifting[i] = False
                shift_points[i] = p_new
            if iteration_callback:
                iteration_callback(shift_points, iteration_number)
        point_grouper = PointGrouper()
        points_as_list: [[float]] = shift_points.tolist()
        group_assignments = point_grouper.group_points(points_as_list)
        return MeanShiftResult(points, shift_points, group_assignments)

    def _shift_point(self, point: numpy.ndarray, points: numpy.ndarray, kernel_bandwidth: float) -> numpy.ndarray:
        # from http://en.wikipedia.org/wiki/Mean-shift
        points = numpy.array(points)

        # numerator
        point_weights = self.kernel(point-points, kernel_bandwidth)
        tiled_weights = numpy.tile(point_weights, [len(point), 1])
        # denominator
        denominator = sum(point_weights)
        shifted_point = numpy.multiply(tiled_weights.transpose(), points).sum(axis=0) / denominator
        return shifted_point

        # ***************************************************************************
        # ** The above vectorized code is equivalent to the unrolled version below **
        # ***************************************************************************
        # shift_x = float(0)
        # shift_y = float(0)
        # scale_factor = float(0)
        # for p_temp in points:
        #     # numerator
        #     dist = ms_utils.euclidean_dist(point, p_temp)
        #     weight = self.kernel(dist, kernel_bandwidth)
        #     shift_x += p_temp[0] * weight
        #     shift_y += p_temp[1] * weight
        #     # denominator
        #     scale_factor += weight
        # shift_x = shift_x / scale_factor
        # shift_y = shift_y / scale_factor
        # return [shift_x, shift_y]


class MeanShiftResult:
    def __init__(self, original_points: numpy.ndarray,
                 shifted_points: numpy.ndarray,
                 cluster_ids: numpy.ndarray):
        self.original_points = original_points
        self.shifted_points = shifted_points
        self.cluster_ids = cluster_ids
