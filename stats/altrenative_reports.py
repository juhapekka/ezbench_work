#!/usr/bin/env python3

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

import collections
import sys
import os
import argparse
import traceback
import gzip
from http.server import BaseHTTPRequestHandler, HTTPServer

# Import ezbench from the utils/ folder
ezbench_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ezbench_dir, 'python-modules'))
sys.path.append(ezbench_dir)

from utils.env_dump.env_dump_parser import *
from ezbench.smartezbench import *
from ezbench.report import *

import htmlReportMain
import altrenative_reports_events
import altrenative_reports_trend
import altrenative_reports_tests

global_db = None
global_html = None
global_log_folder = None

class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    #######################
    ## return image
    #######################
    def give_image(self, image_name):
        real_name = "{}/{}".format(global_log_folder, image_name.split("_",  1)[1] )
        f = open(real_name, 'rb')
        rval = f.read()
        f.close()
        return rval

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

###
# Main handler for the server, this is where all html is sent from.
#
    def do_GET(self):
        return_html = None
        response_code = 200
        
        #small scale caching of results here.
        if os.path.basename(self.path.replace("%20", " ")) in global_db.served_htmls_dict:
            if 'accept-encoding' in self.headers and 'gzip' in self.headers['accept-encoding']:
                return_html = global_db.served_htmls_dict[os.path.basename(self.path.replace("%20", " "))]
                self.send_response(response_code)
                self.send_header('Content-type','text/html')
                self.send_header('content-encoding', 'gzip')
                self.send_header('content-length', len(return_html))
                self.end_headers()
                self.wfile.write(return_html)
                return
            else:
                return_html = str(gzip.decompress(global_db.served_htmls_dict[os.path.basename(self.path.replace("%20", " "))]),'utf-8')
        else:
            ###
            # Everything that will be served is coming through this list, if it's not in the list its 404.
            #
            try:
                chooser = os.path.basename(self.path.split("_")[0])
                listed = ["result", "trends.html", "events.html" ]
                return_html = {
                    "": lambda x: global_html,
                    "/": lambda x: global_html,
                    "index.html": lambda x: global_html,
                    "events.html": lambda x: altrenative_reports_events.list_events(global_db),
                    "result": lambda x: altrenative_reports_events.event_result(global_db, x),
                    "commits.html": lambda x: "commits!!",
                    "trends.html": lambda x: altrenative_reports_trend.trend_page(global_db, x),
                    "detail.html": lambda x: "detail",
                    "tests.html": lambda x: altrenative_reports_tests.tests_page(global_db),
                    "image": lambda x: self.give_image(x),
                    "testlist":  lambda x: altrenative_reports_tests.testlist(global_db, x),
                }[chooser](os.path.basename(self.path.replace("%20", " ")))
                if chooser in listed:
                    # store generated html into our list for later use.
                    # compress it here, first time access for page will not be sent out as compressed
                    global_db.served_htmls_dict[os.path.basename(self.path.replace("%20", " "))] = gzip.compress(bytes(return_html, 'utf-8'))
            except Exception as e:
                print(e)
                traceback.print_exc()
                self.send_error(404, 'File Not Found: %s' % self.path)
                return

        self.send_response(response_code)
        # Send headers, we serve out only two type of content out from here.
        if isinstance(return_html, bytes):
            self.send_header('Content-type','image/jpeg')
            self.end_headers()
            self.wfile.write(return_html)
        else:
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(bytes(return_html, "utf8"))
            
        return

class dbclass:
    ##
    ## this dict contain cached html pages.
    ## here pages are stored in gzipped format.
    served_htmls_dict = {}

    def __env_add_result__(self, db, human_envs, report, commit, result):
        if result.test.full_name not in human_envs:
            for run in result.runs:
                envfile = run.env_file
                if envfile is not None:
                    fullpath = report.log_folder + "/" + envfile
                    human_envs[result.test.full_name] = EnvDumpReport(fullpath, True)
        if result.test.full_name not in db['env_sets']:
            db['env_sets'][result.test.full_name] = list()
        for e in range(0, len(result.runs)):
            # Create the per-run information
            envfile = result.runs[e].env_file
            if envfile is None:
                continue

            fullpath = report.log_folder + "/" + envfile
            r = EnvDumpReport(fullpath, False).to_set(['^DATE',
                                                        '^ENV.ENV_DUMP_FILE',
                                                        '^ENV.ENV_DUMP_METRIC_FILE',
                                                        '^ENV.EZBENCH_CONF_.*\.key$',
                                                        '_PID',
                                                        'SHA1$',
                                                        '.pid$',
                                                        'X\'s pid$',
                                                        'extension count$',
                                                        'window id$'])
            tup = dict()
            tup['log_folder'] = report.name
            tup['commit'] = commit
            tup['run'] = e

            # Compare the set to existing ones
            found = False
            for r_set in db['env_sets'][result.test.full_name]:
                if r  == r_set['set']:
                    r_set['users'].append(tup)
                    found = True

            # Add the report
            if not found:
                new_entry = dict()
                new_entry['set'] = r
                new_entry['users'] = [tup]
                db['env_sets'][result.test.full_name].append(new_entry)


    def __init__(self, reports, output, output_unit = None, title = None,
			   commit_url = None, verbose = False, reference_report = None,
			   reference_commit = None, embed = False):
        # select the right unit
        if output_unit is None:
            self.output_unit = "FPS"
        else:
            self.output_unit = output_unit

        # Parse the results and then create one report with the following structure:
        # commit -> report_name -> test -> bench results
        self.db = dict()
        self.db["commits"] = collections.OrderedDict()
        self.db["reports"] = list()
        self.db["events"] = dict()
        self.db["tests"] = list()
        self.db["metrics"] = dict()
        self.db['env_sets'] = dict()
        self.db["envs"] = dict()
        self.db["targets"] = dict()
        self.db["targets_raw"] = dict()
        self.db["target_result"] = dict()
        self.human_envs = dict()

        if reference_report is None and reference_commit is not None:
            reference_report = reports[0]

        # set all the targets
        if reference_report is not None and len(reference_report.commits) > 0:
            if reference_commit is not None:
                ref_commit = reference_report.find_commit_by_id(reference_commit)
            else:
                ref_commit = reference_report.commits[-1]

            self.db['reference_name'] = "{} ({})".format(reference_report.name, ref_commit.label)
            self.db['reference'] = reference_report
            for result in ref_commit.results.values():
                average_raw = result.result().mean()
                average = convert_unit(average_raw, result.unit, self.output_unit)
                average = float("{0:.2f}".format(average))
                average_raw = float("{0:.2f}".format(average_raw))
                if (not result.test.full_name in db["targets"] or
                    self.db["targets"][result.test.full_name] == 0):
                        self.db["targets"][result.test.full_name] = average
                        self.db["targets_raw"][result.test.full_name] = average_raw
                        self.db["target_result"][result.test.full_name] = result

                self.__env_add_result__(self.db, self.human_envs, reference_report, ref_commit, result)

        for report in reports:
            report.events = [e for e in report.events if not isinstance(e, EventResultNeedsMoreRuns)]

        self.db["events"] = Report.event_tree(reports)

        for report in reports:
            self.db["reports"].append(report)

            # make sure all the tests are listed in db["envs"]
            for test in report.tests:
                self.db["envs"][test.full_name] = dict()

            for event in report.events:
                if type(event) is EventPerfChange:
                    for result in event.commit_range.new.results.values():
                        if result.test.full_name != event.test.full_name:
                            continue
                        result.annotation = str(event)

            # add all the commits
            for commit in report.commits:
                if len(commit.results) == 0 and not hasattr(commit, 'annotation'):
                    continue

                if not commit.label in self.db["commits"]:
                    self.db["commits"][commit.label] = dict()
                    self.db["commits"][commit.label]['reports'] = dict()
                    self.db["commits"][commit.label]['commit'] = commit
                    if not commit.build_broken():
                        self.db["commits"][commit.label]['build_color'] = "#00FF00"
                    else:
                        self.db["commits"][commit.label]['build_color'] = "#FF0000"
                    self.db["commits"][commit.label]['build_error'] = str(commit.compil_exit_code).split('.')[1]
                self.db["commits"][commit.label]['reports'][report.name] = dict()

                # Add the results and perform some stats
                score_sum = 0
                count = 0
                for result in commit.results.values():
                    if not result.test.full_name in self.db["tests"]:
                        self.db["tests"].append(result.test.full_name)
                        self.db["metrics"][result.test.full_name] = []
                    self.db["commits"][commit.label]['reports'][report.name][result.test.full_name] = result
                    average_raw = result.result().mean()
                    if average_raw is not None and result.unit is not None:
                        average = convert_unit(average_raw, result.unit, self.output_unit)
                    else:
                        average_raw = 0
                        average = 0
                        result.unit = "unknown"
                    score_sum += average
                    count += 1

                    result.average_raw = float("{0:.2f}".format(average_raw))
                    result.average = float("{0:.2f}".format(average))
                    result.margin_str = float("{0:.2f}".format(result.result().margin() * 100))

                    # Compare to the target
                    if (not result.test.full_name in self.db["targets"] or
                    (self.db["targets"][result.test.full_name] == 0 and 'reference_name' not in self.db)):
                        self.db["targets"][result.test.full_name] = result.average
                        self.db["targets_raw"][result.test.full_name] = result.average_raw
                    result.diff_target = compute_perf_difference(self.output_unit,
                                                                 self.db["targets"][result.test.full_name],
                                                                 result.average)

                    # Get the metrics
                    result.metrics = dict()
                    for metric in result.results(BenchSubTestType.METRIC):
                        if metric not in self.db["metrics"][result.test.full_name]:
                            self.db["metrics"][result.test.full_name].append(metric)

                        result.metrics[metric] = result.result(metric)


                    # Environment
                    self.__env_add_result__(self.db, self.human_envs, report, commit, result)

                if count > 0:
                    avg = score_sum / count
                else:
                    avg = 0
                self.db["commits"][commit.label]['reports'][report.name]["average"] = float("{0:.2f}".format(avg))
                self.db["commits"][commit.label]['reports'][report.name]["average_unit"] = self.output_unit

        # Generate the environment
        for bench in self.human_envs:
            env = self.human_envs[bench]
            if env is not None:
                for key in sorted(list(env.values)):
                    if not bench in self.db['envs']:
                        continue
                    cur = self.db['envs'][bench]
                    fields = key.split(":")
                    for f in range(0, len(fields)):
                        field = fields[f].strip()
                        if f < len(fields) - 1:
                            if field not in cur:
                                cur[field] = dict()
                            cur = cur[field]
                        else:
                            cur[field] = env.values[key]

        # Generate the environment diffs
        self.db['env_diff_keys'] = dict()
        for bench in self.db['env_sets']:
            final_union = set()
            for report in self.db['env_sets'][bench]:
                diff = self.db['env_sets'][bench][0]['set'] ^ report['set']
                final_union = final_union | diff
            self.db['env_diff_keys'][bench] = sorted(dict(final_union).keys())

        # Sort the tests by name to avoid ever-changing layouts
        self.db["tests"] = np.sort(self.db["tests"])

        # Support creating new URLs
        if commit_url is not None:
            self.db["commit_url"] = commit_url


def gen_report(log_folder, restrict_commits):
    report_name = os.path.basename(os.path.abspath(log_folder))

    try:
        sbench = SmartEzbench(ezbench_dir, report_name, readonly=True)
        report = sbench.report(restrict_to_commits = restrict_commits, silentMode=False)
    except RuntimeError:
        report = Report(log_folder, restrict_to_commits = restrict_commits)
        report.enhance_report(NoRepo(log_folder))

    return report

def gen_mainHTML(dbcontainer,  title):
    html = None
	# Check that we have commits
    if len(dbcontainer.db["commits"]) == 0 and verbose:
        print("No commits were found, cancelling...")
    else:
        # Create the html file
        if title is None:
            report_names = [r.name for r in reports]
            title = "Performance report on the runs named '{run_name}'".format(run_name=report_names)

        html = htmlReportMain.stubSource

    return html

"""
start everything:
"""

if __name__ == "__main__":
#    global global_db
#    global global_html

    # parse the options
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", help="Set the title for the report")
    parser.add_argument("--unit", help="Set the output unit (Default: FPS)")
    parser.add_argument("--output", help="Report html file path")
    parser.add_argument("--commit_url", help="HTTP URL pattern, {commit} contains the SHA1")
    parser.add_argument("--quiet", help="Be quiet when generating the report", action="store_true")
    parser.add_argument("--reference", help="Compare the test results to this reference report")
    parser.add_argument("--reference_commit", help="Compare the test results to the specified commit of the reference report")
    parser.add_argument("--restrict_commits", help="Restrict commits to this list (space separated)")
    parser.add_argument("-p", "--port", type=int, help="Server port.")
    parser.add_argument("log_folder", nargs='+')
    args = parser.parse_args()

    # Set the output folder if not set
    if args.output is None:
        if len(args.log_folder) == 1:
            global_log_folder = args.log_folder[0]
            args.output = "{}/index.html".format(args.log_folder[0])
        else:
            print("Error: The output html file has to be specified when comparing multiple reports!")
            sys.exit(1)

    # Restrict the report to this list of commits
    restrict_commits = []
    if args.restrict_commits is not None:
        restrict_commits = args.restrict_commits.split(' ')

    reports = []
    for log_folder in set(args.log_folder):
        reports.append(gen_report(log_folder, restrict_commits))

    # Reference report
    reference = None
    if args.reference is not None:
        reference = gen_report(args.reference, [])

    global_db = dbclass(reports, args.output, args.unit, args.title,
			   args.commit_url, not args.quiet, reference, args.reference_commit)

    global_html = gen_mainHTML(global_db,  args.title)
    
    try:
        server_port = int(args.port)
    except:
        server_port = 8000

    server_address = ('0.0.0.0', server_port)
    print("serving at", server_address )

    httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    print("closing server")
    httpd.server_close()
