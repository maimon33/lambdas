import json
import boto3
from datetime import datetime, timezone, timedelta

running_instances_metric_name = 'NumberRunningInstances'
running_spot_instances_metric_name = 'NumberRunningSpotInstances'
data_upload_age = 'DataUploadAge'
orphan_eips_metric_name = 'NumberOrphanElasticIps'
ec2_metric_namespace = 'XPOZ/EC2'
s3_metric_namespace = 'XPOZ/S3'
bucket_name = 'mixer.inventory'
folder_prefix = 'AVIT/mixer.dataupload/AVIT_Inventory'

def lambda_handler(event, context):
    ec2 = boto3.resource('ec2', region_name='eu-central-1')
    s3_client = boto3.client('s3', region_name='eu-central-1')
    cloudwatch = boto3.client('cloudwatch')

    timestamp = datetime.utcnow()
    num_instances = count_instances(ec2)
    spot_instances = count_spot_instances(ec2)
    num_eips = count_orphin_eip(ec2)
    dataupload_latest_file_age = check_latest_object_age(s3_client, bucket_name, folder_prefix)
    print("Observed %s instances running at %s" % (num_instances, timestamp))
    print("Observed %s spot instances running at %s" % (spot_instances, timestamp))
    print("Observed %s orphaned elastic ips at %s" % (num_eips, timestamp))
    print("Observed %s age of file in 'mixer.dataupload' bucket at %s" % (dataupload_latest_file_age, timestamp))
    publish_metrics(cloudwatch, timestamp, num_instances, spot_instances, num_eips, dataupload_latest_file_age)
    

def count_spot_instances(ec2):
    total_instances = 0
    instances = ec2.instances.filter(Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running',
                    ]
                },
                {
                    'Name': 'instance-lifecycle',
                    'Values': [
                        'spot',
                    ]
                },
        ])
    for _ in instances:
        total_instances += 1
    return total_instances

def count_instances(ec2):
    spot_instances = 0
    total_instances = 0
    instances = ec2.instances.filter(Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running',
                    ]
                }
            ])
    for _ in instances:
        if _.instance_lifecycle == 'spot':
            spot_instances += 1
        else:
            total_instances += 1
    return total_instances

def check_latest_object_age(s3_client, bucket_name, folder_prefix):
    today = datetime.now(timezone.utc)
    date_str = today.strftime('%Y-%m-%dT01-00Z')
    days_back = 1
    inve_files = {}
    total_size = 0

    success = False
    while not success:
        try:
            print("Now trying: {}".format(date_str))
            inventory = s3_client.get_object(Bucket=bucket_name, Key="{}/{}/manifest.json".format(folder_prefix, date_str))
            json_file = inventory['Body'].read().decode('utf-8')
            data = json.loads(json_file)
            for inventory_file in data['files']:
                inve_files[inventory_file['key']] = inventory_file['size']
                total_size += inventory_file['size']
                # print(inventory_file['Key'])
            # print(len(data['files']))
            # new_date = today - timedelta(days=days_back)
            # date_str = new_date.strftime('%Y-%m-%dT01-00Z')
            # days_back += 1
            # print("Total size of files: {}".format(total_size))
            success = True  # If the function succeeds, set success to True to exit the loop
        except Exception as e:
            print("Failed finding files for: {}".format(date_str))
            new_date = today - timedelta(days=days_back)
            date_str = new_date.strftime('%Y-%m-%dT01-00Z')
            days_back += 1
    print("Inventory content:")
    print(json.dumps(inve_files, indent=4))
    # print(inve_files)
    # age = today - inventory['LastModified']
    # age_hours = age.total_seconds()
    # return age_hours
    return total_size

# Counts the number of unattached elastic ip's
def count_orphin_eip(ec2):
    total_eips = 0
    for eip in ec2.vpc_addresses.all():
        if not eip.association:
            total_eips += 1
    return total_eips

# def spot_usage():
#     # Initialize the Cost Explorer client
#     # s3_client = boto3.client('s3', region_name='eu-central-1')
#     ce_client = boto3.client('ce', region_name='us-east-1')

#     # Define the time period for the query
#     end_date = datetime.now().date()
#     start_date = end_date - timedelta(days=30)  # Adjust based on your needs

#     response = ce_client.get_cost_and_usage(
#         TimePeriod={
#             'Start': start_date.strftime('%Y-%m-%d'),
#             'End': end_date.strftime('%Y-%m-%d')
#         },
#         Granularity='DAILY',
#         Filter={
#             "Dimensions": {
#                 "Key": "USAGE_TYPE_GROUP",
#                 "Values": [
#                     "EC2: Spot Instances"
#                 ],
#                 "MatchOptions": ["EQUALS"]
#             }
#         },
#         Metrics=["UsageQuantity"]
#     )
#     print(response)
#     for result in response.get('ResultsByTime', []):
#         start = result['TimePeriod']['Start']
#         end = result['TimePeriod']['End']
#         for group in result.get('Groups', []):
#             amount = group['Metrics']['UsageQuantity']['Amount']
#             cost = group['Metrics']['UnblendedCost']['Amount']
#             print(f"From {start} to {end}, Spot Instance usage: {amount} hours, Cost: ${cost}")

def publish_metrics(cloudwatch, timestamp, num_instances, spot_instances, num_eips, dataupload_latest_file_age):
    cloudwatch.put_metric_data(
        Namespace=ec2_metric_namespace,
        MetricData=[
            {
                'MetricName': running_instances_metric_name,
                'Dimensions': [
                    {
                        'Name': 'InstanceLifecycle',
                        'Value': 'on-demand'
                    }
                ],
                'Timestamp': timestamp,
                'Value': num_instances,
                'Unit': 'Count',
            },
            {
                'MetricName': running_instances_metric_name,
                'Dimensions': [
                    {
                        'Name': 'InstanceLifecycle',
                        'Value': 'spot'
                    }
                ],
                'Timestamp': timestamp,
                'Value': spot_instances,
                'Unit': 'Count',
            },
        ]
    )
    cloudwatch.put_metric_data(
        Namespace=s3_metric_namespace,
        MetricData=[
                        {
                'MetricName': data_upload_age,
                'Dimensions': [
                    {
                        'Name': 'path',
                        'Value': '{}/{}'.format(bucket_name, folder_prefix)
                    }
                ],
                'Timestamp': timestamp,
                'Value': dataupload_latest_file_age,
                'Unit': 'Seconds',
            },
        ]
    )

if __name__ == '__main__':
    # spot_usage()
    lambda_handler({}, {})
