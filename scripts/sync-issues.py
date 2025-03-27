#!/usr/bin/env python

# Run this from root of project
# poetry run python3 scripts/sync-issues.py

import sys
import django
import os
import logging
import pathlib
# logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)

# sys.path.append("/home/bdeploy/bweb")
PROJECT_PATH = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_PATH))
# os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
django.setup()
from apps.github.models import Issue, Repo
from restmote.sync import sync_objects, remove_objects, full_sync

field_bindings = {
                'id': 'id',
                'number': 'issue_number',
                'html_url': 'issue_url',
                'title': 'issue_title',
                'created_at': 'issue_created_at',
                'updated_at': 'issue_updated_at',
                'state': 'state',
                }

static_field_bindings = {'repo_full_name': 'boostorg/beast'}

# Examples of single repo sync process:
# full_sync("/repos/boostorg/beast/pulls", "", Issue, field_bindings, static_field_bindings={'repo_full_name': 'boostorg/beast'}, rfilter={'repo_full_name': 'boostorg/beast'})

repos = Repo.objects.all()
for repo in repos:
    full_sync("/repos/" + repo.repo_full_name + "/issues", "", Issue, field_bindings, static_field_bindings={'repo_name': repo.repo_name, 'repo_full_name': repo.repo_full_name}, rfilter={'repo_name': repo.repo_name,'repo_full_name': repo.repo_full_name})
