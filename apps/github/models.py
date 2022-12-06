from django.db import models

# Create your models here.

class Issue(models.Model):
    id = models.BigIntegerField(primary_key=True)
    repo_name = models.TextField()
    repo_full_name = models.TextField()
    issue_number = models.IntegerField()
    issue_url = models.TextField()
    issue_title = models.TextField()
    issue_created_at = models.TextField()
    issue_updated_at = models.TextField()
    issue_closed_at = models.TextField(null=True, blank=True)
    issue_state = models.TextField()

class PullRequest(models.Model):
    id = models.BigIntegerField(primary_key=True)
    repo_name = models.TextField()
    repo_full_name = models.TextField()
    pull_request_number = models.IntegerField()
    pull_request_url = models.TextField()
    pull_request_title = models.TextField()
    pull_request_created_at = models.TextField()
    pull_request_updated_at = models.TextField()
    pull_request_closed_at = models.TextField(null=True, blank=True)
    pull_request_state = models.TextField()

class Repo(models.Model):
    id = models.BigIntegerField(primary_key=True)
    repo_name = models.TextField()
    repo_full_name = models.TextField()
    repo_clone_url = models.TextField()
    repo_git_url = models.TextField()
    repo_html_url = models.TextField()
