import os
import json
import boto3

def lambda_handler(event, context):
    queue_url = os.getenv("SQS_QUEUE_URL")
    stack_name = os.getenv("STACK_NAME")
    instance_threshold = 2
    
    sqs_client = boto3.client("sqs")
    ec2_client = boto3.client("ec2")
    cf_client = boto3.client("cloudformation")
    
    # Get the number of messages in flight (not visible)
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessagesNotVisible"]
        )
        in_flight = int(response["Attributes"].get("ApproximateNumberOfMessagesNotVisible", "0"))
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error getting SQS attributes: {str(e)}")
        }
    
    # Get the number of running EC2 instances that belong to the stack
    try:
        ec2_response = ec2_client.describe_instances(
            Filters=[
                {"Name": "tag:aws:cloudformation:stack-name", "Values": [stack_name]},
                {"Name": "instance-state-name", "Values": ["running"]}
            ]
        )
        running_instances = sum(len(reservation["Instances"]) for reservation in ec2_response["Reservations"])
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error describing EC2 instances: {str(e)}")
        }
    
    condition1 = (in_flight == 0)
    condition2 = (running_instances == instance_threshold)
    
    # If either condition is met, delete the CloudFormation stack
    if condition1 or condition2:
        try:
            cf_client.delete_stack(StackName=stack_name)
            message = f"Deletion initiated for stack '{stack_name}' because condition met: in_flight={in_flight}, running_instances={running_instances}"
            return {"statusCode": 200, "body": json.dumps(message)}
        except Exception as e:
            return {"statusCode": 500, "body": json.dumps(f"Error deleting stack: {str(e)}")}
    else:
        message = f"No deletion. in_flight={in_flight}, running_instances={running_instances}"
        return {"statusCode": 200, "body": json.dumps(message)}