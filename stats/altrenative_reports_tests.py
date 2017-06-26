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

import os
import sys
import re
import html

# Import ezbench from the utils/ folder
ezbench_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(ezbench_dir, 'python-modules'))
sys.path.append(ezbench_dir)

from utils.env_dump.env_dump_parser import *
from ezbench.smartezbench import *
from ezbench.report import *


#######################
## all tests page
#######################
def test_result(global_db,  testname):
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

def env_detail(global_db, testname):
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

    changes = 0
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
            changes += 1
        returnstr += "\n            </tr>"

    returnstr += """
            </table>
            </ul>
            </div>
        </div>
"""
    if changes > 0:
        return returnstr
    else:
        return str("")

def onetest(global_db, testname):
    if str("test_"+testname) in global_db.served_htmls_dict:
        #test_ is special naming for particular tests here.
        return global_db.served_htmls_dict[str("test_"+testname)]

    returnStr = "       <h2>{}</h2><br>".format(testname)

    for key in global_db.db["envs"][testname].keys():
        returnStr += "       <h4>{}</h4><br>".format(key)
        for i in sorted(global_db.db["envs"][testname][key]):
            returnStr += "{}  ".format(i)

    returnStr += env_detail(global_db, testname)
    returnStr += test_result(global_db, testname)
    #test_ is special naming for particular tests here.
    global_db.served_htmls_dict[str("test_"+testname)] = returnStr
    return returnStr

def testlist(global_db, testlist):
    return_stringi = """    <div class=\"output\" id="testsmainsdiv">
"""
    return_stringi_footer = """    </div>
"""

    newlist = re.split('\?', testlist)
    newlist.remove("testlist_")
    newlist.remove(".html")
    outputdiv = ""
    for test in newlist:
        outputdiv += onetest(global_db, test)

    return return_stringi+outputdiv+return_stringi_footer


def tests_page(global_db):
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
