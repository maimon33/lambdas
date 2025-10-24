# AWS Lambda Functions

Collection of AWS Lambda functions with automated deployment tooling.

## Structure

Each lambda function is in its own directory with:
- `main.py` - Lambda handler
- `requirements.txt` - Python dependencies
- `lambda-role-policy.json` - IAM permissions
- `lambda-role-trust-policy.json` - IAM trust relationship

## Functions

- **ami-create** - Creates and rotates EC2 AMIs
- **aws-cost-report** - Generates AWS cost reports
- **count-ec2-instances** - Counts EC2 instances

## Usage

```bash
# Interactive deployment
./start.sh

# Or manually deploy a function
cd <function-name>
make deploy
```

### Make Commands

- `make run` - Test locally
- `make deploy` - Deploy to AWS
- `make libs` - Install dependencies
- `make init` - Setup and run

## Deployment Frequencies

- Daily - 10:00 AM UTC
- 5Minutes - Every 5 minutes
- 1Minute - Every minute

## Requirements

- AWS CLI configured
- Python 3.11+ (configurable via `PYTHON_VERSION`)
- virtualenv

## Configuration

Set these environment variables to customize behavior:

**Deployment:**
- `REGION` - AWS region (default: us-east-1)
- `PYTHON_VERSION` - Lambda runtime (default: python3.11)

**ami-create Lambda:**
- `LOGLEVEL` - Logging level (default: INFO)
- `INSTANCE_PREFIXES` - Comma-separated instance names (default: Crawler,Mongo)
- `AMI_RETENTION_COUNT` - Number of AMIs to keep (default: 10)
- `SNS_TOPIC_ARN` - SNS topic for alerts
- `AMI_INTERVAL` - Backup interval (default: daily)
