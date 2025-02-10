import boto3
import os

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    VPC_ID = os.getenv('VPC_ID')
    SUBNET_ID = [os.getenv('SUBNET_ID')]
    SECURITY_GROUP_ID = [os.getenv('SECURITY_GROUP_ID')]
    AWS_REGION = os.getenv('AWS_REGION')
    ENDPOINT_TYPE = 'Interface'
    PRIVATE_DNS_ENABLED = True

    services = [
        f'com.amazonaws.{AWS_REGION}.logs',
        f'com.amazonaws.{AWS_REGION}.sqs',
        f'com.amazonaws.{AWS_REGION}.ecr.api',
        f'com.amazonaws.{AWS_REGION}.ecr.dkr'
    ]

    for service in services:
        try:
            ec2.create_vpc_endpoint(
                VpcEndpointType=ENDPOINT_TYPE,
                VpcId=VPC_ID,
                ServiceName=service,
                SubnetIds=SUBNET_ID,
                SecurityGroupIds=SECURITY_GROUP_ID,
                PrivateDnsEnabled=PRIVATE_DNS_ENABLED
            )
        except ec2.exceptions.ClientError as e:
            error_message = e.response['Error']['Message']
            if "conflicting DNS domain" in error_message:
                print(f"Skipping {service} due to existing private link: {error_message}")
                continue
            else:
                raise e

    return {
        'statusCode': 200
    }