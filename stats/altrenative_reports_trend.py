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

#######################
## trend page
#######################
def test_color_code(testname):
    return int(sum(bytearray(testname, 'ascii'))*12345.12345%0xffffff)

def one_test(testname):
    return "\n\t\t\t\t<input type=\"checkbox\" onClick=\"checkClick()\" " \
        "id=\"{}\" checked><span style=\"color:#{:06X};\">&#9608;</span>" \
        " {} <br>".format(testname, test_color_code(testname), \
        testname)

def decorate_trendgroup(testname, group, elementindexes):
    return "\n\t\t<div style=\"display: inline-block; width: 32vw\">" \
        "\n\t\t\t<fieldset><legend><input type=\"checkbox\" id=\"{}\" " \
        "onClick=\"checkClick(\'{}\', {})\" checked>{}</input></legend>{}" \
        "\n\t\t\t</fieldset>\n\t\t</div>".format(testname, testname, \
        elementindexes, testname, group)

def trend_page(global_db, eventpath):
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
        colorlist += "{}\n\t\t\t\t{}: {{ lineDashStyle: [1,0], color: '#{:06X}'}}".format(commachar,  counter, test_color_code(test) )

        splitted = test.split(':', 1)

        if singleString[0] == 0:
            singleString[1] = splitted[0]
            singleString[0] += 1
            grouppingString[0] += one_test(test)
            grouppingString[1] += "{}".format(str(counter))
        else:
            if singleString[1] == splitted[0]:
                singleString[0] += 1
                grouppingString[0] += one_test(test)
                grouppingString[1] += ", {}".format(str(counter))
            else:
                if singleString[0] is 1:
                    onetimers[0] += grouppingString[0]
                    if len(onetimers[1]) > 0:
                        onetimers[1] += ", "
                    onetimers[1] += grouppingString[1]
                    grouppingString[0] = one_test(test)
                    grouppingString[1] = "{}".format(str(counter))
                    singleString = [1,  splitted[0]]
                else:
                    return_stringi += decorate_trendgroup(singleString[1], grouppingString[0],  grouppingString[1])
                    grouppingString = ["", ""]
                    singleString = [1,  splitted[0]]
                    grouppingString[0] += one_test(test)
                    grouppingString[1] += "{}".format(str(counter))

        commachar = ", "
        counter += 1

    googleArrayData += "],\n"

    if singleString[0] == 1:
        onetimers[0] += grouppingString[0]
        onetimers[1] += ", {}".format(grouppingString[1])
    else:
        return_stringi += decorate_trendgroup(singleString[1], grouppingString[0], grouppingString[1])

    return_stringi += decorate_trendgroup("Single Tests", onetimers[0], onetimers[1])

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
