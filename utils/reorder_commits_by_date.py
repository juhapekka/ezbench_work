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

from ezbench import *
import subprocess
import argparse
import shutil
import sys
import os

# Start by checking what the user wants to monitor!
parser = argparse.ArgumentParser()
parser.add_argument("--path", "-p", help="Repository path")
parser.add_argument("log_folder")
args = parser.parse_args()

if len(args.path) == 0:
    print ("You need to specify a path to the git repo using -p.")
    exit(1)

commits_path = os.path.abspath(args.log_folder + "/commit_list")
commits_sav_path = commits_path + ".sav"

if os.path.exists(commits_sav_path):
    shouldAbort = input("The backup commit list file '{}' already exists and will be deleted.\nAbort? (y/N)".format(commits_sav_path)).lower() == 'y'
    if shouldAbort:
        exit(0)
    print()
shutil.copyfile(commits_path, commits_sav_path)

report = genPerformanceReport(args.log_folder, False)

f = open(commits_path, 'w')

# Move to the repo's list
os.chdir(args.path)

for commit in report.commits:
    gitCommandLine = ["/usr/bin/git", "show", "--format=%ct", "--date=local", "-s", commit.sha1]
    commit.date = subprocess.check_output(gitCommandLine).decode().split(' ')[0]

commits = sorted(report.commits, key=lambda commit: commit.date)

for commit in commits:
    val = "{full_name}\n".format(full_name=commit.full_name)
    f.write(val)
    print(val, end="")
