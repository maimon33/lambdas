import os
import re
import json
import time
import logging

from datetime import datetime
from datetime import timedelta

import boto3

from botocore.exceptions import ClientError

DATE_FORMAT = "%Y-%m-%dT%H.%M.%S"
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO')
INSTANCE_NAME_PREFIX = os.environ.get('INSTANCE_PREFIXES', 'Crawler,Mongo').split(',')
COPIES_TO_KEEP = int(os.environ.get('AMI_RETENTION_COUNT', '10'))
SNS_TOPIC = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:eu-central-1:214673208397:ops-reports')
INTERVAL = os.environ.get('AMI_INTERVAL', 'daily')


logger = logging.getLogger()
logger.setLevel(LOGLEVEL.upper())


def update_sns(instance_name, duration):
    sns_client = boto3.client('sns', region_name='eu-west-1')
    subject = 'AMI missing'.format(instance_name)
    response = sns_client.publish(
        TopicArn=SNS_TOPIC,
        Message=subject,
        Subject='No AMI have been create for {}, Last AMI created {} hours ago'.format(instance_name, duration),
    )
    
def lambda_handler(event, context):
    instance_dictionary = {}
    instance_names = {}
    client = boto3.client('ec2')
    resource = boto3.resource('ec2')
    
    ami_keep_list = []
    instances = client.describe_instances()
    images = resource.images.filter(Owners=['self'])
    snapshots_dict = client.describe_snapshots(OwnerIds=["self"])
    
    if INTERVAL == "daily":
        hours_between_amis = 24
    elif INTERVAL == "weekly":
        hours_between_amis = 168
    else:
        hours_between_amis = 0
    
    # Get instance for the account
    logger.info("Reviewing {} instances".format(len(instances["Reservations"])))
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            try:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name" and tag["Value"] in INSTANCE_NAME_PREFIX:
                        logger.info("adding {} to instances dictionary".format(instance["InstanceId"]))
                        instance_names[instance["InstanceId"]] = tag["Value"]
                        instance_id = instance["InstanceId"]
                        instance_dictionary[instance_id] = []
            except:
                logger.warning("No Name tag found")
                pass
    
    # Get AMIs for instanses requested
    for image in images:
        try:
            if image.name.split(" ")[2] in instance_dictionary.keys():
                instance_name = image.name.split(" ")[2]
                image_date = datetime.strptime(image.creation_date[:-5].replace(":","."), DATE_FORMAT).strftime(DATE_FORMAT)
                instance_dictionary[instance_name].append("{} {}".format(image_date, image.image_id))
                ami_keep_list.append(image.image_id)
        except Exception as e:
            logger.warning(e)
    
    # Sort Images by date and reverse to 
    for key, value in instance_dictionary.items():
        value.sort(reverse=True)
        
    # Create an AMI if the time has come
    for instance, snapshots in instance_dictionary.items():
        now = datetime.now().strftime(DATE_FORMAT)
        try:
            newest_ami_date = snapshots[0].split(" ")[0]
            logger.info("Latest AMI for {} was created at {}".format(instance_names[instance], newest_ami_date))
        except IndexError:
            newest_ami_date = (datetime.now() - timedelta(days=365)).strftime(DATE_FORMAT)
            
        difference = datetime.now().strptime(now, DATE_FORMAT) - datetime.strptime(newest_ami_date, DATE_FORMAT)

        logger.info(difference.total_seconds() / 3600)

        if difference.total_seconds() / 3600 >= hours_between_amis:
            try:
                logger.info("taking snapshot for {}".format(instance))
                creating = "true"
                client.create_image(InstanceId=instance, 
                                    Name="Lambda - {} from {}".format(instance, now), 
                                    Description="Lambda created AMI of instance {} from {}".format(instance, now), 
                                    TagSpecifications=[{'ResourceType': 'image', 'Tags': [{'Key': 'Name', 'Value': instance_names[instance]}]}],
                                    NoReboot=True, 
                                    DryRun=False)
            except ClientError as e:
                logger.warning(e)
                creating = "true"
                logger.info("AMI already being created")
        else:
            logger.info("Instance {} - still 'valid'. no action required".format(instance))
            creating = "false"
            
        if difference.total_seconds() / 3600 > hours_between_amis + 1 and creating == "false":
            hours_since_last_ami = difference.total_seconds() / 3600
            update_sns(instance, hours_since_last_ami)
        
    # Delete the oldest AMI if we exceed retention policy
    for instance, snapshots in instance_dictionary.items():
        ami_to_keep = COPIES_TO_KEEP - 1
        indices_to_keep = list(range(ami_to_keep)) + list(range(ami_to_keep, len(snapshots), 7))
        for index, ami in enumerate(snapshots):
            if index not in indices_to_keep:
                ami_id = ami.split(" ")[1]
                try:
                    client.deregister_image(DryRun=False, ImageId=ami_id)
                    logger.info(f"AMI {ami_id} deregistered successfully.")
                except ClientError as e:
                    logger.warning(e)
            else:
                logger.info(f"AMI {ami.split(' ')[1]} is kept.")
        # for ami in snapshots[ami_to_keep:]:
        #     ami_id = ami.split(" ")[1]
        #     try:
        #         ami_delete = client.deregister_image(DryRun=False, ImageId=ami_id)
        #     except ClientError as e:
        #         logger.warning(e)
                
    # Delete orphaned snapshots
    do_not_delete = False
    for snapshot in snapshots_dict["Snapshots"]:
        ami_parent = " "
        # Get creation date from snapshot id
        snapshot_id = snapshot["SnapshotId"]
        try:
            for tag in snapshot["Tags"]:
                for key, value in tag.iteritems():
                    if value or key == "DO NOT DELETE":
                        do_not_delete = True
                        continue
                    else:
                        logger.info("keeping Snapshot: {}".format(snapshot_id))
        except:
            pass
        
        if "Created by CreateImage" in snapshot["Description"] and do_not_delete == False:
            snapshot_description = snapshot["Description"]
            match = re.search("ami-.*", snapshot_description)
            if match:
                ami_parent = match.group().split(" ")[0]
    
            if ami_parent in ami_keep_list:
                pass
            else:
                snapshot_object = resource.Snapshot(snapshot_id)
                try:
                    logger.debug("Deleting orphan snapshot {}".format(snapshot_object))
                    response = snapshot_object.delete()
                    logger.info(response)
                except ClientError as e:
                    logger.warning(e)
        else:
            logger.info("Keeping Snapshot {}".format(snapshot["Description"]))
            pass


if __name__ == '__main__':
    lambda_handler(None, None)
    