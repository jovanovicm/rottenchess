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
        f'com.amazonaws.{AWS_REGION}.ecr.dkr',
        f'com.amazonaws.{AWS_REGION}.ecs'
    ]

    for service in services:
        ec2.create_vpc_endpoint(
            VpcEndpointType=ENDPOINT_TYPE,
            VpcId=VPC_ID,
            ServiceName=service,
            SubnetIds=SUBNET_ID,
            SecurityGroupIds=SECURITY_GROUP_ID,
            PrivateDnsEnabled=PRIVATE_DNS_ENABLED
        )

    return {
        'statusCode': 200
    }
