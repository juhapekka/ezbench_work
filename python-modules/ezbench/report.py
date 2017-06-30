"""
Copyright (c) 2015, Intel Corporation

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Intel Corporation nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from email.utils import parsedate_tz, mktime_tz
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
from dateutil import relativedelta
from array import array
from scipy import stats
from enum import Enum
import numpy as np
import statistics
import subprocess
import threading
import traceback
import atexit
import pprint
import fcntl
import mmap
import time
import json
import glob
import copy
import math
import ast
import csv
import sys
import os
import re

ezbench_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.append(os.path.join(ezbench_dir, 'timing_DB'))

from ezbench.runner import *
from ezbench.scm import *
from timing import *

from ezbench import imgcmp

class Test:
    def __init__(self, full_name, unit="undefined"):
        self.full_name = full_name
        self.unit = unit

    def __eq__(x, y):
        return x.full_name == y.full_name and x.unit == y.unit

    def __hash__(self):
        return hash(self.full_name) ^ hash(self.unit)

    # returns (base_name, subtests=[], metric)
    @classmethod
    def parse_name(cls, full_name):
        idx = full_name.find('[')
        idx2 = full_name.find('<')
        if idx > 0:
            if full_name[-1] != ']':
                print("WARNING: test name '{}' is invalid.".format(full_name))

            basename = full_name[0 : idx]
            subtests = full_name[idx + 1 : -1].split('|')
            metric = None
        elif idx2 > 0:
            if full_name[-1] != '>':
                print("WARNING: test name '{}' is invalid.".format(full_name))

            basename = full_name[0 : idx2]
            subtests = []
            metric = full_name[idx2 + 1 : -1]
        else:
            basename = full_name
            subtests = []
            metric = None

        return (basename, subtests, metric)

    @classmethod
    def partial_name(self, basename, sub_tests):
        name = basename
        if len(sub_tests) > 0 and sub_tests[0] is not None and len(sub_tests[0]) > 0:
            name += "["
            for i in range(0, len(sub_tests)):
                if i != 0:
                    name += "|"
                name += sub_tests[i]
            name += "]"
        return name

    @classmethod
    def metric_fullname(self, basename, metric_name):
        return "{}<{}>".format(basename, metric_name)

class ListStats:
    __slots__ = ['data', '_cache_result', '_cache_mean', '_cache_std', '_cache_mean_simple']

    def __init__(self, data):
        self.data = np.array(data)

        # cached data
        self.invalidate_cache()

    def invalidate_cache(self):
        """ Trash the cache, necessary if you manually update the data (BAD!) """

        self._cache_result = None
        self._cache_mean = None
        self._cache_std = None
        self._cache_mean_simple = None

    def __samples_needed__(self, sigma, margin, confidence=0.95):
        # TODO: Find the function in scipy to get these values
        if confidence <= 0.9:
            z = 1.645
        elif confidence <= 0.95:
            z = 1.960
        else:
            z = 2.576
        return ((z * sigma) / margin)**2

    def __compute_stats__(self):
        if self._cache_mean is None or self._cache_std is None:
            if len(self.data) > 1:
                self._cache_mean, var, self._cache_std = stats.bayes_mvs(self.data,
                                                                         alpha=0.95)
                if np.math.isnan(self._cache_mean[0]):
                    self._cache_mean = (self.data[0], (self.data[0], self.data[0]))
                    self._cache_std = (0, (0, 0))
            else:
                if len(self.data) == 0:
                    value = 0
                else:
                    value = self.data[0]
                self._cache_mean = (value, (value, value))
                self._cache_std = (float("inf"), (float("inf"), float("inf")))

    def margin(self):
        """ Computes the margin of error for the sample set """

        self.__compute_stats__()
        if self._cache_mean[0] > 0:
            return (self._cache_mean[1][1] - self._cache_mean[1][0]) / 2 / self._cache_mean[0]
        else:
            return 0

    # wanted_margin is a number between 0 and 1
    def confidence_margin(self, wanted_margin = None, confidence=0.95):
        """
        Computes the confidence margin of error and how many samples would be
        needed to guarantee that mean of the data would be inside the wanted_margin.

        Args:
            wanted_margin: A float that represents how much variance you accept. For example, 0.025 would mean the accepted variance is 2.5%
            confidence: The wanted confidence level

        Returns:
            the current margin of error
            the number of samples needed to reach the wanted confidence
        """

        if len(self.data) < 2 or self.data.var() == 0:
            return 0, 2

        self.__compute_stats__()
        margin = self.margin()
        wanted_samples = 2

        if wanted_margin is not None:
            # TODO: Get sigma from the test instead!
            sigma = (self._cache_std[1][1] - self._cache_std[1][0]) / 2
            target_margin = self._cache_mean[0] * wanted_margin
            wanted_samples = np.math.ceil(self.__samples_needed__(sigma,
                                                               target_margin,
                                                               confidence))

        return margin, wanted_samples

    def mean(self):
        """ Computes the mean of the data set """

        if self._cache_mean is not None:
            return self._cache_mean[0]

        if self._cache_mean_simple is None:
            if len(self.data) > 0:
                self._cache_mean_simple = sum(self.data) / len(self.data)
            else:
                self._cache_mean_simple = 0
        return self._cache_mean_simple

    def compare(self, distrib_b, equal_var=True):
        """
        Compare the current sample distribution to distrib_b's

        Args:
            distrib_b: the distribution to compare to
            equal_var: f True (default), perform a standard independent 2 sample test that assumes equal population variances [R263]. If False, perform Welch’s t-test, which does not assume equal population variance [R264].

        Returns:
            the difference of the means (self - b)
            the confidence of them being from the same normal distribution
        """

        if self.data.var() == 0 and distrib_b.data.var() == 0:
            if self.data[0] == distrib_b.data[0]:
                p = 1
            else:
                p = 0
        else:
            t, p = stats.ttest_ind(distrib_b.data, self.data,
                    equal_var = equal_var)
        if distrib_b.mean() != 0:
            diff = abs(self.mean() - distrib_b.mean()) / distrib_b.mean()
        elif self.mean() == distrib_b.mean():
            diff = 0
        else:
            diff = float('inf')

        return diff, 1 - p

    def __len__(self):
        return len(self.data)

class BenchSubTestType(Enum):
    SUBTEST_COMMIT_RESULT = 0
    SUBTEST_FLOAT = 1
    SUBTEST_STRING = 2
    SUBTEST_IMAGE = 3
    METRIC = 4

class SubTestBase:
    __slots__ = ['name', 'value', 'data_raw_file']

    def __init__(self, name, averageValue, data_raw_file = None):
        if name is not None:
            name = sys.intern(name)
        if data_raw_file is not None:
            data_raw_file = sys.intern(data_raw_file)

        self.name = name
        self.value = averageValue
        self.data_raw_file = data_raw_file

class SubTestCommitResult(SubTestBase):
    def __init__(self, commit):
        super().__init__("build_result", commit.compil_exit_code, None)

    def subtest_type(self):
        return BenchSubTestType.SUBTEST_COMMIT_RESULT

    def unit(self):
        return None

class SubTestString(SubTestBase):
    def __init__(self, name, value, data_raw_file = None):
        super().__init__(name, sys.intern(value), data_raw_file)

    def subtest_type(self):
        return BenchSubTestType.SUBTEST_STRING

    def unit(self):
        return None

class SubTestFloat(SubTestBase):
    __slots__ = ['_unit', 'samples']

    def __init__(self, name, unit, samples, data_raw_file = None):
        self.samples = ListStats(samples)
        super().__init__(name, self.samples.mean(), data_raw_file)
        self._unit = unit

    def subtest_type(self):
        return BenchSubTestType.SUBTEST_FLOAT

    def unit(self):
        return self._unit

    @classmethod
    def to_string(cls, mean, unit, margin, n):
        if n > 1:
            return "{:.2f} {} +/- {:.2f}% (n={})".format(mean, unit, margin * 100, n)
        else:
            return "{:.2f} {}".format(mean, unit)

    def __str__(self):
        return self.to_string(self.samples.mean(), self.unit(), self.samples.margin(), len(self.samples))

class Metric(SubTestFloat):
    __slots__ = ['timestamps']

    def __init__(self, name, unit, samples, timestamps = None, data_raw_file = None):
        super().__init__(name, unit, samples, data_raw_file)
        self.timestamps = timestamps

    def subtest_type(self):
        return BenchSubTestType.METRIC

    def exec_time(self):
        """
        Returns the difference between the last and the first timestamp or 0 if
        there are no timestamps.
        """
        if self.timestamps is not None and len(self.timestamps) > 0:
            return self.timestamps[-1]
        else:
            return 0

class SubTestImage(SubTestBase):
    __slots__ = ['img_file_name']

    def __init__(self, name, imgFileName, data_raw_file = None):
        super().__init__(name, None, data_raw_file)
        self.img_file_name = imgFileName

    def subtest_type(self):
        return BenchSubTestType.SUBTEST_IMAGE

    def unit(self):
        return None

    def image_file(self):
        return self.value

    def set_reference(self, imgFile):
        self.value = self.img_compare(imgFile)

    def img_compare(self, imgFile):
        return imgcmp.compare(self.img_file_name, imgFile, ['RMSE'], 'null:')

class TestRun:
    __slots__ = ['test_result', 'run_file', 'main_value_type', 'main_value', 'env_file', '_results']

    # Holds the different subresults for all the tests to allow detecting the
    # missing results
    subresults = dict()
    subresults_type = dict()

    def __init__(self, testResult, testType, runFile, metricsFiles, mainValueType = None, mainValue = None):
        self.test_result = testResult
        self.run_file = runFile

        # Ignore the main value for units, as they are pointless anyway
        if testType != "unit":
            self.main_value_type = mainValueType
            self.main_value = mainValue
        else:
            self.main_value_type = None
            self.main_value = None

        self._results = dict()

        # Add the environment file
        self.env_file = runFile + ".env_dump"
        if not os.path.isfile(self.env_file):
            self.env_file = None

        if testType == "bench":
            # There are no subtests here
            data, unit, more_is_better = readCsv(runFile)
            if len(data) > 0:
                result = SubTestFloat("", testResult.unit, data, runFile)
                self.__add_result__(result)
        elif testType == "unit":
            unit_tests = readUnitRun(runFile)
            for subtest in unit_tests:
                result = SubTestString(subtest, unit_tests[subtest], runFile)
                self.__add_result__(result)
        elif testType == "imgval":
            self.importImgTestRun(runFile)
        elif testType == "unified":
            self.importUnifiedTestRun(runFile)
        elif testType == "commit_result":
            self.__add_result__(SubTestCommitResult(testResult.commit))
        else:
            raise ValueError("Ignoring results because the type '{}' is unknown".format(testType))

        for f in metricsFiles:
            self.__add_metrics__(f)

    def importImgTestRun(self, runFile):
        with open(runFile, 'rt') as f:
            for line in f:
                split = line.split(',')
                if len(split) == 2:
                    frameid = split[0].strip()
                    frame_file = split[1].strip()
                    fullpath = os.path.join(self.test_result.commit.report.log_folder, frame_file)
                    self.__add_result__(SubTestImage(frameid, fullpath, runFile))
            self.__add_result__(SubTestString("", "complete", runFile))

    def importUnifiedTestRun(self, runFile):
        l_re = re.compile(r'^(.*): (.*)\((.*)\)( .*)?$')
        with open(runFile, 'rt') as f:
            for i, line in enumerate(f):
                m = l_re.match(line)
                if m is None:
                    print("{}: invalid format at line {}: '{}'".format(runFile, i, line))
                    continue

                key, key_type, value, unit = m.groups()

                if unit is not None:
                    unit = unit.strip()

                if key_type == "float":
                    if unit is None:
                        print("{}: Float type requires a unit at line {}".format(runFile, i))
                        continue

                    # handle lists of floats, if necessary
                    value = ast.literal_eval(value)
                    if type(value) is float:
                        value = [value]

                    self.__add_result__(SubTestFloat(key, unit, value, runFile))
                elif key_type == "str":
                    self.__add_result__(SubTestString(key, value, runFile))
                elif key_type == "img":
                    self.__add_result__(SubTestImage(key, value, runFile))

    def __add_result__(self, subtest):
        if subtest.subtest_type() == BenchSubTestType.METRIC:
            key = "metric_{}".format(subtest.name)
        else:
            key = subtest.name

        # Add the key to the subresults
        test_name = self.test_result.test.full_name
        if test_name not in TestRun.subresults:
            TestRun.subresults[test_name] = set()
            TestRun.subresults_type[test_name] = dict()
        TestRun.subresults[test_name].add(key)
        TestRun.subresults_type[test_name][key] = subtest.__class__.__name__

        # Verify that the subtest does not already exist
        if key in self._results:
            msg = "Raw data file '{}' tries to add an already-existing result '{}' (found in '{}')"
            msg = msg.format(subtest.data_raw_file, key, self._results[key].data_raw_file)
            raise ValueError(msg)

        self._results[key] = subtest

    def tag_missing_results(self):
        # Verify that the TestRun was a complete run
        if self.result("") is None:
            return

        # Find the keys that are not present
        test_name = self.test_result.test.full_name
        for key in TestRun.subresults[test_name] - self.results():
            t = TestRun.subresults_type[test_name][key]
            if t == "SubTestFloat":
                self.__add_result__(SubTestFloat(key, self.test_result.unit, -1, self.run_file))
            elif t == "SubTestString":
                self.__add_result__(SubTestString(key, "missing", self.run_file))
            elif t == "SubTestImage":
                self.__add_result__(SubTestImage(key, None, self.run_file))

    def __add_metrics__(self, metric_file):
        values = dict()
        with open(metric_file, 'rt') as f:
            # Do not try to open files bigger than 1MB
            if os.fstat(f.fileno()).st_size > 1e6:
                print('The metric file \'{}\' is too big (> 1MB)'.format(metric_file), file=sys.stderr)
                return

            field_names = None
            fields_values = list()
            mmaped_file = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
            for line in iter(mmaped_file.readline, ""):
                fields = line.decode().split(',')
                if field_names is None:
                    field_names = fields
                    for i in range(0, len(fields)):
                        fields_values.append(list())
                elif len(fields) == len(field_names):
                    for i in range(0, len(fields)):
                        fields_values[i].append(float(fields[i]))
                else:
                    break

            for i in range(0, len(field_names)):
                values[field_names[i]] = fields_values[i]
            mmaped_file.close()

        # Find the time values and store them aside after converting them to seconds
        time_unit_re = re.compile(r'^time \((.+)\)$')
        time = list()
        for field in values:
            m = time_unit_re.match(field)
            if m is not None:
                unit = m.groups()[0]
                factor = 1
                if unit == "s":
                    factor = 1
                elif unit == "ms":
                    factor = 1e-3
                elif unit == "us" or unit == "µs":
                    factor = 1e-6
                elif unit == "ns":
                    factor = 1e-9
                else:
                    print("unknown time unit '{}'".format(unit))
                for v in values[field]:
                    time.append(v * factor)

        # Create the metrics
        metric_name_re = re.compile(r'^(.+) \((.+)\)$')
        for field in values:
            unit = None
            m = metric_name_re.match(field)
            if m is not None:
                metric_name, unit = m.groups()
            else:
                metric_name = field

            if metric_name.lower() == "time":
                continue

            if unit.lower() == "rpm" or unit.lower() == "°c":
                continue

            vals = list()
            timestamps = list()
            for v in range(0, len(values[field])):
                vals.append(values[field][v])
                timestamps.append(time[v] - time[0])
            metric = Metric(metric_name, unit, vals, timestamps, metric_file)
            self.__add_result__(metric)

            # Try to add more metrics by combining them
            if unit == "W" or unit == "J":
                power_value = None
                if unit == "W":
                    if metric.exec_time() > 0:
                        energy_name = metric_name + ":energy"
                        power_value =  metric.samples.mean()
                        value = power_value * metric.exec_time()
                        energy_metric = Metric(energy_name, "J", [value], [metric.exec_time()], metric_file)
                        self.__add_result__(energy_metric)
                elif unit == "J":
                    if metric.exec_time() > 0:
                        energy_name = metric_name + ":power"
                        power_value = metric.samples.mean() / metric.exec_time()
                        power_metric = Metric(energy_name, "W", [power_value], [metric.exec_time()], metric_file)
                        self.__add_result__(power_metric)

                if power_value is not None and self.main_value_type == "FPS":
                    efficiency_name = metric_name + ":efficiency"
                    value = self.main_value / power_value
                    unit = "{}/W".format(self.main_value_type)
                    efficiency_metric = Metric(efficiency_name, unit, [value], [metric.exec_time()], metric_file)
                    self.__add_result__(efficiency_metric)

    def result(self, key = None):
        """ Returns the result associated to the key or None if it does not exist """
        if key is None:
            if self.main_value is not None:
                return SubTestFloat(None, self.main_value_type, [self.main_value], self.test_result.test_file)
            else:
                return None
        if key in self._results:
            return self._results[key]
        else:
            return None

    def results(self, restrict_to_type = None):
        """
        Returns a set of all the available keys for results (to be queried
        individually using the result() method). You may select only one type
        of results by using the restrict_to_type parameter.

        Args:
            restrict_to_type: A BenchSubTestType to only list the results of a certain type

        """
        if restrict_to_type is None:
            return set(self._results.keys())
        else:
            return set([x for x in self._results if self._results[x].subtest_type() == restrict_to_type])


class SubTestResult:
    __slots__ = ['test_result', 'commit', 'test', 'key', 'runs', 'value_type',
                 'unit', 'results', 'average_image_file', '_cache_list', '_cache_list_stats']

    def __init__(self, testResult, test, key, runs):
        self.test_result = testResult
        self.commit = testResult.commit
        self.test = test
        self.key = key
        self.runs = runs

        self.value_type = None
        self.unit = None
        self.results = []

        for run in runs:
            run_result = run.result(key)
            if run_result is None:
                continue
            if self.value_type is None:
                self.value_type = run_result.subtest_type()
            elif self.value_type != run_result.subtest_type():
                msg ="Tried to add a result (run file '{}') for the subtest '{}' with type {} to list only containing the type {}"
                msg = msg.format(run_result.data_raw_file, key,
                                 run_result.subtest_type(), self.value_type)
                raise ValueError(msg)
            if self.unit is None:
                self.unit = run_result.unit()
            elif self.unit != run_result.unit():
                msg ="Tried to add a result (run file '{}') for the subtest '{}' with unit '{}' to list only containing the unit '{}'"
                msg = msg.format(run_result.data_raw_file, key,
                                 run_result.unit(), self.unit)
                raise ValueError(msg)

            # Do not add the results of images, we need to process them first
            if self.value_type == BenchSubTestType.SUBTEST_IMAGE:
                continue

            # Do not add empty samples
            if (run_result.value is None or
                ((self.value_type == BenchSubTestType.SUBTEST_FLOAT or
                     self.value_type == BenchSubTestType.METRIC)
                and np.math.isnan(run_result.value))):
                continue
            self.results.append((run, run_result.value))

        if self.value_type == BenchSubTestType.SUBTEST_IMAGE:
            log_folder = self.commit.report.log_folder

            # Generate average
            images = []
            for run in runs:
                result = run.result(self.key)
                if result is not None:
                    images.append(result.img_file_name)

            # Generate the average image with the list of image files
            self.average_image_file = os.path.join(log_folder, '{}.{}.avg.png'.format(testResult.test_file, self.key))
            imgcmp.average(images, self.average_image_file)

            # Compare every image to the average image
            for run in runs:
                result = run.result(self.key)
                if result is not None:
                    result.set_reference(self.average_image_file)
                    self.results.append((run, result.value))

        self._cache_list = None
        self._cache_list_stats = None

    def __len__(self):
        return len(self.to_list())

    def __getitem__(self, key):
        return self.to_list()[key]

    def __str__(self):
        if (self.value_type == BenchSubTestType.SUBTEST_FLOAT or
                self.value_type == BenchSubTestType.METRIC):
            return SubTestFloat.to_string(self.mean(), self.unit, self.margin(), len(self))
        else:
            s = self.to_set()
            if len(s) == 1:
                return str(self.to_list()[0])
            else:
                return str(s)

    def to_list(self):
        """ Returns the list of all the mean values for every run """

        if self._cache_list is None:
            self._cache_list = [x[1] for x in self.results if x[1] is not None]
        return self._cache_list

    def to_set(self):
        """ Returns a set of all the values found at every run """

        return set(self.to_list())

    def to_liststat(self):
        """ Convenience method that returns a ListStats(self.to_list()) object """

        if self._cache_list_stats is None:
            if (self.value_type == BenchSubTestType.SUBTEST_FLOAT or
                self.value_type == BenchSubTestType.SUBTEST_IMAGE or
                self.value_type == BenchSubTestType.METRIC):
                self._cache_list_stats = ListStats(self.to_list())
            else:
                self._cache_list_stats = ListStats([])
        return self._cache_list_stats

    def compare(self, old_subtestresult):
        """
        Compare the current sample distribution to old_subtestresult's

        Args:
            old_subtestresult: the subrest to compare to
            equal_var: f True (default), perform a standard independent 2 sample test that assumes equal population variances [R263]. If False, perform Welch’s t-test, which does not assume equal population variance [R264].

        Returns:
            the difference going from the old to the new result
            the confidence of them being from the same normal distribution

        WARNING: Does not work when the type is SUBTEST_STRING
        """
        if self.value_type == BenchSubTestType.SUBTEST_IMAGE:
            results = []
            for run in self.runs:
                results.append(run.result(self.key).img_compare(old_subtestresult.average_image_file))

            output = '{}_compare_{}'.format(self.average_image_file, os.path.basename(old_subtestresult.average_image_file))
            imgcmp.compare(self.average_image_file, old_subtestresult.average_image_file, ['RMSE'], output)

            # Do the reverse comparaison because the distance has no direction
            # and the oldresult's average value should be 0 anyway
            new_results = ListStats(results)
            diff, confidence = old_subtestresult.to_liststat().compare(new_results)
            return new_results.mean(), confidence
        elif self.value_type == BenchSubTestType.SUBTEST_STRING:
            # TODO: Try to come up with something a little smarter
            if self.to_set() == old_subtestresult.to_set():
                return 0, 0
            else:
                return 1, 1
        elif self.value_type == BenchSubTestType.SUBTEST_COMMIT_RESULT:
            if self.commit.compil_exit_code == old_subtestresult.commit.compil_exit_code:
                return 0, 0
            else:
                return 1, 1
        else:
            return self.to_liststat().compare(old_subtestresult.to_liststat())

    def mean(self):
        """
        Returns the mean of the values. Only works on numbers outputs.

        WARNING: Does not work when the type is SUBTEST_STRING
        """
        return self.to_liststat().mean()

    def margin(self):
        """
        Computes the margin of error for the sample set.

        WARNING: Does not work when the type is SUBTEST_STRING
        """
        return self.to_liststat().margin()

    def confidence_margin(self, wanted_margin = None, confidence=0.95):
        """
        Computes the confidence margin of error and how many samples would be
        needed to guarantee that mean of the data would be inside the wanted_margin.

        Args:
            wanted_margin: A float that represents how much variance you accept. For example, 0.025 would mean the accepted variance is 2.5%
            confidence: The wanted confidence level

        Returns:
            the current margin of error
            the number of samples needed to reach the wanted confidence

        WARNING: Does not work when the type is SUBTEST_STRING
        """

        liststat = self.to_liststat()
        return self.to_liststat().confidence_margin(wanted_margin, confidence)

    def subtest_fullname(self):
        """
        Returns the name that should be used to reproduce this result.

        WARNING: Does not work when the type is SUBTEST_STRING
        """
        if self.value_type != BenchSubTestType.METRIC:
            return Test.partial_name(self.test.full_name, [self.key])
        else:
            return Test.metric_fullname(self.test.full_name, self.key)

class TestResult:
    def __init__(self, commit, test, testType, testFile, runFiles, metricsFiles):
        self.commit = commit
        self.test = test
        self.test_file = testFile

        self.runs = []
        self.test_type = testType
        self.more_is_better = True
        self.unit = None

        self._results_cache = dict()

        self.__parse_results__(testType, testFile, runFiles, metricsFiles)

    def __parse_results__(self, testType, testFile, runFiles, metricsFiles):
        if testType == "commit_result":
            self.runs.append(TestRun(self, testType, "", []))
        elif testType != "unified":
            # Read the data and abort if there is no data
            data, unit, self.more_is_better = readCsv(testFile)
            if len(data) == 0:
                raise ValueError("The TestResult {} does not contain any runs".format(testFile))

            if len(data) != len(runFiles):
                print("The test result {} does not contain all the runs ({} vs {}). Ignore data...".format(testFile, len(data), len(runFiles)), file=sys.stderr)
                data = [-1] * len(runFiles)

            if unit is None:
                unit = "FPS"
            self.unit = sys.intern(unit)

            # Check that we have the same unit as the test
            if self.test.unit != self.unit:
                if self.test.unit != "undefined":
                    msg = "The unit used by the test '{test}' changed from '{unit_old}' to '{unit_new}' in commit {commit}"
                    print(msg.format(test=self.test.full_name,
                                    unit_old=self.test.unit,
                                    unit_new=self.unit,
                                    commit=self.commit.sha1))
                self.test.unit = unit

            for i in range(0, len(runFiles)):
                run = TestRun(self, testType, runFiles[i], metricsFiles[runFiles[i]], unit, data[i])
                self.runs.append(run)
        else:
            for i in range(0, len(runFiles)):
                run = TestRun(self, testType, runFiles[i], metricsFiles[runFiles[i]], None, None)
                self.runs.append(run)


    def result(self, key = None):
        """ Returns the result associated to the key or None if it does not exist """
        cached_result = self._results_cache.get(key, None)
        if cached_result is not None:
            return cached_result

        if len(self.runs) == 0:
            raise ValueError('Cannot get the results when there are no runs ({})'.format(self.test_file))
        result = SubTestResult(self, self.test, key, self.runs)
        self._results_cache[key] = result

        return result

    def results(self, restrict_to_type = None):
        """
        Returns a set of all the available keys for results (to be queried
        individually using the result() method). You may select only one type
        of results by using the restrict_to_type parameter.

        Args:
            restrict_to_type: A BenchSubTestType to only list the results of a certain type

        """

        res = set()
        for run in self.runs:
            res |= run.results(restrict_to_type)
        return res


class Commit:
    def __init__(self, report, sha1, full_name, label):
        self.report = report
        self.sha1 = sha1
        self.full_name = full_name
        self.label = label

        self.results = dict()
        self.geom_mean_cache = -1
        self.oldness_factor = 0

        self.__parse_commit_information__(report)

    def __eq__(x, y):
        if y is None:
            return False
        return x.sha1 == y.sha1

    def __hash__(self):
        return hash(self.sha1)

    def __parse_commit_information__(self, report):
        self.compile_log = self.sha1 + "_compile_log"
        self.patch = self.sha1 + ".patch"

        # Set default values then parse the patch
        self.full_sha1 = self.sha1
        self.author = "UNKNOWN AUTHOR"
        self.commiter = "UNKNOWN COMMITER"
        self.author_date = datetime.min
        self.commit_date = datetime.min
        self.title = ''
        self.commit_log = ''
        self.signed_of_by = set()
        self.reviewed_by = set()
        self.tested_by = set()
        self.bugs = set()
        try:
            with open(self.patch, 'r') as f:
                log_started = False
                fdo_bug_re = re.compile('fdo#(\d+)')
                basefdourl = "https://bugs.freedesktop.org/show_bug.cgi?id="
                for line in f:
                    line = line.strip()
                    if not log_started:
                        if line == "---": # Detect the end of the header
                            break
                        elif line.startswith('commit'):
                            self.full_sha1 = line.split(' ')[1]
                        elif line.startswith('Author:'):
                            self.author = line[12:]
                        elif line.startswith('AuthorDate: '):
                            self.author_date = datetime.fromtimestamp(mktime_tz(parsedate_tz(line[12:])))
                        elif line.startswith('Commit:'):
                            self.commiter = line[12:]
                        elif line.startswith('CommitDate: '):
                            self.commit_date = datetime.fromtimestamp(mktime_tz(parsedate_tz(line[12:])))
                        elif line == '':
                            # The commit log is about to start
                            log_started = True
                    else:
                        if self.title == '':
                            self.title = line
                        else:
                            self.commit_log += line + '\n'
                            if line.startswith('Reviewed-by: '):
                                self.reviewed_by |= {line[13:]}
                            elif line.startswith('Signed-off-by: '):
                                self.signed_of_by |= {line[15:]}
                            elif line.startswith('Tested-by: '):
                                self.tested_by |= {line[11:]}
                            elif line.startswith('Bugzilla: '):
                                self.bugs |= {line[10:]}
                            elif line.startswith('Fixes: '):
                                self.bugs |= {line[7:]}
                            else:
                                fdo_bug_m = fdo_bug_re.search(line)
                                if fdo_bug_m is not None:
                                    bugid = fdo_bug_m.groups()[0]
                                    self.bugs |= {basefdourl + bugid}
        except Exception:
            self.patch = None
            pass

        # Look for the exit code
        self.compil_exit_code = RunnerErrorCode.UNKNOWN
        if report.journal.deployed_count(self.full_sha1) > 0:
            self.compil_exit_code = RunnerErrorCode.NO_ERROR
        elif report.journal.deploy_count(self.full_sha1) > 1:
            self.compil_exit_code = RunnerErrorCode.DEPLOYMENT_ERROR
        else:
            # Last resort, try to inspect the compilation logs
            try:
                with open(self.compile_log, 'r') as f:
                    for line in f:
                        pass
                    # Line contains the last line of the report, parse it
                    s = "Exiting with error code "
                    if line.startswith(s):
                        self.compil_exit_code = RunnerErrorCode(int(line[len(s):]))
            except Exception:
                self.compile_log = None
                pass

    def build_broken(self):
        return (self.compil_exit_code.value >= RunnerErrorCode.COMP_DEP_UNK_ERROR.value and
                self.compil_exit_code.value <= RunnerErrorCode.DEPLOYMENT_ERROR.value)

    def geom_mean(self):
        """ Returns the geometric mean of the average performance of all the
        tests (default key).
        """

        if self.geom_mean_cache >= 0:
            return self.geom_mean_cache

        # compute the variance
        s = 1
        n = 0
        for result in self.results.values():
            testresults = result.result()
            if len(testresults) > 0:
                s *= testresults.mean()
                n = n + 1
        if n > 0:
            value = s ** (1 / n)
        else:
            value = 0

        geom_mean_cache = value
        return value

    def results_set(self):
        """ Returns the list of results found on this commit"""

        results = set()
        for result in self.results.values():
            for key in result.results():
                results.add(Test.partial_name(result.test.full_name, [key]))
        return results

    def result_by_name(self, result):
        """ Look for $result and return it if available. Return None otherwise."""

        basename, subtests, metrics = Test.parse_name(result)
        if len(subtests) > 1:
            raise ValueError("The result name contains more than one result")

        r = self.results.get(basename, None)
        if r is not None:
            key = None
            if len(subtests) > 0:
                key = subtests[0]
            return r.result(key)
        else:
            return None

class EventCommitRange:
    def __init__(self, old, new = None, commit_graph = None):
        """
        Create a commit range.

        Args:
            old: the oldest commit (instance of Commit) of the commit range
            new: the newest commit (instance of Commit) of the commit range or None
            commit_graph: The graph containing all the commits before old and new
                          for the wanted results

        Returns:
            A commit range
        """

        self.old = old
        if new is None:
            self.new = old
        else:
            self.new = new

        self.commit_graph = commit_graph

    def is_single_commit(self):
        return self.distance() <= 1

    def commit_date(self):
        if self.old is not None:
            return self.old.commit_date
        elif self.new is not None:
            return self.new.commit_date
        else:
            return datetime.min

    def average_oldness_factor(self):
        """
        Returns the average oldness factor of the range (between old and new)
        """
        if self.old is not None and self.new is not None:
            return self.old.oldness_factor + (self.new.oldness_factor - self.old.oldness_factor) / 2
        elif self.old is not None:
            return self.old.oldness_factor
        else:
            return self.new.oldness_factor

    def distance(self):
        """
        Returns the number of commits between old and new
        """
        if self.commit_graph is not None:
            return len(self.commit_graph)
        elif self.old == self.new:
            return 1
        else:
            return sys.maxsize

    def bisect_point(self, ignore_commits = set()):
        """
        Find the most suitable bisecting point in the associated commit graph.
        Ignore all the commits found as $ignore_commits.

        Args:
            ignore_commits: commits to ignore, as they do not work (for instance)

        Returns:
            The commit ID of the most suitable bisecting point, None otherwise
        """
        try:
            return self.bisect_scores(ignore_commits)[0][0]
        except Exception as e:
            return None

    def bisect_scores(self, ignore_commits = set()):
        """
        Get the most suitable bisecting points in the associated commit graph.
        Ignore all the commits found as $ignore_commits.

        Args:
            ignore_commits: commits to ignore, as they do not work (for instance)

        Returns:
            A list of tuples (commit_id, score), ordered from the most suitable
            to the least suitable bisecting points.
        """
        if self.commit_graph is None:
            return []

        scores = self.commit_graph.bisecting_scores(self.new.full_sha1)
        return list(filter(lambda x: x[0] not in ignore_commits, scores))

    def __eq__(x, y):
        if isinstance(y, EventCommitRange) == False:
            return False

        if x.is_single_commit() and y.is_single_commit():
            return x.new == y.new
        else:
            return x.old == y.old and x.new == y.new

    def __hash__(self):
        if self.is_single_commit():
            return hash(self.new)
        else:
            return hash(self.old) ^ hash(self.new)

    def date(self):
        if self.new == None:
            return "{}".format(self.old.commit_date)
        elif self.is_single_commit():
            return "{}".format(self.new.commit_date)
        elif self.old is not None:
            return "between {} and {}".format(self.old.commit_date, self.new.commit_date)
        else:
            return "before {}".format(self.new.commit_date)

    def __str__(self):
        if self.new == None:
            return "{}".format(self.old.full_name)

        if self.is_single_commit():
            return "{}".format(self.new.full_name)
        elif self.old is not None:
            distance = self.distance()
            if distance == -1:
                distance = "unkown"
            return "commit range {}:{}({} commits, ~{} steps)".format(self.old.sha1, self.new.sha1,
                                                   distance, math.ceil(math.log2(distance)))
        else:
            return "commit before {}".format(self.new.full_name)

class Event:
    def __init__(self, event_type, commit_range, test, subresult_key, significance, short_desc):
        self.event_type = event_type
        self.commit_range = commit_range
        self.test = test
        self.subresult_key = subresult_key
        self.significance = significance
        self.short_desc = short_desc

        if test is not None:
            self.full_name = Test.partial_name(test.full_name, [subresult_key])
        else:
            self.full_name = "<not a test>"

    def __str__(self):
        if self.test is not None:
            return "{}: {}: {}".format(self.commit_range, self.test.full_name, self.short_desc)
        else:
            return "{}: {}".format(self.commit_range, self.short_desc)

class EventBuildStatusChanged(Event):
    def __init__(self, commit_range):
        desc = "status went from {} to {}"
        desc = desc.format(commit_range.old.compil_exit_code, commit_range.new.compil_exit_code)

        super().__init__("build", commit_range, None, None, 1, desc)

class EventPerfChange(Event):
    def __init__(self, commit_range, old_result, new_result, confidence):
        self.new_result = new_result
        self.old_result = old_result
        self.confidence = confidence

        if old_result.key != new_result.key:
            raise ValueError("Results should have the same key (old={}, new={})".format(old_result.key, new_result.key))

        if old_result.unit != new_result.unit:
            raise ValueError("Results should have the same unit (old={}, new={})".format(old_result.unit, new_result.unit))

        key = self.old_result.key
        if key is None or len(key) == 0:
            key = "main value"

        msg = "{} went from {:.2f} to {:.2f} {} ({:+.2f}%) with confidence p={:.2f}"
        desc = msg.format(key, self.old_result.mean(), self.new_result.mean(),
                          self.new_result.unit, self.diff() * 100, self.confidence)

        super().__init__("perf", commit_range, old_result.test, old_result.key, abs(self.diff()), desc)

    def diff(self):
        if self.old_result.mean() != 0:
            return (1 - (self.new_result.mean() / self.old_result.mean())) * -1
        elif self.new_result.mean() == 0 and self.old_result.mean() == 0:
            return 0
        else:
            return float("inf")

    def __str__(self):
        msg = "{} changed the performance of {}: {}"
        return msg.format(self.commit_range, self.old_result.test.full_name, self.short_desc)

class EventResultNeedsMoreRuns(Event):
    def __init__(self, result, wanted_n):
        self.result = result
        self._wanted_n = wanted_n

        key = self.result.key
        if key is None or len(key) == 0:
            key = "main value"

        msg = "{} requires at least {} runs, found {}"
        desc = msg.format(key, self.wanted_n(), len(self.result))

        super().__init__("variance", EventCommitRange(result.commit), result.test, result.key, wanted_n, desc)

    def wanted_n(self):
        return self._wanted_n

class EventInsufficientSignificance(EventResultNeedsMoreRuns):
    def __init__(self, result, wanted_margin):
        super().__init__(result, result.confidence_margin(wanted_margin)[1])
        self.wanted_margin = wanted_margin

        key = self.result.key
        if key is None or len(key) == 0:
            key = "main value"

        msg = "{} requires more runs to reach the wanted margin ({:.2f}% vs {:.2f}%), proposes n = {}, found {}."
        self.short_desc.format(key, self.margin() * 100, self.wanted_margin * 100,
                               self.wanted_n(), len(self.result))

    def margin(self):
        return self.result.confidence_margin(self.wanted_margin)[0]

class EventUnitResultChange(Event):
    def __init__(self, commit_range, old_result, new_result):
        self.old_result = old_result
        self.new_result = new_result
        self.old_status = old_result
        self.new_status = new_result

        if old_result.key != new_result.key:
            raise ValueError("Results should have the same key (old={}, new={})".format(old_result.key, new_result.key))

        if old_result.unit != new_result.unit:
            raise ValueError("Results should have the same unit (old={}, new={})".format(old_result.unit, new_result.unit))

        msg = "{}: {} -> {}"
        desc = msg.format(self.old_result.key, self.old_status, self.new_status)

        super().__init__("unit test",commit_range, old_result.test, old_result.key, 2, desc)

class EventUnitResultUnstable(Event):
    def __init__(self, result):
        self.result = result

        msg = "{}: unstable results ({})"
        desc = msg.format(self.result.key, self.result.to_set())

        super().__init__("variance", EventCommitRange(result.commit), result.test, result.key, 2, desc)

class EventRenderingChange(Event):
    def __init__(self, commit_range, result, difference, confidence):
        self.result = result
        self.difference = difference
        self.confidence = confidence

        msg = "frame ID {} changed by {:.5f} RMSE with confidence p={:.2f}"
        desc = msg.format(self.result.key, self.diff(), self.confidence)

        super().__init__("rendering", commit_range, result.test, result.key, abs(self.diff()), desc)

    def diff(self):
        return self.difference

class EventDivergingBaseResult(Event):
    def __init__(self, result, merge_base):
        self.result = result
        self.merge_base = merge_base

        key = self.result.key
        if key is None or len(key) == 0:
            key = "main value"

        msg = "{} diverges from at least one other base result, requires testing on the merge base ({})"
        desc = msg.format(key, merge_base)

        super().__init__("divergence", EventCommitRange(result.commit), result.test, result.key, 1, desc)

class Journal:
    def __init__(self, filepath):
        self._journal = dict()

        try:
            with open(filepath, 'r') as f:
                for entry in f.readlines():
                    entry = entry.strip()
                    fields = entry.split(',')
                    if not fields or len(fields) < 3:
                        continue

                    # Parse the time
                    attrs = dict()
                    try:
                        attrs["timestamp"] = float(fields[0])
                    except:
                        continue

                    op = fields[1]
                    if op == "test" or op == "tested":
                        key=",".join(fields[2:4])

                        attrs["version"] = fields[2]
                        attrs["test"] = fields[3]

                        if len(fields) > 4:
                            attrs["result_file"] = fields[4]
                    else:
                        key=",".join(fields[2:])

                    self.__add_value__(op, key, attrs)
        except Exception:
            pass

    def __add_value__(self, op, key, attrs):
        if op not in self._journal:
            self._journal[op] = dict()
        if key not in self._journal[op]:
            self._journal[op][key] = [attrs]
        else:
            self._journal[op][key].append(attrs)

    def __key_test__(self, version, test_name):
        return "{},{}".format(version, test_name)

    def count(self, operation, key):
        return len(self._journal.get(operation, dict()).get(key, []))

    def deploy_count(self, version):
        return self.count("deploy", version)

    def deployed_count(self, version):
        return self.count("deployed", version)

    def test_count(self, version, test_name):
        return self.count("test", self.__key_test__(version, test_name))

    def tested_count(self, version, test_name):
        return self.count("tested", self.__key_test__(version, test_name))

    def incomplete_tests(self):
        if "test" not in self._journal:
            return []

        incomplete_tests = []
        result_file_set = set()
        for key in self._journal["test"]:
            for test_attrs in self._journal["test"][key]:
                if "result_file" not in test_attrs:
                    continue

                found = False
                if "tested" in self._journal and key in self._journal["tested"]:
                    for tested_attrs in self._journal["tested"][key]:
                        if "result_file" not in tested_attrs:
                            continue

                        if test_attrs["result_file"] == tested_attrs["result_file"]:
                            found = True
                            break

                # We did not find the same result file in the "tested" set,
                # this means the run did not complete!
                if not found and test_attrs["result_file"] not in result_file_set:
                    incomplete_tests.append(test_attrs)
                    result_file_set.add(test_attrs["result_file"])

        return incomplete_tests

class Report:
    def __init__(self, log_folder, silentMode = False, restrict_to_commits = []):
        self.log_folder = log_folder
        self.silentMode = silentMode
        self.name = os.path.basename(os.path.abspath(log_folder))

        self.journal = Journal(self.log_folder + "/journal")

        self.tests = list()
        self.commits = list()
        self.notes = list()
        self.events = list()

        self._cached_walk = dict()

        self.__parse_report__(restrict_to_commits)

    def __readNotes__(self):
        try:
            with open("notes", 'rt') as f:
                return f.readlines()
        except:
            return []

    def __readCommitLabels__(self):
        labels = dict()
        try:
            f = open( "commit_labels", "r")
            try:
                labelLines = f.readlines()
            finally:
                f.close()
        except IOError:
            return labels

        for labelLine in labelLines:
            fields = labelLine.split(" ")
            sha1 = fields[0]
            label = fields[1].split("\n")[0]
            labels[sha1] = label

        return labels

    def log(self, msg, temporary=False):
        if self.silentMode:
            return

        sys.stdout.write(msg)
        sys.stdout.write(" " * (79 - len(msg)))
        sys.stdout.write("\r")
        sys.stdout.flush()

    def __parse_report__(self, restrict_to_commits):
        # Save the current working directory and switch to the log folder
        cwd = os.getcwd()
        os.chdir(self.log_folder)

        # Look for the commit_list file
        try:
            f = open( "commit_list", "r")
            try:
                commitsLines = f.readlines()
            finally:
                f.close()
        except IOError:
            if not self.silentMode:
                sys.stderr.write("The log folder '{0}' does not contain a commit_list file\n".format(self.log_folder))
            return False

        # Read all the commits' labels
        labels = self.__readCommitLabels__()

        # Check that there are commits
        if (len(commitsLines) == 0):
            self.log("The commit_list file is empty\n")
            return False

        self.log("Listing the results' files", temporary=True)

        # Find all the result files and sort them by sha1
        files_list = os.listdir()
        testFiles = dict()
        testResults = dict()
        commit_test_file_re = re.compile(r'^(.+)_(bench|unit|imgval|unified)_[^\.]+(.metrics_[^\.]+)?$')
        results_count = 0
        for f in files_list:
            if os.path.isdir(f):
                continue
            m = commit_test_file_re.match(f)
            if m is not None:
                sha1 = m.groups()[0]
                if sha1 not in testFiles:
                    testFiles[sha1] = []
                result_type = m.groups()[1]
                testFiles[sha1].append((f, result_type))

                 # Skip on unrelated files
                if "." in f:
                    continue

                # Skip when the file is a run file (finishes by #XX)
                if result_type != "unified" and re.search(r'#\d+$', f) is not None:
                    continue

                if sha1 not in testResults:
                    testResults[sha1] = []
                testResults[sha1].append((f, result_type))
                results_count += 1
        files_list = None

        self.log("Found {} results across {} commits".format(results_count, len(commitsLines)))

        # Verify the state of the commits
        ezbench_runner = Test("ezbench_runner")
        self.tests.append(ezbench_runner)

        # Gather all the information from the commits
        commits_txt = ""
        table_entries_txt = ""
        result_cur = 0
        for commitLine in commitsLines:
            full_name = commitLine.strip(' \t\n\r')
            sha1 = commitLine.split()[0]

            label = labels.get(sha1, sha1)
            if (len(restrict_to_commits) > 0 and sha1 not in restrict_to_commits
                and label not in restrict_to_commits):
                continue
            commit = Commit(self, sha1, full_name, label)

            # If there are no results, just continue
            if sha1 in testResults:
                handled_tests = set()
                for testFile, testType in testResults[sha1]:
                    # Unified-formated runs should not have the # in their name
                    testFile = testFile.split("#")[0]
                    if testFile not in handled_tests:
                        handled_tests.add(testFile)
                    else:
                        continue

                    result_cur += 1
                    self.log("Reading result {}/{}".format(result_cur, results_count), temporary=True)

                    # Get the test name
                    test_name = testFile[len(commit.sha1) + len(testType) + 2:]

                    # Find the right Test or create one if none are found
                    try:
                        test = next(b for b in self.tests if b.full_name == test_name)
                    except StopIteration:
                        test = Test(test_name)
                        self.tests.append(test)

                    # Look for the runs
                    run_re = re.compile(r'^{testFile}#[0-9]+$'.format(testFile=testFile))
                    runsFiles = [f for f,t in testFiles[sha1] if run_re.search(f)]
                    runsFiles.sort(key=lambda x: '{0:0>100}'.format(x).lower()) # Sort the runs in natural order

                    # Look for metrics!
                    metricsFiles = dict()
                    for runFile in runsFiles:
                        metricsFiles[runFile] = list()
                        metrics_re = re.compile(r'^{}.metrics_.+$'.format(runFile))
                        for metric_file in [f for f,t in testFiles[sha1] if metrics_re.search(f)]:
                            metricsFiles[runFile].append(metric_file)

                    # Create the result object
                    try:
                        result = TestResult(commit, test, testType, testFile, runsFiles, metricsFiles)

                        # Add the result to the commit's results
                        commit.results[test.full_name] = result
                        commit.compil_exit_code = RunnerErrorCode.NO_ERROR # The deployment must have been successful if there is data
                    except Exception as e:
                        traceback.print_exc(file=sys.stderr)
                        sys.stderr.write("\n")
                        pass

            # Add the information about the runtime and the commit to the list of commits
            # INFO: Do not add the commit if we got no meaningful results for it
            if len(commit.results) > 0 or commit.compil_exit_code != RunnerErrorCode.UNKNOWN:
                result = TestResult(commit, ezbench_runner, "commit_result", None, None, None)
                commit.results[result.test.full_name] = result
                self.commits.append(commit)

        # Go through all the runs and add the missing results
        for commit in self.commits:
            for result in commit.results.values():
                for run in result.runs:
                    run.tag_missing_results()

        # Sort the list of tests
        self.tests = sorted(self.tests, key=lambda test: test.full_name)

        # Read the notes before going back to the original folder
        notes = self.__readNotes__()

        # Go back to the original folder
        os.chdir(cwd)

    def find_commit_by_id(self, sha1):
        for commit in self.commits:
            if commit.sha1 == sha1 or commit.full_sha1 == sha1:
                return commit
        return None

    def find_result(self, commit, test):
        return commit.results.get(test.full_name, None)

    def find_result_by_name(self, commit, test_full_name):
        return commit.results.get(test_full_name, None)

    def overlay_graphs(self, scm):
        overlay = ResultsDAG(scm)

        if len(self.commits) == 1:
            return overlay

        self.log("Generate the results overlay graph", temporary=True)

        g = scm.subDAG([c.full_sha1 for c in self.commits])
        count = 1
        for commit in self.commits:
            self.log("Overlay graph: get results list for commit {}/{}".format(count, len(g)), temporary=True)
            count += 1

            full_sha1 = scm.full_version_name(commit.sha1)
            overlay.set_results(full_sha1, commit.results_set())
            g.set_results(full_sha1, commit.results_set())

        count = 1
        for commit in self.commits:
            self.log("Overlay graph: Find closests result [{}/{}]".format(count, len(self.commits)), temporary=True)
            count += 1

            # Look for the closest commits from this position and add them to
            # the overlay
            w = scm.full_version_name(commit.sha1)
            graphs_closests = g.find_closest_nodes_with_results(w)
            for c, r in graphs_closests:
                overlay.add_edge(w, c, results=r)

        return overlay

    def __enhance_report_check_variance__(self, variance_cache, result, max_variance):
        cached_value = variance_cache.get(result, None)
        if cached_value is not None:
            return cached_value

        if result.value_type == BenchSubTestType.SUBTEST_FLOAT:
            if result.margin() > max_variance:
                self.events.append(EventInsufficientSignificance(result, max_variance))
                variance_cache[result] = True
                return True
        elif result.value_type == BenchSubTestType.SUBTEST_IMAGE:
            # FIXME: Need special handling here
            return False
        elif result.value_type == BenchSubTestType.SUBTEST_STRING:
            if len(result.to_set()) > 1:
                self.events.append(EventUnitResultUnstable(result))
                variance_cache[result] = True
                return True

        return False

    def __enhance_report_cached_walk__(self, scm, heads, ignores):
        k = (frozenset(heads), frozenset(ignores))
        cached = self._cached_walk.get(k, None)
        if cached == None:
            cached = scm.walk(heads, ignores)
            self._cached_walk[k] = cached

        return cached

    def enhance_report(self, scm, max_variance = 0.025,
                       min_diff_confidence = 0.99, smallest_perf_change=0.005,
                       variance_min_run_count = 2):
        # Find the oldest commit we have
        now = datetime.now()
        oldest_commit = now
        for c in self.commits:
            if c.commit_date < oldest_commit:
                oldest_commit = c.commit_date

        # Compute the oldness factor of all the commits
        biggest_timedelta = (now - oldest_commit)
        for c in self.commits:
            commit_timedelta = now - c.commit_date
            c.oldness_factor = max(0.1, min(1, commit_timedelta / biggest_timedelta))

        # Generate the overlay graph containing every commit with results for
        # all the results we have.
        overlay = self.overlay_graphs(scm)

        # Compute the list of commits and set of results found on all the commits
        results = set()
        commits_list = []
        for commit in self.commits:
            results |= commit.results_set()
            commits_list.append(commit.full_sha1)

        # For all results, find what are the changes
        variance_cache = dict()
        count = 1
        for result in results:
            self.log("Analyse result {}/{}".format(count, len(results)), temporary=True)
            count += 1

            bottom_leaves = set(commits_list)
            for child in overlay.nodes():
                 # Skip if the result is not present on the current node
                if result not in overlay.results(child):
                    # Remove the node from the bottom leaves since it does not
                    # have the result
                    try:
                        bottom_leaves.remove(child)
                    except:
                        pass
                    continue

                # Get the commit and results
                commit_child = self.find_commit_by_id(child)
                after = commit_child.result_by_name(result)

                # completely ignore metrics for now
                if after is None or after.value_type == BenchSubTestType.METRIC:
                    break

                # Go through all the parents of the child
                has_one_similar_parent = False
                has_one_inconclusive_parent = False
                potential_changes = []
                parents_for_current_result = set()
                for parent in overlay.parents(child):
                    # Skip if the result is not in our overlay graph
                    if result not in overlay.edge_results(parent, child):
                        continue
                    else:
                        # Remove the child from the bottom leaves since we are
                        # its parent, we are closer to being a bottom leaf
                        try:
                            bottom_leaves.remove(child)
                        except:
                            pass

                    # Add the current parent in the list of parents for this result
                    parents_for_current_result.add(parent)

                    commit_parent = self.find_commit_by_id(parent)
                    before = commit_parent.result_by_name(result)

                    # Generate variance events if necessary
                    variance_too_high_before = self.__enhance_report_check_variance__(variance_cache, before, max_variance)
                    variance_too_high_after = self.__enhance_report_check_variance__(variance_cache, after, max_variance)

                    # Compare the two data sets
                    diff, confidence = after.compare(before)
                    if confidence >= min_diff_confidence:
                        if before.value_type == BenchSubTestType.SUBTEST_FLOAT:
                            if diff >= smallest_perf_change:
                                potential_changes.append((parent, before, after, diff, confidence))
                        elif before.value_type == BenchSubTestType.SUBTEST_STRING:
                            if variance_too_high_before or variance_too_high_after:
                                has_one_inconclusive_parent = True
                                continue

                            if len(before) < variance_min_run_count:
                                self.events.append(EventResultNeedsMoreRuns(before, variance_min_run_count))
                            if len(after) < variance_min_run_count:
                                self.events.append(EventResultNeedsMoreRuns(after, variance_min_run_count))
                            if len(before) >= variance_min_run_count and len(after) >= variance_min_run_count:
                                potential_changes.append((parent, before, after, diff, confidence))
                            else:
                                has_one_inconclusive_parent = True
                        elif before.value_type == BenchSubTestType.SUBTEST_IMAGE:
                            # Ignore insignificant changes
                            if  diff < 1.0e-4:
                                continue
                            if len(before) < 2:
                                self.events.append(EventResultNeedsMoreRuns(before, 2))
                            if len(after) < 2:
                                self.events.append(EventResultNeedsMoreRuns(after, 2))
                            if len(before) >= 2 and len(after) >= 2:
                                potential_changes.append((parent, before, after, diff, confidence))
                            else:
                                has_one_inconclusive_parent = True
                        elif before.value_type == BenchSubTestType.SUBTEST_COMMIT_RESULT:
                            potential_changes.append((parent, before, after, diff, confidence))
                    else:
                        # Mark that we have found at least one case where the
                        # child and the parent have the same results
                        has_one_similar_parent = True

                # Now that we went through all the parents, we can check what to do
                # with all the changes
                if not has_one_similar_parent and not has_one_inconclusive_parent and len(parents_for_current_result) > 0:
                    commit_graph = self.__enhance_report_cached_walk__(scm, [child], parents_for_current_result)

                    # Create the events
                    for parent, before, after, diff, confidence in potential_changes:
                        commit_parent = self.find_commit_by_id(parent)
                        commit_range = EventCommitRange(commit_parent, commit_child, commit_graph)

                        if before.value_type == BenchSubTestType.SUBTEST_FLOAT:
                            middle = commit_range.bisect_point()
                            self.events.append(EventPerfChange(commit_range,
                                                        before, after,
                                                        confidence))
                        elif before.value_type == BenchSubTestType.SUBTEST_STRING:
                            self.events.append(EventUnitResultChange(commit_range,
                                                    before,
                                                    after))
                        elif before.value_type == BenchSubTestType.SUBTEST_IMAGE:
                            self.events.append(EventRenderingChange(commit_range,
                                                                    after, diff,
                                                                    confidence))
                        elif before.value_type == BenchSubTestType.SUBTEST_COMMIT_RESULT:
                            self.events.append(EventBuildStatusChanged(commit_range))

            # Now compare all the bottom leaves to see if they match, if they
            # don't, then we need to add the merge base for testing!
            bottoms = set(bottom_leaves)
            first_bottom = bottoms.pop()
            first_bottom_result = self.find_commit_by_id(first_bottom).result_by_name(result)

            # completely ignore metrics for now
            if first_bottom_result is None or first_bottom_result.value_type == BenchSubTestType.METRIC:
                continue

            diverge = False
            for bottom in bottoms:
                bottom_result = self.find_commit_by_id(bottom).result_by_name(result)
                if bottom_result is None:
                    continue

                diff, confidence = first_bottom_result.compare(bottom_result)
                if confidence >= min_diff_confidence:
                    diverge = True
                    break

            # We found an actual change,
            if diverge:
                merge_base = scm.merge_base(bottom_leaves)
                for bottom in bottom_leaves:
                    bottom_result = self.find_commit_by_id(bottom).result_by_name(result)
                    self.events.append(EventDivergingBaseResult(bottom_result, merge_base))

        return overlay

    @classmethod
    def event_tree(cls, reports):
        events_tree = OrderedDict()
        for report in reports:
            r = report.name

            report.events = sorted(report.events, key=lambda e: e.commit_range.commit_date(), reverse=True)
            for e in report.events:
                c = e.commit_range
                if c not in events_tree:
                    events_tree[c] = OrderedDict()

                t = e.event_type
                if t not in events_tree[c]:
                    events_tree[c][t] = OrderedDict()

                if e.test is None:
                    test = "ezbench.build"
                else:
                    test = e.test.full_name
                if test not in events_tree[c][t]:
                    events_tree[c][t][test] = OrderedDict()

                if r not in events_tree[c][t][test]:
                    events_tree[c][t][test][r] = list()

                events_tree[c][t][test][r].append(e)

        # Order by severity
        for c in events_tree:
            for t in events_tree[c]:
                for r in events_tree[c][t]:
                    for test in events_tree[c][t][r]:
                        if not isinstance(test, Event):
                            sorted(events_tree[c][t][r][test], key=lambda e: e.significance)

        return events_tree


def readCsv(filepath):
    data = []

    h1 = re.compile('^# (.*) of \'(.*)\' using commit (.*)$')
    h2 = re.compile('^# (.*) \\((.*) is better\\) of \'(.*)\' using (commit|version) (.*)$')

    with open(filepath, 'rt') as f:
        reader = csv.reader(f)
        unit = None
        more_is_better = True
        try:
            for row in reader:
                if row is None or len(row) == 0:
                    continue

                # try to extract information from the header
                if unit is None:
                    m1 = h1.match(row[0])
                    m2 = h2.match(row[0])
                    if m2 is not None:
                        # groups: unit type, more|less qualifier, test, commit/version, commit_sha1
                        unit = m2.groups()[0]
                        more_is_better = m2.groups()[1].lower() == "more"
                    elif m1 is not None:
                        # groups: unit type, test, commit_sha1
                        unit = m1.groups()[0]

                # Read the actual data
                if len(row) > 0 and not row[0].startswith("# "):
                    try:
                        data.append(float(row[0]))
                    except ValueError as e:
                        sys.stderr.write('Error in file %s, line %d: %s\n' % (filepath, reader.line_num, e))
        except csv.Error as e:
            sys.stderr.write('file %s, line %d: %s\n' % (filepath, reader.line_num, e))
            return [], "none"

    return data, unit, more_is_better

def readUnitRun(filepath):
    tests = dict()
    with open(filepath, 'rt') as f:
        for line in f.readlines():
            fields = line.split(':')
            if len(fields) == 2:
                tests[fields[0]] = fields[1].strip()
    return tests

def convert_unit(value, input_unit, output_unit):
	ir_fps = -1.0

	if input_unit == output_unit:
		return value

	if input_unit.lower() == "fps":
		ir_fps = value
	elif value == 0:
		return 0

	if input_unit == "s":
		ir_fps = 1.0 / value
	elif input_unit == "ms":
		ir_fps = 1.0e3 / value
	elif input_unit == "us" or output_unit == "µs":
		ir_fps = 1.0e6 / value

	if ir_fps == -1:
		print("convert_unit: Unknown input type '{}'".format(input_unit))
		return value

	if output_unit.lower() == "fps":
		return ir_fps
	elif ir_fps == 0:
		return float('+inf')

	if output_unit == "s":
		return 1.0 / ir_fps
	elif output_unit == "ms":
		return 1.0e3 / ir_fps
	elif output_unit == "us" or output_unit == "µs":
		return 1.0e6 / ir_fps

	print("convert_unit: Unknown output type '{}'".format(output_unit))
	return value

def compute_perf_difference(unit, target, value):
    if unit == "s" or unit == "ms" or unit == "us" or unit == "µs" or unit == "J" or unit == "W":
        if value != 0:
            return target * 100.0 / value
        else:
            return 100
    else:
        if target != 0:
            return value * 100.0 / target
        else:
            return 100
