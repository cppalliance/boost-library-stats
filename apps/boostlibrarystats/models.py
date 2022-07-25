from django.db import models

# Create your models here.

class Stat(models.Model):
    id = models.BigAutoField(primary_key=True)
    library = models.CharField(max_length=50)
    lines_of_code = models.IntegerField()
    lines_of_tests = models.IntegerField()
    commits_one_month = models.IntegerField()
    commits_one_year = models.IntegerField()
    dependency_level = models.IntegerField()
    dependency_weight = models.IntegerField()
    issues = models.IntegerField()
    pull_requests = models.IntegerField()
    created = models.DateTimeField()
    class Meta:
        db_table = "stats"
