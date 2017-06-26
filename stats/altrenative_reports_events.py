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
import sys
import os
import difflib
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
## single event page
#######################
def diff_html_higlight(str1,  str2,  rInclude="insert delete"):
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

def event_result(global_db, eventpath):
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
        
			<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
			<script type="text/javascript">
				google.charts.load('current', {'packages':['corechart', 'table']});
			</script>        
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
            if test == "variance":
                print("variance")
            if test == "unit test":
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

#            temp_return_string = tableformat.format(testname,  testname)
#            temp_return_string += "\n            <tr style=\"border: 1px solid black\">"
#            temp_return_string += "\n            <th style=\"border: 1px solid black\">Key</th>"
#            change_counter = 0
#
#            try:
#                for env_set in global_db.db["env_sets"][testname]:
#                    users = ""
#                    for user in env_set['users']:
#                        if user['commit'].label == interesting_event.old.label or user['commit'].label == interesting_event.new.label:
#                            if len(users) > 0:
#                                users += "<br/>"
#
#                            users += "{}.{}#{}".format(user['log_folder'], user['commit'].label, user['run'])
#                            temp_return_string += "\n            <th style=\"border: 1px solid black\">{}</th>".format(users)
#
#                for key in global_db.db["env_diff_keys"][testname]:
#                    temp_return_string2 = "\n            <tr style=\"border: 1px solid black\">"
#                    temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(key)
#                    temp_vals = []
#                    for env_set in global_db.db["env_sets"][testname]:
#                        for user in env_set['users']:
#                            if user['commit'].label == interesting_event.old.label or user['commit'].label == interesting_event.new.label:
#                                if key in dict(env_set['set']):
#                                    env_val = dict(env_set['set'])[key]
#                                else:
#                                    env_val = "MISSING"
#                                temp_vals.append(str(env_val))
#
#                    if len(temp_vals) == 2 and temp_vals[0] != temp_vals[1]:
#                        temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(diff_html_higlight(temp_vals[0], temp_vals[1], "delete"))
#                        temp_return_string2 += "\n                <td style=\"border: 1px solid black\">{}</td>".format(diff_html_higlight(temp_vals[0], temp_vals[1], "insert"))
#                        temp_return_string2 += "\n            </tr>"
#                        temp_return_string += temp_return_string2
#                        change_counter += 1
#            except:
#                pass
#
#            if change_counter > 0:
#                return_string += temp_return_string
#                return_string += """
#            </table>
#            </ul>
#            </div>
#        </div>
#"""

####################################

            for j in events[interesting_event][test][testname]:

                if test != "perf":
                    return_string += "\t\t\t\t\t<p class=\"testparagraph\">"

                for e in events[interesting_event][test][testname][j]:
                    if not isinstance(e, EventRenderingChange):
                        if test == "perf":
                            return_string += "\t\t\t\t\t<div class=\"testonelinerparagraph\">"

                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub('[_ ]', '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))
                        elif test == "unit test":
                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub('[_ ]', '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))

#                            return_string += html.escape(e.short_desc)
#                            return_string += "<br>"
                            return_string += "old status: "
                            for run in range(len(e.old_status.results)):
                                return_string += " {}".format(e.old_status.results[run][1])
                            return_string += "<br>new status: "
                            for run in range(len(e.new_status.results)):
                                return_string += " {}".format(e.new_status.results[run][1])
                            return_string += "<br>"
                        elif test == "variance":
                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub('[_ ]', '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))
                            return_string += "<br>"
                            return_string += "results from runs ({}): ".format(str(len(e.result.results)))
                            for run in range(len(e.result.results)):
                                return_string += " {}".format(e.result.results[run][1])
                        else:
                            return_string += html.escape(e.short_desc)
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

                if test != "perf":
                    return_string += "\t\t\t\t\t</p>"

    return_string += return_string_footer
    return str(return_string)

#######################
## events page
#######################
def list_events(global_db):
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
