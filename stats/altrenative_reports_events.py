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

import altrenative_reports_singleevent

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
</html>
"""

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

    for test in events[interesting_event]:
        teststring = ""
        assstring = ""

        for testname in events[interesting_event][test]:

            if len(teststring) > 0:
                assstring = "s"
                teststring += ", "

            teststring += str(testname)

        subentries += "\t\t\t\t<li><b>{} {} test{}</b> {}</li>\n".format(test,  len(events[interesting_event][test]), assstring, teststring)
    subentries += "\t\t\t</ul>"
    
    return_string += "\t\t<p class=\"normalparagraph\">{}</p>\n".format(subentries)

    for test in events[interesting_event]:
        return_string += "\t\t\t<h2>{}</h2>\n".format(str(test))
        for testname in events[interesting_event][test]:
            return_string += "\t\t\t\t<h4>{}</h4>\n".format(str(testname))

            for j in events[interesting_event][test][testname]:
                return_string += "\t\t\t\t\t<p class=\"testparagraph\">"

                for e in events[interesting_event][test][testname][j]:
                    if not isinstance(e, EventRenderingChange):
                        if test == "perf":

                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub(altrenative_reports_singleevent.singleevent_url_format, '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))
                        elif test == "unit test":
                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub(altrenative_reports_singleevent.singleevent_url_format, '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))

                        elif test == "variance":
                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub(altrenative_reports_singleevent.singleevent_url_format, '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))
                        else:
                            if e.subresult_key == None:
                                thisname = e.full_name
                            else:
                                thisname = e.subresult_key
                            return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub(altrenative_reports_singleevent.singleevent_url_format, '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))
                            return_string += "<br>"
                    else:
                        # Reconstruct image path
                        if e.subresult_key == None:
                            thisname = e.full_name
                        else:
                            thisname = e.subresult_key
                        return_string += "\t\t\t\t<a href=\"#\" onclick=\"window.open('{}', '{}')\";>{}</a>\n".format(str("singleevent_"+event_finder+"_"+re.sub(altrenative_reports_singleevent.singleevent_url_format, '', thisname)+"_"+test+".html"), str(e.subresult_key),  html.escape(e.short_desc))

                    return_string += "\n\t\t\t\t\t<br>\n"

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
