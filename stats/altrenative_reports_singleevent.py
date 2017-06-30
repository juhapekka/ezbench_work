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
import difflib
#import datetime
import html

# Import ezbench from the utils/ folder
ezbench_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(ezbench_dir, 'python-modules'))
sys.path.append(ezbench_dir)

#characters we will not expect to see in test names when they're part of url
singleevent_url_format = str("[\_\ \<\>\@\.\-\%\/\:]")

from utils.env_dump.env_dump_parser import *
from ezbench.smartezbench import *
from ezbench.report import *

def diff_html_higlight(str1,  str2,  rInclude="insert delete"):
    """
    diff_html_higlight(str1 to compare, str2 to compare, <optional> "insert" or "delete")
    
    @type str1: string
    @param str1: String to compare

    @type str2: string
    @param str2: String to compare
    
    @type rInclude: string
    @param rInclude: Instruct what to include into output. Expected "insert" or "delete", default is
                     "insert delete", inserted and deleted will be highlighted.
    
    @rtype: string
    @return: Html formatted string highlighting changes between str1 and str2.
    """
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

def buildcommitinfotable_helper(object):
    """
    buildcommitinfotable_helper(object)
    
    @type object: any
    @param object: what need to be outputed into commint info table
    
    @rtype: string
    @return: Html formatted string produced from object parameter. Lenght can be zero.
    """
    ## just a string, return as is
    if type(object) is str:
        html.escape(object)
        
    if type(object) is set:
        rstring = ""
        separatorstr = ""
        for i in object:
            rstring += separatorstr
            rstring += html.escape(str(i))
            separatorstr = "<br>"
        return rstring

    return html.escape(str(object))
    

def buildcommitinfotable(oldcommit,  newcommit):
    """
    buildcommitinfotable(oldcommit, newcommit)
    
    @type oldcommit: ezbench.report.Commit
    @param oldcommit: old commit
    
    @type newcommit: ezbench.report.Commit
    @param newcommit: new commit
    
    @rtype: string
    @return: Html formatted string. Html table object to contain commit information from both commits,
             only one is outputted if they're the same
    """
    commit_infos = [("Title:", "title"), ("sha1:", "sha1"),  ("author:", "author"), ("author date:", "author_date"),
        ("signed-of-by:", "signed_of_by"), ("tested-by:", "tested_by"), ("commit date:", "commit_date"), ("commiter:", "commiter") ]

    return_string = """
            <div class="list">
            <ul>
            <table style=\"font-family:arial;font-size: 12pt;border-collapse: collapse;\">"""
    return_string += "\n            <tr class=\"tablehelp\">"
    return_string += "\n            <th class=\"tablehelp\">Commit</th>"
    
    if oldcommit.sha1 == newcommit.sha1:
        return_string += "\n            <th class=\"tablehelp\">Value</th>"
    else:
        return_string += "\n            <th class=\"tablehelp\">Old</th>"
        return_string += "\n            <th class=\"tablehelp\">New</th>"
    
    for commitinfo in commit_infos:
        ## write commit infos. If we get empty strings we don't output those. We can rely this output
        ## at least something as there's sha1.
        writeout = False
        temp_return_string = "\n            <tr class=\"tablehelp\">"
        temp_return_string += "\n                <td class=\"tablehelp\">{}</td>".format(commitinfo[0])
        if oldcommit.sha1 == newcommit.sha1:
            rVal = buildcommitinfotable_helper(getattr(oldcommit, commitinfo[1]))
            if len(rVal) > 0:
                temp_return_string += "\n                <td class=\"tablehelp\">{}</td>".format(rVal)
                writeout = True
        else:
            rVal = buildcommitinfotable_helper(getattr(oldcommit, commitinfo[1]))
            if len(rVal) > 0:
                writeout = True
            temp_return_string += "\n                <td class=\"tablehelp\">{}</td>".format(rVal)
            rVal = buildcommitinfotable_helper(getattr(newcommit, commitinfo[1]))
            if len(rVal) > 0:
                writeout = True
            temp_return_string += "\n                <td class=\"tablehelp\">{}</td>".format(rVal)
        temp_return_string += "\n            </tr>"

        if writeout == True:
            return_string += temp_return_string
    return_string += """
            </table>
            </ul>
            </div>
        </div>\n"""
    return "<h2>Commit information:</h2><br>" + return_string

def buildenvchangestable(global_db, interesting_event, testname, collapsable = True):
    if collapsable is True:
        tableformat = """            <input id="togList{}" type="checkbox">
                <label for="togList{}">
                    <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>+</b>Expand Environment changes:</span>
                    <span style="font-family:arial;font-size: 12pt;background:#CCCCFF;"><b>-</b>Collapse Environment changes:</span>
                </label>
                <div class="list">
                <ul>
                <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;">"""
        temp_return_string = tableformat.format(testname,  testname)
    else:
        tableformat = """
                <div class="list">
                <ul>
                <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;">"""
        temp_return_string = tableformat.format(testname,  testname)

    temp_return_string += "\n            <tr class=\"tablehelp\">"
    temp_return_string += "\n            <th class=\"tablehelp\">Key</th>"
    change_counter = 0

    try:
        for env_set in global_db.db["env_sets"][testname]:
            users = ""
            for user in env_set['users']:
                if user['commit'].label == interesting_event.old.label or user['commit'].label == interesting_event.new.label:
                    if len(users) > 0:
                        users += "<br/>"

                    users += "{}.{}#{}".format(user['log_folder'], user['commit'].label, user['run'])
                    temp_return_string += "\n            <th class=\"tablehelp\">{}</th>".format(users)

        for key in global_db.db["env_diff_keys"][testname]:
            temp_return_string2 = "\n            <tr class=\"tablehelp\">"
            temp_return_string2 += "\n                <td class=\"tablehelp\">{}</td>".format(key)
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
                temp_return_string2 += "\n                <td class=\"tablehelp\">{}</td>".format(diff_html_higlight(temp_vals[0], temp_vals[1], "delete"))
                temp_return_string2 += "\n                <td class=\"tablehelp\">{}</td>".format(diff_html_higlight(temp_vals[0], temp_vals[1], "insert"))
                temp_return_string2 += "\n            </tr>"
                temp_return_string += temp_return_string2
                change_counter += 1
    except:
        pass

    if change_counter > 0:
        return "<h2>Environment changes:</h2><br>" + temp_return_string+"""
            </table>
            </ul>
            </div>
        </div>\n"""
    else:
        return str("")

def differentrunresulttable_variance(testcontents, report):
    barchart = """
    google.charts.load('current', {{packages: ['corechart', 'bar']}});
    google.charts.setOnLoadCallback(drawMaterial);

    function drawMaterial() {{
        var data = new google.visualization.DataTable();

        {}

        var options = {{
            title: 'Run results bar chart or something..',
            hAxis: {{
              title: 'Result',
              viewWindow: {{
                min: [7, 30, 0],
                max: [17, 30, 0]
              }}
            }},
            vAxis: {{
              title: 'Count'
            }}
        }};

        var materialChart = new google.charts.Bar(document.getElementById('chart_div'));
        materialChart.draw(data, options);
    }}
"""

    return_string = ""
    """
        <div class="list">
            <ul>
            <table style=\"font-family:arial;font-size: 12pt;border-collapse: collapse;\">"""
    
    lista = []
    tablehtml1 =  """        <div class="list">
            <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;table-layout: fixed;width: 100%;">
                <tr class="tablehelp">
                    <th class="tablehelp">Run</th>"""

    tablehtml2 = """                <tr class="tablehelp">
                    <th class="tablehelp">Result</th>"""

    for i in range(0, len(testcontents.result.results)):
        runresult = testcontents.result.results[i]
        lista.append(runresult[1])
        tablehtml1 += "\n                    <th class=\"tablehelp\">{}</th>".format(i)
        tablehtml2 += "\n                    <td class=\"tablehelp\" style=\"text-align:center;\">{}</td>".format(runresult[1])

    tablehtml1 += "\n                </tr>\n"
    tablehtml2 += """\n                </tr>
            </table>
        </div>\n"""

    dictResultCounts = {x:lista.count(x) for x in lista}

    datavariable = "var data = google.visualization.arrayToDataTable([\n         ['Result', 'Count', { role: 'style' }],\n"
    for i in dictResultCounts.keys():
        datavariable += "         [\"{}\", {}, '#b87333'],\n".format(str(i), str(dictResultCounts[i]) )
    datavariable += "      ]);"

    return_string += "        <div id=\"chart_div\">\n        </div>\n"
    return_string += tablehtml1+tablehtml2
    return (str("        <h2>Run results:</h2><br>\n" + return_string), barchart.format(datavariable))


def differentrunresulttable_unit(testcontents, report):
    tablehtml1 =  """        <div class="list">
            <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;table-layout: fixed;width: 100%;">
                <tr class="tablehelp">
                    <th class="tablehelp">Run</th>"""

    tablehtml2 = """                <tr class="tablehelp">
                    <th class="tablehelp">Old result</th>"""

    tablehtml3 = """                <tr class="tablehelp">
                    <th class="tablehelp">New result</th>"""

    for i in range(0, max(len(testcontents.new_result.results),  len(testcontents.old_result.results))):
        if i < len(testcontents.old_result.results):
            old_runresult = testcontents.old_result.results[i][1]
        else:
            old_runresult = ""

        if i < len(testcontents.new_result.results):
            new_runresult = testcontents.new_result.results[i][1]
        else:
            new_runresult = ""

        tablehtml1 += "\n                    <th class=\"tablehelp\">{}</th>".format(i)
        tablehtml2 += "\n                    <td class=\"tablehelp\" style=\"text-align:center;\">{}</td>".format(old_runresult)
        tablehtml3 += "\n                    <td class=\"tablehelp\" style=\"text-align:center;\">{}</td>".format(new_runresult)

    tablehtml1 += "\n                </tr>\n"
    tablehtml2 += "\n                </tr>\n"
    tablehtml3 += """\n                </tr>
            </table>
        </div>\n"""

    return_string = tablehtml1+tablehtml2+tablehtml3
    return (str("        <h2>Run results:</h2><br>\n" + return_string), "")


def differentrunresulttable_perf(global_db, testcontents, testname, report):
    return_string_footer = """
            google.charts.load('current', {'packages':['corechart', 'table']});
            google.charts.setOnLoadCallback(drawchart);

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

            chart = new parent.parent.google.visualization.LineChart(document.getElementById("chart_div"));
            chart.draw(data, options);"""

    graph_builder_finish = """
            }
"""

    return_string = ""
    return_string += "        <div id=\"chart_div\">\n        </div>\n"

    testdict = {}
    for commit in global_db.db["commits"]:
        if testname in global_db.db["commits"][commit]["reports"][report]:
            result = global_db.db["commits"][commit]["reports"][report][str(testname)]
            if re.sub('[^0-9a-zA-Z]+', '_', testname) not in testdict:
                testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)] = ["[{}, {}]".format(str(result.commit.commit_date.strftime('new Date(%Y, %m, %d, %H, %M, %S)')),  str(result.diff_target))]
            else:
                lista = testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)]
                lista.append("[{}, {}]".format(str(result.commit.commit_date.strftime('new Date(%Y, %m, %d, %H, %M, %S)')),  str(result.diff_target)))
                testdict[re.sub('[^0-9a-zA-Z]+', '_', testname)] = lista

    for key in testdict:
        datestr = ""
        commastr = ""
        lista = testdict[key]
        for item in lista:
            datestr = datestr+commastr
            commastr = ", "
            datestr = datestr+item

        return_string_footer = return_string_footer+graph_builder.format(datestr)
    return_string_footer = return_string_footer+graph_builder_finish


    tablehtml1 =  """        <div class="list">
            <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;table-layout: fixed;width: 100%;">
                <tr class="tablehelp">
                    <th class="tablehelp">Run</th>"""

    tablehtml2 = """                <tr class="tablehelp">
                    <th class="tablehelp">Result</th>"""

    for i in range(0, len(result.runs)):
        runresult = result.runs[i].result()
        tablehtml1 += "\n                    <th class=\"tablehelp\">{}</th>".format(i)
        tablehtml2 += "\n                    <td class=\"tablehelp\" style=\"text-align:center;\">{}</td>".format(str(runresult))

    tablehtml1 += "\n                </tr>\n"
    tablehtml2 += """\n                </tr>
            </table>
        </div>\n"""

    return_string += str("        <h2>Run results:</h2><br>\n" + tablehtml1 + tablehtml2)
    return (str("        <h2>Perf test history:</h2><br>\n" + return_string), return_string_footer)


def differentrunresulttable_rendering(global_db, testcontents, testname, report):
    new = testcontents.result.average_image_file
    old = new.replace(testcontents.commit_range.new.sha1, testcontents.commit_range.old.sha1)
    diff = '{}_compare_{}'.format(new, os.path.split(old)[1])

    new_e = "/image_{}".format(os.path.split(new)[1])
    old_e = "/image_{}".format(os.path.split(old)[1])
    diff_e = "/image_{}".format(os.path.split(diff)[1])

    return_string = "\t\t\t\t\t<p class=\"testparagraph\">"
    return_string += testcontents.short_desc
    return_string += "\n"
    return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'Old image');\">\n".format(old_e, old_e)
    return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'Diff image');\">\n".format(diff_e, diff_e)
    return_string += "\t\t\t\t\t\t<img src=\"{}\" style=\"width:20%;\" onclick=\"window.open('{}', 'New image');\">\n".format(new_e, new_e)
    return_string += "\t\t\t\t\t</p>"

    tablehtmlformat =  """        <div class="list">
        <table style="font-family:arial;font-size: 12pt;border-collapse: collapse;table-layout: fixed;width: 100%;">
            <tr class="tablehelp">
                    <th class="tablehelp">{}</th>"""
    return_string += tablehtmlformat.format(testcontents.short_desc)
    return_string += "\n                    <td class=\"tablehelp\"><img src=\"{}\" onclick=\"window.open('{}', 'Old image');\"></img></td>".format(old_e, old_e)
    return_string += "\n                    <td class=\"tablehelp\"><img src=\"{}\" onclick=\"window.open('{}', 'Diff image');\"></img></td>".format(diff_e, diff_e)
    return_string += "\n                    <td class=\"tablehelp\"><img src=\"{}\" onclick=\"window.open('{}', 'New image');\"></img></td>".format(new_e, new_e)
    return_string += """\n                </tr>
            </table>
        </div>\n"""
    return(return_string, "")

#######################
## single event page
#######################
def eventpage(global_db,  eventname):
    return_string = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    
    <html xmlns="http://www.w3.org/1999/xhtml">
    <html lang="en">
        <head>
        <meta charset="utf-8"/>
        <style type="text/css">
        body {
            height:auto;
            width:auto;
            background-color:#ffffff
        }
        dummy { padding-left: 4em; }
        tab1 { margin-left: 2em; }
        tab2 { margin-left: 10%; position:inherit }
        tab3 { margin-left: 20%; position:inherit }
        
        .normalparagraph {
            font-family:'Courier New';
        }
        .testparagraph {
            font-family:'Courier New';
            margin-left: 2em;
        }
        .tablehelp {
            border: 1px solid black;
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
        <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
        <script type="text/javascript">
"""
    arrivals = re.split("[ _.]+", eventname)
    if arrivals[0] == "singleevent":
        # 1 = hash
        # 2 = fullname
        # 3 = subname
        # 4 = type
        event_finder = (arrivals[1], arrivals[2], arrivals[3],  arrivals[4])
    else:
        return_string += "<h1>Unecpected error, unknown event!</h1></body>"
        return str(return_string)

    events = global_db.db["events"]
    interesting_event = None
    for current_event in events:
        if event_finder[0] in str(current_event):
            interesting_event = current_event
            break

    if interesting_event == None:
        return_string += "<h1>Unecpected error, unknown event!</h1></body>"
        return str(return_string)

    ##
    # found event, next get the info about test who did this for us.
    #
    testcontents = []
    realname = ""
    eventtype = event_finder[3]
    thisReport = ""
    testnamefullname = ""
    testnamesubname = ""

    if eventtype == "unit":
        eventtype = "unit test"

    for setname in events[interesting_event][eventtype]:
        for report in events[interesting_event][eventtype][setname]:
            for testname in events[interesting_event][eventtype][setname][report]:
                testnamefullname = str(testname.full_name)
                testnamesubname = str(testname.subresult_key)

                if re.sub(singleevent_url_format, '', testnamefullname) == event_finder[1] and re.sub(singleevent_url_format, '', testnamesubname) == event_finder[2]:
                    realname = testnamefullname

                    thisReport = report
                    testcontents.append(testname)
                    break

    #start building the html
    return_string += "<h1><b>"+ eventtype + ":</b> " + realname + "</h1><br>"

    # Commit informations
    return_string += buildcommitinfotable(getattr(getattr(locals()["testname"], "commit_range"), "old"), getattr(getattr(locals()["testname"], "commit_range"), "new"))
    # Environment changes
    return_string += buildenvchangestable(global_db, interesting_event, realname,  False)
    
    #particular test related additions.
    if eventtype == "variance":
        variancerstrings = differentrunresulttable_variance(testcontents[0], thisReport)
        return_string += variancerstrings[0]
        return_string_footer += variancerstrings[1]

    if eventtype == "unit test":
        unitstrings = differentrunresulttable_unit(testcontents[0], thisReport)
        return_string += unitstrings[0]
        return_string_footer += unitstrings[1]

    if eventtype == "perf":
        perfstrings = differentrunresulttable_perf(global_db, testcontents[0], realname, thisReport)
        return_string += perfstrings[0]
        return_string_footer += perfstrings[1]

    if eventtype == "rendering":
        renderingstrings = differentrunresulttable_rendering(global_db, testcontents[0], realname, thisReport)
        return_string += renderingstrings[0]
        return_string_footer += renderingstrings[1]

    return return_string+return_string_footer+"         </script>\n</html>"

