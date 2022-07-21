#!/usr/bin/python3

# Script to collect boost library stats.
# The first version of this uses direct psycopg2 database access. Could be migrated to django models.
# Use os.environ for db access such as.
# 'ENGINE': 'django.db.backends.postgresql',
# 'NAME': os.environ['DATABASE_NAME'],
# 'HOST': os.environ['DATABASE_HOST'],
# 'PORT': os.environ['DATABASE_PORT'],
# 'USER': os.environ['DATABASE_USER'],
# 'PASSWORD': os.environ['DATABASE_PASSWORD'],
#
# All data is collected into an internal data structure called gitmodules. 
# pprint(gitmodules)
# After it has been gathered, then it is input to the db with a timestamp.

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
# from config import config
import config

dt = datetime.now()
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
    print(str(output.stdout) + "\n", flush=True)
    print("Sync prs\n", flush=True)
    output = subprocess.run(["./sync-prs.py"], capture_output=True, text=True) 
    print(str(output.stdout) + "\n", flush=True)
    print("Sync issues\n", flush=True)
    output = subprocess.run(["./sync-issues.py"], capture_output=True, text=True) 
    print(str(output.stdout) + "\n", flush=True)

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
    conn = psycopg2.connect(
           database=os.environ['DATABASE_NAME'], user=os.environ['DATABASE_USER'], password=os.environ['DATABASE_PASSWORD'], host=os.environ['DATABASE_HOST'], port=os.environ['DATABASE_PORT']
        )
    cursor = conn.cursor()
    for library in library_list:
        pull_requests=0
        issues=0
        all_issues=0
        # print("library is " + library + "\n", flush=True)
        postgres_query = "select COUNT(*) from github_pullrequest where repo_name = '" + library + "' ;"
        # print("postgres_query is " + str(postgres_query) + "\n", flush=True)
        cursor.execute(postgres_query)
        records_one = cursor.fetchone()
        # print ("Printing first record", records_one, flush=True)
        pull_requests=int(records_one[0])

        postgres_query = "select COUNT(*) from github_issue where repo_name = '" + library + "' ;"
        # print("postgres_query is " + str(postgres_query) + "\n", flush=True)
        cursor.execute(postgres_query)
        records_one = cursor.fetchone()
        # print ("Printing first record", records_one, flush=True)
        all_issues=int(records_one[0])
        # all_issues includes pull requests. Discover how many plain issues there are.
        issues=all_issues - pull_requests

        gitmodules[library]['issues'] = issues
        gitmodules[library]['pull_requests'] = pull_requests

    # close communication with the PostgreSQL database server
    if(conn):
        cursor.close()
        conn.close()


def create_tables():
    """ create tables in the PostgreSQL database"""
    print("Create table\n", flush=True)
    # optionally add this command during testing:
    # "DROP TABLE stats CASCADE",
    # not in production.
    commands = (
        """
        CREATE TABLE stats (
            item_id SERIAL PRIMARY KEY,
            library VARCHAR(50) NOT NULL,
            lines_of_code INTEGER,
            lines_of_tests INTEGER,
            commits_one_month INTEGER,
            commits_one_year INTEGER,
            dependency_level INTEGER,
            dependency_weight INTEGER,
            issues INTEGER,
            pull_requests INTEGER,
            created timestamptz
        )
        """,
        )
    conn = None
    try:
        # read the connection parameters
        # params = config()

        # connect to the PostgreSQL server
        # conn = psycopg2.connect(**params)

        conn = psycopg2.connect(
           database=os.environ['DATABASE_NAME'], user=os.environ['DATABASE_USER'], password=os.environ['DATABASE_PASSWORD'], host=os.environ['DATABASE_HOST'], port=os.environ['DATABASE_PORT']
        )
        cursor = conn.cursor()
        # create table one by one
        for command in commands:
            cursor.execute(command)
        # close communication with the PostgreSQL database server
        cursor.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def insert_data():
    print("Insert data\n", flush=True)
    conn = psycopg2.connect(
           database=os.environ['DATABASE_NAME'], user=os.environ['DATABASE_USER'], password=os.environ['DATABASE_PASSWORD'], host=os.environ['DATABASE_HOST'], port=os.environ['DATABASE_PORT']
        )
    cursor = conn.cursor()

    postgres_insert_query = """ INSERT INTO stats (library, lines_of_code, lines_of_tests, commits_one_month, commits_one_year, dependency_level, dependency_weight, issues, pull_requests, created ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    for library in library_list:
        # print("library is " + library + "\n", flush=True)
        record_to_insert = (library, gitmodules[library]['lines_of_code'], gitmodules[library]['lines_of_tests'], gitmodules[library]['commits_one_month'], gitmodules[library]['commits_one_year'],
            gitmodules[library]['dependency_level'], gitmodules[library]['dependency_weight'], gitmodules[library]['issues'], gitmodules[library]['pull_requests'], dt.isoformat(' ', 'seconds'))
        # print("record_to_insert is " + str(record_to_insert) + "\n", flush=True)
        cursor.execute(postgres_insert_query, record_to_insert)

    # create view
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
    create_tables()
    insert_data()

if __name__ == '__main__':
    main()

