#!/usr/bin/python3

# Script to collect boost library stats.
#
# All data is collected into an internal data structure called gitmodules.
# pprint(gitmodules)
# After it has been gathered, then it is input to the db with a timestamp.
#
# Add a crontab entry
# 0 5 1 * * . $HOME/.web-env-vars && cd $HOME/boost_library_stats && ./scripts/collect_stats.py > /tmp/boost-library-stats.output 2>&1

import os
import sys
import subprocess
import configparser
import re
import glob
from pprint import pprint
from datetime import datetime, timedelta
from pathlib import Path
import psycopg2
import config
from django.utils import timezone
import pytz

PROJECT_PATH = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_PATH))
import django
from django.conf import settings
django.setup()

from apps.boostlibrarystats.models import Stat
from apps.github.models import PullRequest, Issue


#dt = datetime.now()
dt = timezone.now()
dt_one_month_ago = dt + timedelta(days=-30.5)
dt_one_year_ago = dt + timedelta(days=-365)

homedir=os.path.expanduser('~')
boostroot=os.path.join(homedir, "boost-root")
boostbranch="develop"
rebuild_boostdep=False

def checkout_boost():
      if not os.path.isdir(boostroot):
          os.chdir(Path(boostroot).parent)
          print("Cloning boost repo\n", flush=True)
          subprocess.run(["git", "clone", "-b", boostbranch, "https://github.com/boostorg/boost", boostroot])
          os.chdir(Path(boostroot))
          print("---Updating submodules\n", flush=True)
          subprocess.run(["git", "submodule", "update", "--init"])
          print("---Running bootstrap.sh\n", flush=True)
          subprocess.run(["./bootstrap.sh"],shell=True)
          print("---Running b2 headers\n", flush=True)
          subprocess.run(["./b2", "headers"],shell=True)
          print("---Build boostdep\n", flush=True)
          subprocess.run(["./b2 tools/boostdep/build"], shell=True)
      else:
          os.chdir(Path(boostroot))
          print("---Check out " + boostbranch + " branch\n", flush=True)
          subprocess.run(["git", "checkout", boostbranch])
          print("---Git pull\n", flush=True)
          subprocess.run(["git", "pull"])
          print("---Updating submodules\n", flush=True)
          subprocess.run(["git", "submodule", "update", "--init"])
          if rebuild_boostdep:
              print("---Running bootstrap.sh\n", flush=True)
              subprocess.run(["./bootstrap.sh"],shell=True)
              print("---Running b2 headers\n", flush=True)
              subprocess.run(["./b2", "headers"],shell=True)
              print("---Build boostdep\n", flush=True)
              subprocess.run(["./b2 tools/boostdep/build"],shell=True)

def sync_github_repos():

    os.chdir(Path(Path(__file__).resolve().parents[0]))

    print("Sync repos\n", flush=True)
    output = subprocess.run(["./sync-repos.py"], capture_output=True, text=True)
    print(str(output.stdout)[:1000] + "\n", flush=True)
    print(str(output.stderr)[:1000] + "\n", flush=True)
    print("Sync prs\n", flush=True)
    output = subprocess.run(["./sync-prs.py"], capture_output=True, text=True)
    print(str(output.stdout)[:1000] + "\n", flush=True)
    print(str(output.stderr)[:1000] + "\n", flush=True)
    print("Sync issues\n", flush=True)
    output = subprocess.run(["./sync-issues.py"], capture_output=True, text=True)
    print(str(output.stdout)[:1000] + "\n", flush=True)
    print(str(output.stderr)[:1000] + "\n", flush=True)

def discover_library_list():
    print("Discover library list\n", flush=True)
    library_list = []
    gitmodules={}
    os.chdir(Path(boostroot))
    config = configparser.ConfigParser()
    config.read('.gitmodules')
    for each_section in config.sections():
        repattern = re.compile('submodule "(.*)"')
        result=repattern.match(each_section)
        if result:
            libraryname = result.group(1)
            gitmodules[libraryname]=config._sections[each_section]
        if "libs/headers" in config[each_section]["path"]:
            # headers is a "fake" library
            pass
        elif "libs/" in config[each_section]["path"]:
                library_list.append(libraryname)
    return library_list, gitmodules

def calculate_lines_of_code():
    print("Calculate lines of code\n", flush=True)
    for library in library_list:
        includepath = os.path.join(boostroot,gitmodules[library]["path"],"include")
        target = Path(includepath)
        if os.path.isdir(includepath):
            names = {}
            for file in target.rglob("*"):
                if os.path.isfile(file):
                    with file.open("rt") as f:
                        names[f.name] = sum(
                            1 for line in f
                            if line.strip()
                        )
            # pprint(names)
            lines_of_code=0
            for key in names:
                lines_of_code=lines_of_code + names[key]
        else:
            # set value to 0. lines=0
            lines_of_code=0
        gitmodules[library]["lines_of_code"]=lines_of_code
        # print("Library " + library + " has " + str(lines_of_code) + " lines of code.\n", flush=True)

def calculate_lines_of_tests():
    excludefiles=[]
    print("Calculate lines of tests\n", flush=True)
    for library in library_list:
        testspath = os.path.join(boostroot,gitmodules[library]["path"],"test")
        target = Path(testspath)
        if os.path.isdir(testspath):
            names = {}
            for file in target.rglob("*.cpp"):
                if os.path.isfile(file):
                    # print(library + " " + str(file) + "\n", flush=True)
                    if str(file) in excludefiles:
                        print("skipping")
                    else:
                        try:
                            with file.open("rb") as f:
                                names[f.name] = sum(
                                    1 for line in f
                                    if line.strip()
                                )
                        except:
                            print(library + " " + str(file) + "\n", flush=True)
                            print("difficulties opening file")
            # pprint(names)
            lines_of_tests=0
            for key in names:
                lines_of_tests=lines_of_tests + names[key]
        else:
            # set value to 0. lines=0
            lines_of_tests=0
        gitmodules[library]["lines_of_tests"]=lines_of_tests
        # print("Library " + library + " has " + str(lines_of_tests) + " lines of tests.\n", flush=True)

def calculate_commits():
    print("Calculate commits\n", flush=True)
    for library in library_list:
        librarypath = os.path.join(boostroot,gitmodules[library]["path"])
        os.chdir(librarypath)
        output=""
        output = subprocess.run(["git", "rev-list", "--count", "HEAD", '--since="' + str(dt_one_month_ago) + '"'], capture_output=True, text=True)
        # print("commits one month: " + str(output.stdout).strip() + "\n")
        gitmodules[library]["commits_one_month"]=str(output.stdout).strip()
        output=""
        output = subprocess.run(["git", "rev-list", "--count", "HEAD", '--since="' + str(dt_one_year_ago) + '"'], capture_output=True, text=True)
        # print("commits one year: " + str(output.stdout).strip() + "\n")
        gitmodules[library]["commits_one_year"]=str(output.stdout).strip()

def calculate_dependency_level():
    print("Calculate dependency level\n", flush=True)
    os.chdir(Path(boostroot))
    dependency_level=""
    output=""
    output = subprocess.run(["./dist/bin/boostdep", "--module-levels"], capture_output=True, text=True)
    for line in output.stdout.splitlines():
        if not line.strip():
            pass
        elif "Level" in line:
            result=re.match('Level (.*):',line)
            if result:
                dependency_level=result.group(1).strip()
        else:
            result=re.match('^\s*(\S*)',line)
            if result:
                library=result.group(1).strip()

                if library=="numeric~conversion":
                    library="numeric_conversion"
                elif library=="numeric~interval":
                    library="interval"
                elif library=="numeric~ublas":
                    library="ublas"
                elif library=="numeric~odeint":
                    library="odeint"

                if library=="(unknown)":
                    pass
                else:
                    gitmodules[library]["dependency_level"]=dependency_level
            else:
                pass

    dependency_weight=""
    output=""
    output = subprocess.run(["./dist/bin/boostdep", "--module-weights"], capture_output=True, text=True)
    for line in output.stdout.splitlines():
        if not line.strip():
            pass
        elif "Weight" in line:
            result=re.match('Weight (.*):',line)
            if result:
                dependency_weight=result.group(1).strip()
        else:
            result=re.match('^\s*(\S*)',line)
            if result:
                library=result.group(1).strip()

                if library=="numeric~conversion":
                    library="numeric_conversion"
                elif library=="numeric~interval":
                    library="interval"
                elif library=="numeric~ublas":
                    library="ublas"
                elif library=="numeric~odeint":
                    library="odeint"

                if library=="(unknown)":
                    pass
                else:
                    gitmodules[library]["dependency_weight"]=dependency_weight
            else:
                pass

def calculate_open_issues():
    print("Calculate open issues\n", flush=True)
    for library in library_list:

        # First, "open" and "closed" issues in _all

        pull_requests_all=0
        issues_all=0
        all_issues_all=0
        # print("library is " + library + "\n", flush=True)
        my_filter = {}
        my_filter['repo_name'] = library
        pull_requests_all = PullRequest.objects.filter(**my_filter).count()
        # print("pull_requests is " + str(pull_requests) + "\n", flush=True)

        my_filter = {}
        my_filter['repo_name'] = library
        all_issues_all = Issue.objects.filter(**my_filter).count()
        # all_issues includes pull requests. Discover how many plain issues there are.
        issues_all=all_issues_all - pull_requests_all

        gitmodules[library]['issues_all'] = issues_all
        gitmodules[library]['pull_requests_all'] = pull_requests_all

        # Next only "open" issues

        pull_requests=0
        issues=0
        all_issues=0
        # print("library is " + library + "\n", flush=True)
        my_filter = {}
        my_filter['repo_name'] = library
        my_filter['pull_request_state'] = 'open'
        pull_requests = PullRequest.objects.filter(**my_filter).count()
        # print("pull_requests is " + str(pull_requests) + "\n", flush=True)

        my_filter = {}
        my_filter['repo_name'] = library
        my_filter['issue_state'] = 'open'
        all_issues = Issue.objects.filter(**my_filter).count()
        # all_issues includes pull requests. Discover how many plain issues there are.
        issues=all_issues - pull_requests

        gitmodules[library]['issues'] = issues
        gitmodules[library]['pull_requests'] = pull_requests

def insert_data():
    print("Insert data\n", flush=True)
    for library in library_list:
        # print("library is " + library + "\n", flush=True)
        record_to_insert = Stat(library=library, lines_of_code=gitmodules[library]['lines_of_code'], lines_of_tests=gitmodules[library]['lines_of_tests'], commits_one_month=gitmodules[library]['commits_one_month'], commits_one_year=gitmodules[library]['commits_one_year'], dependency_level= gitmodules[library]['dependency_level'], dependency_weight=gitmodules[library]['dependency_weight'], issues=gitmodules[library]['issues'], issues_all=gitmodules[library]['issues_all'], pull_requests=gitmodules[library]['pull_requests'], pull_requests_all=gitmodules[library]['pull_requests_all'], created=dt.isoformat(' ', 'seconds'))

        # print("record_to_insert is " + str(record_to_insert) + "\n", flush=True)
        record_to_insert.save()

    # creating a database view
    conn = psycopg2.connect(
       database=os.environ['DATABASE_NAME'], user=os.environ['DATABASE_USER'], password=os.environ['DATABASE_PASSWORD'], host=os.environ['DATABASE_HOST'], port=os.environ['DATABASE_PORT']
    )
    cursor = conn.cursor()
    view_name="view_" + dt.strftime("%Y_%m_%d")
    postgres_insert_query = "CREATE OR REPLACE VIEW " + view_name + "  as SELECT * from stats where created = '" + dt.isoformat(' ', 'seconds') + "'; "
    # print("postgres_insert_query is " + str(postgres_insert_query) + "\n", flush=True)
    cursor.execute(postgres_insert_query, record_to_insert)

    # close communication with the PostgreSQL database server
    cursor.close()
    # commit the changes
    conn.commit()

def main():
    checkout_boost()
    global library_list
    global gitmodules
    library_list, gitmodules = discover_library_list()
    sync_github_repos()
    calculate_lines_of_code()
    calculate_lines_of_tests()
    calculate_commits()
    calculate_dependency_level()
    calculate_open_issues()
    insert_data()

if __name__ == '__main__':
    main()

