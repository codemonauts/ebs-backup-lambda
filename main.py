#! /usr/bin/env python3

import boto3
import configparser
from datetime import date, timedelta

config = configparser.RawConfigParser()
config.read("./vars.ini")


def find_instance_name(instance):
    for tags in instance["Tags"]:
        if tags["Key"] == "Name":
            return tags["Value"]
    return ""


def lambda_handler(event, context):
    regions = config.get("regions", "regionList").split(",")
    backup_tag = config.get("main", "EC2_INSTANCE_TAG")
    retention_days = config.getint("main", "RETENTION_DAYS")
    account = event["account"]
    today = date.today()

    for region in regions:
        ec = boto3.client("ec2", region_name=region)
        reservations = ec.describe_instances(
            Filters=[
                {"Name": "tag-key", "Values": [backup_tag]},
            ]
        )["Reservations"]
        instances = sum([[i for i in r["Instances"]] for r in reservations], [])

        for instance in instances:
            for device in instance["BlockDeviceMappings"]:
                if not device.get("Ebs"):
                    # skip non EBS volumes
                    continue

                vol_id = device["Ebs"]["VolumeId"]
                instance_id = instance["InstanceId"]
                instance_name = find_instance_name(instance)
                print(f"Found EBS Volume {vol_id} on Instance {instance['InstanceId']}")

                snapshot_name = f"{vol_id}_{date.strftime('%Y-%m-%d')}"
                delete_date = date.today() + timedelta(days=retention_days)

                snap = ec.create_snapshot(
                    Description=f"Snapshot of {device['DeviceName']} from {instance_id} ({instance_name})",
                    VolumeId=vol_id,
                    TagSpecifications=[
                        {
                            "ResourceType": "snapshot",
                            "Tags": [
                                {
                                    "Key": "DeleteOn",
                                    "Value": delete_date.strftime("%Y-%m-%d"),
                                },
                                {
                                    "Key": "Name",
                                    "Value": snapshot_name,
                                },
                                {
                                    "Key": "DeviceName",
                                    "Value": device["DeviceName"],
                                },
                            ],
                        },
                    ],
                )

        filters = [
            {"Name": "tag-key", "Values": ["DeleteOn"]},
            {"Name": "tag-value", "Values": [today.strftime("%Y-%m-%d")]},
        ]
        snapshot_response = ec.describe_snapshots(OwnerIds=[account], Filters=filters)
        for snap in snapshot_response["Snapshots"]:
            print(f"Deleting snapshot {snap['SnapshotId']}")
            ec.delete_snapshot(SnapshotId=snap["SnapshotId"])
