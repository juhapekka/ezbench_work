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
import htmlReportMain
import argparse
import re
import traceback
import html
import difflib

# Import ezbench from the utils/ folder
ezbench_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(ezbench_dir, 'python-modules'))
sys.path.append(ezbench_dir)

from utils.env_dump.env_dump_parser import *
from ezbench.smartezbench import *
from ezbench.report import *

from http.server import BaseHTTPRequestHandler, HTTPServer

global_db = None
global_html = None
global_log_folder = None

class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    served_htmls_dict = {}
    #######################
    ## all tests page
    #######################
    def test_result(self, testname):
        returnstr = ""

        unit_results = []
        stats_status = dict()
        statuses = set()

        target_changes = dict()
        changes = set()

        # Add the target report in the list of reports if it
        # contains tests for this test
        target_result = None
        if 'target_result' in global_db.db and testname in global_db.db['target_result']:
            subtests = global_db.db['target_result'][testname].results(BenchSubTestType.SUBTEST_STRING)
            if len(subtests) > 0:
                target_result = global_db.db['target_result'][testname]
                target_result.name = "Target"
                stats_status[target_result.name] = dict()
                unit_results.append(target_result)

        for report in global_db.db['reports']:
            for commit in report.commits:
                for result in commit.results.values():
                    if result.test.full_name != testname:
                        continue
                    if result.test_type != "unit":
                        continue
                    result.name = "{}.{}".format(report.name, commit.label)
                    stats_status[result.name] = dict()
                    target_changes[result.name] = dict()
                    unit_results.append(result)

        all_tests = set()
        for result in unit_results:
            all_tests |= set(result.results(BenchSubTestType.SUBTEST_STRING))
            result.unit_results = dict()

        unit_tests = set()
        for test in all_tests:
            value = None
            for result in unit_results:
                if "<" in test: # Hide subsubtests
                    continue
                subtest = result.result(test)
                if subtest is None or len(subtest) == 0:
                    status = "missing"
                else:
                    if len(subtest.to_set()) == 1:
                        status = subtest[0]
                    else:
                        status = "unstable"
                result.unit_results[test] = status

                # Collect stats on all the status
                if status not in stats_status[result.name]:
                    stats_status[result.name][status] = 0
                    statuses |= set([status])
                stats_status[result.name][status] += 1

                if value == None and status != "missing":
                    value = status
                    continue
                if value != status and status != "missing":
                    unit_tests |= set([test])

                if (target_result is None or result == target_result or
                    target_result.unit_results[test] == status):
                    continue

                change = "{} -> {}".format(target_result.unit_results[test],
                                           status)
                if change not in target_changes[result.name]:
                    target_changes[result.name][change] = 0
                    changes |= set([change])
                target_changes[result.name][change] += 1

        all_tests = []

        if len(unit_results) > 0:
            returnstr += "<h4>Unit tests</h4>"
            returnstr += "<h5>Basic stats</h5>"
            returnstr += "<table style=\"font-family:arial;font-size: 8pt;border-collapse: collapse;\">"
            returnstr += "<tr style=\"border: 1px solid black\"><th>Version</th>"

            for status in sorted(statuses):
                returnstr += "<th style=\"border: 1px solid black\">{}</th>".format(status)
            returnstr += "</tr>"

            for result in stats_status:
                returnstr += "<tr style=\"border: 1px solid black\"><td style=\"border: 1px solid black\">{}</td>".format(result)
                for status in sorted(statuses):
                    if status in stats_status[result]:
                        returnstr += "<td style=\"border: 1px solid black\">{}</td>".format(stats_status[result][status])
                    else:
                        returnstr += "<td style=\"border: 1px solid black\">0</td>"
                returnstr += "</tr>"
            returnstr += "</table>"

            if 'target_result' in global_db.db and testname in global_db.db['target_result']:
                returnstr += "<h5>Status changes</h5>"
                returnstr += "<table style=\"font-family:arial;font-size: 8pt;border-collapse: collapse;\">"
                returnstr += "<tr><th>Version</th>"

                for result in target_changes:
                    returnstr += "<th>{}</th>".format(result)

                returnstr += "</tr>"

                for change in sorted(changes):
                    returnstr += "<tr style=\"border: 1px solid black\"><td style=\"border: 1px solid black\">{}</td>".format(change)
                    for result in target_changes:
                        if change in target_changes[result]:
                            returnstr += "<td style=\"border: 1px solid black\">{}</td>".format(target_changes[result][change])
                        else:
                            returnstr += "<td style=\"border: 1px solid black\">0</td>"
                    returnstr += "</tr>"
                returnstr += "</table>"

                returnstr += "<h5>Changes</h5>"
                returnstr += "<div style='overflow:auto; width:100%;max-height:1000px;'>"
                returnstr += "<table style=\"font-family:arial;font-size: 8pt;border-collapse: collapse;\">"
                returnstr += "<tr style=\"border: 1px solid black\"><th style=\"border: 1px solid black\">test name ({})</th>".format(len(unit_tests))

                for result in unit_results:
                    returnstr += "<th style=\"border: 1px solid black\">{}</th>".format(result.name)
                returnstr += "</tr>"

                for test in sorted(unit_tests):
                    returnstr += "<tr style=\"border: 1px solid black\"><td style=\"border: 1px solid black\">{}</td>", format(html.escape(test))
                    for result in unit_results:
                        returnstr += "<td style=\"border: 1px solid black\">{}</td>".format(result.unit_results[test])
                    returnstr += "</tr>"
                returnstr += "</table>"
                returnstr += "</div>"
        return returnstr

    def env_detail(self, testname):
        returnstr = """
        <div class="row"">
            <input id="togList{}" type="checkbox">
            <label for="togList{}">
                <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>+</b>Expand Environment detail:</span>
                <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>-</b>Collapse Environment detail:</span>
            </label>
            <div class="list">
            <ul>
            <table style="font-family:arial;font-size: 8pt;border-collapse: collapse;">
"""

        returnstr = returnstr.format(testname,  testname)
        returnstr += "\n            <tr style=\"border: 1px solid black\">"
        returnstr += "\n            <th style=\"border: 1px solid black\">Key</th>"

        for env_set in  global_db.db["env_sets"][testname]:
            users = ""
            for user in env_set['users']:
                if len(users) > 0:
                    users += "<br/>"
                users += "{}.{}#{}".format(user['log_folder'], user['commit'].label, user['run'])
            returnstr += "\n            <th style=\"border: 1px solid black\">{}</th>".format(users)

        for key in global_db.db["env_diff_keys"][testname]:
            returnstr += "\n            <tr style=\"border: 1px solid black\">"
            returnstr += "\n                <td style=\"border: 1px solid black\">{}</td>".format(key)
            prev = None
            for env_set in global_db.db["env_sets"][testname]:
                if key in dict(env_set['set']):
                    env_val = dict(env_set['set'])[key]
                else:
                    env_val = "MISSING"
                if prev is None or env_val != prev:
                    css_class = "background:#FFCCCC;border: 1px solid black"
                else:
                    css_class = "background:#EEEEEE;border: 1px solid black"
                prev = env_val
                returnstr += "\n                <td style=\"{}\">{}</td>".format(css_class, env_val)
            returnstr += "\n            </tr>"

        returnstr += """
            </table>
            </ul>
            </div>
        </div>
"""
        return returnstr

    def onetest(self, testname):
        returnStr = "       <h2>{}</h2><br>".format(testname)

        for key in global_db.db["envs"][testname].keys():
            returnStr += "       <h4>{}</h4><br>".format(key)
            for i in sorted(global_db.db["envs"][testname][key]):
                returnStr += "{}  ".format(i)

        returnStr += self.env_detail(testname)
        returnStr += self.test_result(testname)
        return returnStr

    def testlist(self, testlist):
        return_stringi = """    <div class=\"output\" id="testsmainsdiv">
"""
        return_stringi_footer = """    </div>
"""

        newlist = re.split('\?', testlist)
        newlist.remove("testlist_")
        newlist.remove(".html")
        print(newlist)
        outputdiv = ""
        for test in newlist:
            outputdiv += self.onetest(test)

        return return_stringi+outputdiv+return_stringi_footer


    def tests_page(self):
        return_stringi = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <style type="text/css">
        body {
            height:auto;
            width:100vw;
            max-height:100vh;
            overflow: scroll;
        }

        dummy { padding-left: 4em; }
        tab1 { margin-left: 2em; }
        tab2 { margin-left: 10%; position:inherit }
        tab3 { margin-left: 20%; position:inherit }

        .selections {
            border-radius: 8px;
            background: #EEEEEE;
            width: 20vw;
            padding: 10px;
            border: 2px solid #FFFFFF;
        }

        .output {
            display:table;
            height: auto;
            overflow: scroll;
            border-radius: 8px;
            background: #EEEEEE;
            padding: 10px;
            border: 2px solid #FFFFFF;

            position: absolute;
            top: 8px;
            left: calc(20vw + 32px);
            width: calc(80vw - 64px);
        }

        [id^="togList"],
        [id^="togList"] ~ .list,
        [id^="togList"] + label  span + span,
        [id^="togList"]:checked + label span{ display:none; }
        [id^="togList"]:checked + label span + span{ display:inline-block; }
        [id^="togList"]:checked ~ .list{ display:block; }
    </style>
</head>
<body>
"""
        return_stringi_footer = """    </div>
</body>
<script type="text/javascript">
    var elements = [{}];
    function checkClick(parameetteri) {{
        var testlist = ""
        for (var c = 0; c < elements.length; c++) {{
            if (document.getElementById(elements[c]).checked == true) {{
                testlist += "?" + elements[c];
            }}
        }}

        var elem = document.getElementById("testsmainsdiv");
        if(elem != null) {{
            elem.parentNode.removeChild(elem);
        }}

        var client = new XMLHttpRequest();
        var ll = "testlist_"+testlist+"?.html"
        client.open('GET', ll);
        client.onreadystatechange = function() {{
            if (this.readyState === 4 && this.status === 200) {{
                document.getElementById("testsoutput").insertAdjacentHTML('afterbegin', client.responseText);
            }}
        }}
        client.send();
    }}
</script>
</html>"""

#        reportsdiv = "<div class=\"selections\">"
#        for report in global_db.db["reports"]:
#            reportsdiv += "<input type=\"checkbox\" id=\"{}\" onClick=\"checkClick(\'{}\')\" checked>{}</input>".format(str(report.name), str(report.name), str(report.name))
#            reportsdiv += "<br>"
#        reportsdiv += "</div>"

        testssdiv = "<div id=\"selections\"class=\"selections\">"
        commachar = ""
        elements = ""
        for test in global_db.db["tests"]:
            testssdiv += "<input type=\"checkbox\" id=\"{}\" onClick=\"checkClick(\'{}\')\">{}</input>".format(test, test, test)
            testssdiv += "<br>"
            elements += "{}\"{}\"".format(commachar,  test)
            commachar = ", "
        testssdiv += "</div>"

        outputdiv = "<div id=\"testsoutput\"></div>"
        return return_stringi+testssdiv+outputdiv+return_stringi_footer.format(elements)

    #######################
    ## trend page
    #######################
    def test_color_code(self,  testname):
        return int(sum(bytearray(testname, 'ascii'))*12345.12345%0xffffff)

    def one_test(self,  testname):
        return "\n\t\t\t\t<input type=\"checkbox\" onClick=\"checkClick()\" " \
            "id=\"{}\" checked><span style=\"color:#{:06X};\">&#9608;</span>" \
            " {} <br>".format(testname, self.test_color_code(testname), \
            testname)

    def decorate_trendgroup(self,  testname, group, elementindexes):
        return "\n\t\t<div style=\"display: inline-block; width: 32vw\">" \
            "\n\t\t\t<fieldset><legend><input type=\"checkbox\" id=\"{}\" " \
            "onClick=\"checkClick(\'{}\', {})\" checked>{}</input></legend>{}" \
            "\n\t\t\t</fieldset>\n\t\t</div>".format(testname, testname, \
            elementindexes, testname, group)

    def trend_page(self, eventpath):
        return_stringi = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <style type="text/css">
        body {
            height:auto;
            width:100vw;
            max-height:100vh;
            overflow-x: hidden;
            overflow-y: scroll;
        }

        dummy { padding-left: 4em; }
        tab1 { margin-left: 2em; }
        tab2 { margin-left: 10%; position:inherit }
        tab3 { margin-left: 20%; position:inherit }

        .trenddiv {
            display: inline-block;
            overflow-y: hidden;
            overflow-x: hidden;
            height: 45vh;
            width: 97%;
            border: 0px;
            z-index: 100;
        }

        fieldset {
            -webkit-border-radius: 8px;
            -moz-border-radius: 8px;
            border-radius: 8px;
        }

        legend {
            background: #FF9;
            border: solid 1px black;
            -webkit-border-radius: 8px;
            -moz-border-radius: 8px;
            border-radius: 8px;
            padding: 6px;
        }
            </style>
</head>
<body>
    <div id="trends" class="trenddiv"></div>
"""
        return_stringi_footer = """
<script type="text/javascript">
    parent.parent.google.charts.setOnLoadCallback(drawLineColors);

    var data;
    var chart;

    function drawLineColors() {{
{}

        var Options = {{
            legend: 'none',
            hAxis: {{ textPosition: 'in' }},
            vAxis: {{ title: '% of target', textPosition: 'in' }},
            chartArea: {{ left: "5%", right: "2%", bottom: "1%", top: "1%" }},
            pointSize: 7,
            dataOpacity: 0.3,
            interpolateNulls: 'true',
            series: {{{}
            }}
        }};
    
        chart = new parent.parent.google.visualization.LineChart(document.getElementById('trends'));
        chart.draw(data, Options);
    }}
    function checkClick() {{
        var elements = [{}];

        var lOptions = {{
            legend: 'none',
            hAxis: {{ textPosition: 'in' }},
            vAxis: {{ title: '% of target', textPosition: 'in' }},
            chartArea: {{ left: "5%", right: "2%", bottom: "1%", top: "1%" }},
            pointSize: 7,
            dataOpacity: 0.3,
            interpolateNulls: 'true',
            series: {{{}
            }}
        }};

        if (arguments.length > 0) {{
            var chk = document.getElementById(arguments[0]).checked;
            for (var i = 1; i < arguments.length; i++ ) {{
                document.getElementById(elements[arguments[i]]).checked = chk;
            }}
        }}

        var view = new parent.parent.google.visualization.DataView(data);
        for (var c = 0, c2 = 0; c < elements.length; c++, c2++) {{
            if (document.getElementById(elements[c]).checked == false) {{
                    view.hideColumns([1+c*2]);
                    view.hideColumns([2+c*2]);
                    c2--;
            }}
            else {{
                lOptions.series[c2] = lOptions.series[c];
            }}
        }}
        chart.draw(view, lOptions);
    }}
    </script>
</body>
</html>"""

        commits = global_db.db["commits"]
        commitlist = list()

        # create list with all commit dates/times
        for single in commits:
            commitlist.append(commits[single]["commit"].commit_date)

        commitlist.sort()

        report = global_db.db["reports"][0].name
        testDict = {}
        for test in global_db.db["tests"]:
            #dictionary of tuples, [test] = (date, result)
            testDict[test] = []

            for commit in global_db.db["commits"]:
                if test in global_db.db["commits"][commit]["reports"][report]:
                    result = global_db.db["commits"][commit]["reports"][report][test]
                    testDict[test].append((result.commit.commit_date, \
                    result.diff_target ))

        googleArrayData =  "\t\tdata = parent.parent.google.visualization.arrayToDataTable ([['DateTime', "
        commachar = ""
        prevResultDict = {}
        for key in testDict:
            prevResultDict[key] = "null"

        colorlist = ""
        onetimers = ["", ""]
        grouppingString = ["", ""]
        singleString = [0,  ""]
        elementlist = ""
        counter = 0
        for test in sorted(testDict.keys()):
            # elementlist is javascript var elements, list to check for checkmarks
            elementlist += "{}\"{}\"".format(commachar,  test)
            googleArrayData += "{}'{}', {{'type': 'string', 'role': 'style'}}".format(commachar, test)
            # color list actually is list of the series. if new fields needed per series add them to format line below.
            colorlist += "{}\n\t\t\t\t{}: {{ lineDashStyle: [1,0], color: '#{:06X}'}}".format(commachar,  counter, self.test_color_code(test) )

            splitted = test.split(':', 1)

            if singleString[0] == 0:
                singleString[1] = splitted[0]
                singleString[0] += 1
                grouppingString[0] += self.one_test(test)
                grouppingString[1] += "{}".format(str(counter))
            else:
                if singleString[1] == splitted[0]:
                    singleString[0] += 1
                    grouppingString[0] += self.one_test(test)
                    grouppingString[1] += ", {}".format(str(counter))
                else:
                    if singleString[0] is 1:
                        onetimers[0] += grouppingString[0]
                        if len(onetimers[1]) > 0:
                            onetimers[1] += ", "
                        onetimers[1] += grouppingString[1]
                        grouppingString[0] = self.one_test(test)
                        grouppingString[1] = "{}".format(str(counter))
                        singleString = [1,  splitted[0]]
                    else:
                        return_stringi += self.decorate_trendgroup(singleString[1], grouppingString[0],  grouppingString[1])
                        grouppingString = ["", ""]
                        singleString = [1,  splitted[0]]
                        grouppingString[0] += self.one_test(test)
                        grouppingString[1] += "{}".format(str(counter))

            commachar = ", "
            counter += 1

        googleArrayData += "],\n"

        if singleString[0] == 1:
            onetimers[0] += grouppingString[0]
            onetimers[1] += ", {}".format(grouppingString[1])
        else:
            return_stringi += self.decorate_trendgroup(singleString[1], grouppingString[0], grouppingString[1])

        return_stringi += self.decorate_trendgroup("Single Tests",  onetimers[0],  onetimers[1])

        indicecomma = ""
        for item in commitlist:
            googleArrayData += "{}\t\t\t[{}, ".format(indicecomma, item.strftime('new Date(%Y, %m, %d, %H, %M, %S)'))
            commachar = ""
            extrastr = "null"
            for test in sorted(testDict.keys()):
                res2 = "'line { stroke-width: 1;}'"
                res = "null"
                for i in testDict[test]:
                    if i[0] == item:
                        res = str(i[1])
                        extrastr = prevResultDict[test]
                        res2 = "null"
                        break
                googleArrayData += "{}{}, {}".format(commachar,  str(res), extrastr)
                prevResultDict[test] = res2
                commachar = ", "
            googleArrayData += "]"
            indicecomma = ",\n"
        googleArrayData += "]);"

        return_stringi += "\n\t</div>"
        return_stringi += return_stringi_footer.format(googleArrayData, colorlist, elementlist, colorlist)
        return return_stringi

    #######################
    ## single event page
    #######################
    def diff_html_higlight(self,  str1,  str2,  rInclude="insert delete"):
        seqm = difflib.SequenceMatcher(None, str1, str2)
        output= []
        for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
            if opcode == 'equal':
                output.append(seqm.a[a0:a1])
            elif opcode == 'insert':
                if "insert" in rInclude:
                    output.append("<span style=\"color:#00AA00;\">" + seqm.b[b0:b1] + "</span>")
            elif opcode == 'delete':
                if "delete" in rInclude:
                    output.append("<span style=\"color:#FF0000;\">" + seqm.a[a0:a1] + "</span>")
            elif opcode == 'replace':
                if "delete" in rInclude:
                    output.append("<span style=\"color:#FF0000;\">" + seqm.a[a0:a1] + "</span>")
                elif "insert" in rInclude:
                    output.append("<span style=\"color:#00AA00;\">" + seqm.b[b0:b1] + "</span>")
            else:
                raise(RuntimeError, "unexpected opcode")
        return ''.join(output)

    def event_result(self, eventpath):
        return_string = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">




    <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <style type="text/css">
        body {
            height:auto;
            width:100vw;
            overflow-x: hidden;

            overflow-y: scroll;
            background-color:#fcfccf
        }
        button.link { background:none;border:none;width:100%; }
        dummy { padding-left: 4em; }
        tab1 { margin-left: 2em; }
        tab2 { margin-left: 10%; position:inherit }
        tab3 { margin-left: 20%; position:inherit }
        
        .events {
            display: inline-block;
            height:auto;
            width:99%;
            border: 0px;
        }
        .normalparagraph {
            font-family:'Courier New';
        }
        
        .testparagraph {
            font-family:'Courier New';
            margin-left: 2em;
        }

        .testonelinerparagraph {
            margin-left: 2em;
            font-family:'Courier New';
            height: auto;
            width: auto;
        }
        
        
        .testonelinerparagraph:hover .tooltipchart {
            visibility: visible;
            display: inline-block;
            max-height:300px;
            max-widtht:450px;
            height: 300px;
            width: 450px;
            container: 'body';
            z-index: 500;
            opacity: 1;
        }
        .testonelinerparagraph:hover:after .tooltipchart {
            opacity: 1;
        }


        .testonelinerparagraph:after{
            opacity: 0;
            -webkit-transition: opacity .25s ease-in-out;
            -moz-transition: opacity .25s ease-in-out;
            transition: opacity .25s ease-in-out;
        }

        .testonelinerparagraph .tooltipchart {
            container: 'body';
            visibility: hidden;
            max-height:300px;
            max-widtht:450px;
            height: 300px;
            width: 450px;
            background-color: black;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 5px 10px;

            position: fixed;
            display: block;
            right: 0;
            bottom: 6px;
            opacity: 0;
            transition: all .25s ease-out;

            z-index: 500;
        }

        [id^="togList"],
        [id^="togList"] ~ .list,
        [id^="togList"] + label  span + span,
        [id^="togList"]:checked + label span{ display:none; }
        [id^="togList"]:checked + label span + span{ display:inline-block; }
        [id^="togList"]:checked ~ .list{ display:block; }
        </style>
        </head>
        <body>
        """

        return_string_footer = """
        </body>
        <script type="text/javascript">
            parent.parent.google.charts.setOnLoadCallback(drawchart);

            function datesort(elem1, elem2)
            {
                if (elem1[0] > elem2[0]) return 1;
                if (elem1[0] < elem2[0]) return -1;
                return 0;                
            }

            function drawchart()
            {
                var chart;
                var data;
                var originaldata;

                var options = {
                    hAxis: { title: '\% of target', textPosition: 'in' },
                    vAxis: { textPosition: 'in' },
                    chartArea: { left: 0, right: 0, top: 0, bottom: 0 },
                    axisTitlesPosition: 'in',
                    pointSize: 7,
                    dataOpacity: 0.3,
                    colors: ['#a52714'],
                    series: {
                        0:{visibleInLegend: false},
                    }
                };
"""

        graph_builder = """
                data = new parent.parent.google.visualization.DataTable();
                data.addColumn('datetime', 'X');
                data.addColumn('number', '\% of target');

                originaldata = [{}];
                originaldata.sort(datesort);                
                data.addRows(originaldata);

                chart = new parent.parent.google.visualization.LineChart(document.getElementById("{}"));
                chart.draw(data, options);"""

        graph_builder_finish = """
            }            
        </script>
</html>
"""
        tableformat = """            <input id="togList{}" type="checkbox">
            <label for="togList{}">
                <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>+</b>Expand Environment changes:</span>
                <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>-</b>Collapse Environment changes:</span>
            </label>
            <div class="list">
            <ul>
            <table style="font-family:arial;font-size: 8pt;border-collapse: collapse;">"""

        arrivals = re.split("[ _.]+",  eventpath)
        if arrivals[0] == "result":
            event_finder = arrivals[1]
        else:
            return_string += "<h1>Unecpected error, unknown event!</h1></body>"
            return str(return_string)

        events = global_db.db["events"]
        interesting_event = None
        for current_event in events:
            if event_finder in str(current_event):
                interesting_event = current_event
                break
        
        if interesting_event == None:
            return_string += "<h1>Unecpected error, unknown event!</h1></body>"
            return str(return_string)
        ##
        # got the event, start making the html report
        #
        return_string += "<h1>{} <a href=\"{}\" onclick=\"window.open('{}', '{}')\";>&#10697;</a></h1>\n".format(str(interesting_event), eventpath, eventpath, str(interesting_event))

        subentries = "\n\t\t\t<ul class=\"normalparagraph\">\n"

        report = global_db.db["reports"][0].name

        testdict = {}
        for test in events[interesting_event]:
            teststring = ""
            assstring = ""

            # this for-loop build dictionary of results to show in popup graph.
            for testname in events[interesting_event][test]:
                if test == "perf":
                    for commit in global_db.db["commits"]:
                        if testname in global_db.db["commits"][commit]["reports"][report]:
                            result = global_db.db["commits"][commit]["reports"][report][str(testname)]
                            if re.sub('[^0-9a-zA-Z]+', '_', testname) not in testdict:
                                testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)] = ["[{}, {}]".format(str(result.commit.commit_date.strftime('new Date(%Y, %m, %d, %H, %M, %S)')),  str(result.diff_target))]
                            else:
                                lista = testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)]
                                lista.append("[{}, {}]".format(str(result.commit.commit_date.strftime('new Date(%Y, %m, %d, %H, %M, %S)')),  str(result.diff_target)))
                                testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)] = lista

                if len(teststring) > 0:
                    assstring = "s"
                    teststring += ", "

                teststring += str(testname)

            subentries += "\t\t\t\t<li><b>{} {} test{}</b> {}</li>\n".format(test,  len(events[interesting_event][test]), assstring, teststring)
        subentries += "\t\t\t</ul>"
        
        for key in testdict:
            datestr = ""
            commastr = ""
            lista = testdict[key]
            for item in lista:
                datestr = datestr+commastr
                commastr = ", "
                datestr = datestr+item
            
            return_string_footer = return_string_footer+graph_builder.format(datestr, key)
        return_string_footer = return_string_footer+graph_builder_finish

        return_string += "\t\t<p class=\"normalparagraph\">{}</p>\n".format(subentries)

        for test in events[interesting_event]:
            return_string += "\t\t\t<h2>{}</h2>\n".format(str(test))
            for testname in events[interesting_event][test]:
                return_string += "\t\t\t\t<h4>{}</h4>\n".format(str(testname))
####################################
                temp_return_string = tableformat.format(testname,  testname)
                temp_return_string += "\n            <tr style=\"border: 1px solid black\">"
                temp_return_string += "\n            <th style=\"border: 1px solid black\">Key</th>"
                change_counter = 0

                try:
                    for env_set in global_db.db["env_sets"][testname]:
                        users = ""
                        for user in env_set['users']:
                            if user['commit'].label == interesting_event.old.label or user['commit'].label == interesting_event.new.label:
                                if len(users) > 0:
                                    users += "<br/>"

                                users += "{}.{}#{}".format(user['log_folder'], user['commit'].label, user['run'])
                                temp_return_string += "\n            <th style=\"border: 1px solid black\">{}</th>".format(users)

                    for key in global_db.db["env_diff_keys"][testname]:
                        temp_return_string2 = "\n            <tr style=\"border: 1px solid black\">"
                        temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(key)
                        temp_vals = []
                        for env_set in global_db.db["env_sets"][testname]:
                            for user in env_set['users']:
                                if user['commit'].label == interesting_event.old.label or user['commit'].label == interesting_event.new.label:
                                    if key in dict(env_set['set']):
                                        env_val = dict(env_set['set'])[key]
                                    else:
                                        env_val = "MISSING"
                                    temp_vals.append(str(env_val))

                        if len(temp_vals) == 2 and temp_vals[0] != temp_vals[1]:
                            temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(self.diff_html_higlight(temp_vals[0], temp_vals[1], "delete"))
                            temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(self.diff_html_higlight(temp_vals[0], temp_vals[1], "insert"))
                            temp_return_string2 += "\n            </tr>"
                            temp_return_string += temp_return_string2
                            change_counter += 1
                except:
                    pass

                if change_counter > 0:
                    return_string += temp_return_string
                    return_string += """
            </table>
            </ul>
            </div>
        </div>
"""

####################################

                for j in events[interesting_event][test][testname]:

                    for e in events[interesting_event][test][testname][j]:
                        if not isinstance(e, EventRenderingChange):
                            if test == "perf":
                                return_string += "\t\t\t\t\t<div class=\"testonelinerparagraph\">"
                                return_string += html.escape(e.short_desc)
                                return_string += "<span id=\"{}\" class=\"tooltipchart\"></span></div>".format(re.sub('[^0-9a-zA-Z]+', '_', testname))
                            else:
                                return_string += "\t\t\t\t\t<p class=\"testparagraph\">"
                                return_string += html.escape(e.short_desc)
                                return_string += "</p>"
                        else:
                            # Reconstruct image path
                            new = e.result.average_image_file
                            old = new.replace(e.commit_range.new.sha1, e.commit_range.old.sha1)
                            diff = '{}_compare_{}'.format(new, os.path.split(old)[1])

                            new_e = "/image_{}".format(os.path.split(new)[1])
                            old_e = "/image_{}".format(os.path.split(old)[1])
                            diff_e = "/image_{}".format(os.path.split(diff)[1])

                            return_string += "\t\t\t\t\t<p class=\"testparagraph\">"
                            return_string += e.short_desc
                            return_string += "\n"
                            return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'Old image');\">\n".format(old_e, old_e)
                            return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'Diff image');\">\n".format(diff_e, diff_e)
                            return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'New image');\">\n".format(new_e, new_e)
                            return_string += "\t\t\t\t\t</p>"
                        return_string += "\n\t\t\t\t\t<br>\n"

        return_string += return_string_footer
        return str(return_string)

    #######################
    ## events page
    #######################
    def list_events(self):
        pweek = None
        return_stringi = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <style type="text/css">
        body {
            height:auto;
            width:100vw;
            max-height:100vh;
            overflow-x: hidden;
            overflow-y: hidden;
        }
        button.link {
            background:none;
            border:none;
            width:100%;
            border-radius: 0px;
            padding: 0px 0px;
            position: relative;
            font-size: 14pt;
            font-style: normal;
            font-weight: normal;
            color: #000000;
            z-index: 100;
        }
        button.link:hover {background-color:Gainsboro; z-index: 200; }

        button.link:hover .tooltiptext {
            visibility: visible;
            }
        button.link .tooltiptext {
            visibility: hidden;
            width: auto;
            background-color: black;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 5px 10px;

            position: absolute;
            z-index: 1;
        }

        dummy { padding-left: 4em; }
        tab1 { margin-left: 2em; }
        tab2 { margin-left: 10%; position:inherit }
        tab3 { margin-left: 20%; position:inherit }

        .framediv, .resdiv {
            display: inline-block;
            overflow-y: scroll;
            height:auto;
            max-height:50vh;
            width: calc(100% - 8px);
            border: 0px;
            z-index: 100;
        }

        .resdiv { min-height:50vh;  }

        .events {
            display: inline-block;
            height:auto;
            width: calc(100% - 8px);
            border: 0px;
        }
    </style>
    <script type="text/javascript">
        function SetResultDiv(eventid) {
            document.getElementById("result_div").innerHTML='<object class="resdiv" type="text/html" data="result_\'+eventid+\'.html"></object>';
        }
    </script>
</head>
<body>
    <div id="reportti" class="framediv">
"""

        footerstringi = """
        <br>
        </div>
    </div>
    <div id="result_div">
        <object class="framedivs" type="text/html" data=""></object>
    </div>
</body>"""

        labelstringtemplate = """
                <table width="100%">
                <tr>
                    <td width="70%" style="text-align:left">{}
                        <span class="tooltiptext">{}</span></td>
                    <td width="15%" style="text-align:left">{}</td>
                    <td width="15%" style="text-align:left">{}</td>
                </tr>
                </table>"""

        onelinertemplate = """            <button class="link" onclick="SetResultDiv('{}')">{}
            </button>
            <br>
"""

        events = global_db.db["events"]
        workweekcolorswitch = "#f8f8f8"

        #generate clickable links for the event list
        for i in events:
            subentries = ""
            spantext = ""
            for t in events[i]:
                assstring = ""
                if len(subentries) > 0:
                    subentries += ", "
                
                if len(events[i][t]) > 1:
                    assstring = "s"

                subentries += "{} {}{}".format(len(events[i][t]), t,  assstring)

                teststring = ""
                assstring = ""
                dotter = 0
                for j in events[i][t]:
                    if len(teststring) > 0:
                        assstring = "s"
                        teststring += ", "

                    # list only 3 first tests from event into tooltip
                    if dotter > 2:
                        teststring += "..."
                        break

                    teststring += str(j)
                    dotter = dotter +1

                if len(spantext) > 0:
                    spantext += "<br>"

                spantext += "* {} {} test{} {}".format(str(t), len(events[i][t]), assstring, teststring)

            commit_date = i.commit_date()
            if i.is_single_commit() == True:
                labelstring = str(i).split(" ",  1)[1]
            else:
                labelstring = str(i)

            label = labelstringtemplate.format(labelstring,  spantext, subentries, commit_date)

            isocal = commit_date.isocalendar()
            week = "{}-{}".format(isocal[0], isocal[1])
        
            if week != pweek:
                if workweekcolorswitch == "#ffffff":
                    workweekcolorswitch = "#f0f0f0"
                else:
                    workweekcolorswitch = "#ffffff"

                if pweek != None:
                    return_stringi += str('\t\t\t<br>\n\t\t</div>')

                pweek = week
                return_stringi += str('\n\t\t<div class="events" type="text/html" style="background-color:'+workweekcolorswitch + ';"><h4>Week ' + week + '</h4>\n')

            for j in events[i]:
                for test in events[i][j]:
                    oneline = str('')

                    eventidentifier = re.split("[ _()]+",  str(i))
                    if eventidentifier[0] == "commit" and eventidentifier[1] == "range":
                        event_finder = eventidentifier[2]
                    else:
                        event_finder = eventidentifier[0]

                    oneline += onelinertemplate.format(event_finder,  label)

            return_stringi += oneline

        return_stringi += footerstringi
        return return_stringi
        
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
        if os.path.basename(self.path.replace("%20", " ")) in self.served_htmls_dict:
            return_html = self.served_htmls_dict[os.path.basename(self.path.replace("%20", " "))]
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
                    "events.html": lambda x: self.list_events(),
                    "result": lambda x: self.event_result(x),
                    "commits.html": lambda x: "commits!!",
                    "trends.html": lambda x: self.trend_page(x),
                    "detail.html": lambda x: "detail",
                    "tests.html": lambda x: self.tests_page(),
                    "image": lambda x: self.give_image(x),
                    "testlist":  lambda x: self.testlist(x),
                }[chooser](os.path.basename(self.path.replace("%20", " ")))
                if chooser in listed:
                    self.served_htmls_dict[os.path.basename(self.path.replace("%20", " "))] = return_html
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

#        with open(output, 'w') as f:
#            f.write(html)
#            if verbose:
#                print("Output HTML generated at: {}".format(output))


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
