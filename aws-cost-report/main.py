import os
import re
import json
import time
import datetime

import boto3

from collections import defaultdict

from botocore.exceptions import ClientError


def get_secrets(key_name):
    secretsmanager = boto3.client('secretsmanager', region_name='us-east-1')
    response = secretsmanager.get_secret_value(SecretId='ops')
    return json.loads(response['SecretString'])['TOKEN']
    # return json.loads(response['SecretString'])

def _format_json(dictionary):
    return json.dumps(dictionary, indent=4, sort_keys=True)

def abv(service_name):
    for service_item in SERVICES_DIRECTORY.keys():
        if service_item in service_name:
            output = SERVICES_DIRECTORY[service_item]
        else:
            output = service_name[0:40]
    return output

def get_report(requested_time_period, requested_granularity):
    session = boto3.session.Session()
    cd = session.client("ce", "us-east-1")

    results = []

    token = None
    while True:
        if token:
            kwargs = {"NextPageToken": token}
        else:
            kwargs = {}
        data = cd.get_cost_and_usage(
            TimePeriod=requested_time_period,
            Granularity=requested_granularity,
            Metrics=["UnblendedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                {"Type": "DIMENSION", "Key": "SERVICE"},
            ],
            **kwargs
        )
        results += data["ResultsByTime"]
        token = data.get("NextPageToken")
        if not token:
            break
    return results


def send_to_sns(data_attachment, sns_topic_arn, cycle):
    # Create an SNS client
    sns_client = boto3.client('sns', region_name='us-east-1')


    # Publish the message to the specified SNS topic
    response = sns_client.publish(
        TopicArn=sns_topic_arn,
        Message=data_attachment,
        Subject="AWS {} Cost Report".format(cycle)
    )

    # Print the MessageId from the response
    print(f"MessageId: {response['MessageId']}")
    
def lambda_handler(event, context):
    now = datetime.datetime.utcnow()
    start = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    end = now.strftime("%Y-%m-%d")
    # First day of the month
    start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
    start_of_previous_month = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")

    # Last day of the month
    end_of_month = (now.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    end_of_month_str = end_of_month.strftime("%Y-%m-%d")
    end_of_previous_month = now.replace(day=1) - datetime.timedelta(days=1)
    end_of_previous_month_str = end_of_previous_month.strftime("%Y-%m-%d")

    if now.day == 2:
        requested_time_period = {"Start": start_of_previous_month, "End": end_of_previous_month_str}
        requested_granularity = "MONTHLY"
        results = get_report(requested_time_period, requested_granularity)

            # Step 1: Extract and Separate the Information
        time_periods = defaultdict(list)

        for entry in results:
            time_period = entry['TimePeriod']['Start']
            groups = entry['Groups']
            
            time_periods[time_period].extend(groups)

        # Step 2: Sort the Groups by UnblendedCost Amount
        for time_period, groups in time_periods.items():
            time_periods[time_period] = sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)

        # Step 3: Calculate the Total UnblendedCost for Each TimePeriod
        for time_period, groups in time_periods.items():
            total_cost = sum(float(group['Metrics']['UnblendedCost']['Amount']) for group in groups)
            entry = {'Total': {'UnblendedCost': {'Amount': str(total_cost), 'Unit': 'USD'}}, 'Groups': groups}
            time_periods[time_period] = entry

        # sns_topic_arn = "arn:aws:sns:eu-central-1:214673208397:ops-reports"
        sns_topic_arn = "arn:aws:sns:us-east-1:401144893760:ops-report"

        email_body = """
Monthly AWS cost report for the specified time period:
        """

        # Iterate through time_periods
        for time_period, entry in time_periods.items():
            email_body += f"\nTime Period: {time_period}\n"
            email_body += f"Total Daily Cost: ${entry['Total']['UnblendedCost']['Amount']} USD\n"
            email_body += "\nSorted Services:\n"

            # Iterate through Groups
            for group in entry['Groups']:
                if float(group['Metrics']['UnblendedCost']['Amount']) > 1.00:
                    email_body += f"- {group['Keys'][1]}: ${group['Metrics']['UnblendedCost']['Amount']} USD\n"

        email_body += """
Services costing more then $1.00 a day are listed above.
        """
        
        send_to_sns(email_body, sns_topic_arn, "Monthly")


    requested_time_period = {"Start": start, "End": end}
    requested_granularity = "DAILY"
    results = get_report(requested_time_period, requested_granularity)


    # Step 1: Extract and Separate the Information
    time_periods = defaultdict(list)

    for entry in results:
        time_period = entry['TimePeriod']['Start']
        groups = entry['Groups']
        
        time_periods[time_period].extend(groups)

    # Step 2: Sort the Groups by UnblendedCost Amount
    for time_period, groups in time_periods.items():
        time_periods[time_period] = sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)

    # Step 3: Calculate the Total UnblendedCost for Each TimePeriod
    for time_period, groups in time_periods.items():
        total_cost = sum(float(group['Metrics']['UnblendedCost']['Amount']) for group in groups)
        entry = {'Total': {'UnblendedCost': {'Amount': str(total_cost), 'Unit': 'USD'}}, 'Groups': groups}
        time_periods[time_period] = entry

    # sns_topic_arn = "arn:aws:sns:eu-central-1:214673208397:ops-reports"
    sns_topic_arn = "arn:aws:sns:us-east-1:401144893760:ops-report"

    email_body = """
Daily AWS cost report for the specified time period:
    """

    # Iterate through time_periods
    for time_period, entry in time_periods.items():
        email_body += f"\nTime Period: {time_period}\n"
        email_body += f"Total Daily Cost: ${entry['Total']['UnblendedCost']['Amount']} USD\n"
        email_body += "\nSorted Services:\n"

        # Iterate through Groups
        for group in entry['Groups']:
            if float(group['Metrics']['UnblendedCost']['Amount']) > 1.00:
                email_body += f"- {group['Keys'][1]}: ${group['Metrics']['UnblendedCost']['Amount']} USD\n"

    email_body += """
Services costing more then $1.00 a day are listed above.
    """
    
    send_to_sns(email_body, sns_topic_arn, "Daily")

if __name__ == '__main__':
    lambda_handler(None, None)
    