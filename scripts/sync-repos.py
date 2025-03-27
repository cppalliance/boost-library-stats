#!/usr/bin/env python

# Run this from root of project
# poetry run python3 scripts/sync-repos.py

import sys
import django
import os
import logging
import pathlib
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)

# sys.path.append("/home/bdeploy/bweb")
PROJECT_PATH = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_PATH))
# os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
django.setup()
from apps.github.models import Repo
from restmote.sync import sync_objects, remove_objects, full_sync

field_bindings = {
                'id': 'id',
                'name': 'repo_name',
                'full_name': 'repo_full_name',
                'git_url': 'repo_git_url',
                'clone_url': 'repo_clone_url',
                'html_url': 'repo_html_url',
                }

static_field_bindings = {'repo_full_name': 'boostorg/beast'}

full_sync("/orgs/boostorg/repos", "", Repo, field_bindings)
