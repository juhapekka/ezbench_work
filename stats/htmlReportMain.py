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

stubSource = """
	<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

	<html xmlns="http://www.w3.org/1999/xhtml">
		<head>
			<title>${title}</title>
			<meta http-equiv="content-type" content="text/html; charset=utf-8" />
			<style>
				body { font-size: 10pt; }
				table { font-size: 8pt; }

				table{
					border-collapse:collapse;
				}

			</style>
			<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
			<script type="text/javascript">
				google.charts.load('current', {'packages':['corechart', 'table']});
			</script>
		</head>

<title>${title}</title>

<style type="text/css">

body {
    overflow: hidden;
}
head, body, html {
    height: calc(100vh- 16px);
    width: calc(100vw- 16px);
}

.container {
    overflow-y: hidden;
    display: table;
    height: 100%;
    width: 100%;
}

.wrapper {
    display: block;
    height:70px;
    width: 100%;
}

.inner {
    display: inline-block;
    height: calc(100vh - 86px);
    width: 100%;
    border: 0px;
}

.playground {
    height: calc(100vh - 86px);
}

    body {background-color: #FFFFFF;min-height: 100%; overflow-x: hidden;}
    h2 {color: #000000;}
    p {font-size: 14pt; font-style: normal; font-weight: normal; color: #000000;}
    .link {color: #000000;}
    .alink {color: #000000;}
    .vlink {color: #000000;}
    table, th, td { border: 0px; border-collapse: collapse;}
    
    .tdwrapper {
        background-color:powderblue;
        text-align:center;
        vertical-align:middle;
    }
    td.tdwrapper:hover { background-color:red; }

</style>

</head>

<body>
<div class="container">
    <div class="wrapper" id="menu">
        <table width="100%">
        <tr>
            <td width="20%" class="tdwrapper" onclick="clicky('events')"><h2>Events</h2></td>
<!---	    <td width="20%" class="tdwrapper" onclick="clicky('commits')"><h2>Commits</h2></td> --->
            <td width="20%" class="tdwrapper" onclick="clicky('trends')"><h2>Trends</h2></td>
<!---	    <td width="20%" class="tdwrapper" onclick="clicky('detail')"><h2>Detail</h2></td> --->
            <td width="20%" class="tdwrapper" onclick="clicky('tests')"><h2>Tests</h2></td>
        </tr>
        </table>
    </div>
    <div id="playground" class="playground">
    </div>
</body>

<script type="text/javascript">
    function clicky(cell) {
        document.getElementById("playground").innerHTML='<object class="inner" type="text/html" data="'+location.origin+'/'+cell+'.html"></object>';
        return false;
    }

    clicky('events');
</script>
"""

