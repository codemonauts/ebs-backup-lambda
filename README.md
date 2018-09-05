# EBS Backup Script for Lambda

This lambda function should be called by a CloudWatch event once a day and will iterate over all instances
from the regions defined in `vars.ini`. If they have the Tag "tag:Backup" a snapshot will be created.

Most of the code is taken from:
https://serverlesscode.com/post/lambda-schedule-ebs-snapshot-backups/