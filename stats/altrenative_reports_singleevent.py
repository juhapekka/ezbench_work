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
####################################
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
        <script type="text/javascript">
        </script>
</html>
"""
    arrivals = re.split("[ _.]+", eventname)
    if arrivals[0] == "singleevent":
        event_finder = (arrivals[1], arrivals[2],  arrivals[3])
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
    eventtype = arrivals[3]
    if eventtype == "unit":
        eventtype = "unit test"

    for setname in events[interesting_event][eventtype]:
        for report in events[interesting_event][eventtype][setname]:
            for testname in events[interesting_event][eventtype][setname][report]:
                if testname.subresult_key == None:
                    thisname = testname.full_name
                else:
                    thisname = testname.subresult_key

                if re.sub('[_ <>@]', '', thisname) == event_finder[1]:
                    realname = thisname
                    testcontents.append(testname)
                    break

    #start building the html
    return_string += "<h1>"+ realname + "</h1><br>"

    # Commit informations
    return_string += buildcommitinfotable(getattr(getattr(locals()["testname"], "commit_range"), "old"), getattr(getattr(locals()["testname"], "commit_range"), "new"))
    # Environment changes
    return_string += buildenvchangestable(global_db, interesting_event, realname,  False)

    return return_string+return_string_footer
