import boto3
import os

cloudformation = boto3.client('cloudformation')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    S3_BUCKET = os.environ['S3_BUCKET']
    TEMPLATE_KEY = os.environ['TEMPLATE_KEY']
    VPC = os.environ['VPC']
    EKS_SUBNETS = os.environ['EKS_SUBNETS']
    SECURITY_GROUP = os.environ['SECURITY_GROUP']
    AWS_REGION = os.environ['AWS_REGION']
    
    template_url = f'https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{TEMPLATE_KEY}'
    stack_name = 'TestEKSStack'

    response = cloudformation.create_stack(
        StackName=stack_name,
        TemplateURL=template_url,
        Capabilities=['CAPABILITY_AUTO_EXPAND'],
        Parameters=[
            {
                'ParameterKey': 'VPC',
                'ParameterValue': VPC
            },
            {
                'ParameterKey': 'EKSSubnets',
                'ParameterValue': EKS_SUBNETS
            },
            {
                'ParameterKey': 'SecurityGroup',
                'ParameterValue': SECURITY_GROUP
            },
        ],
    )

    return {
        'statusCode': 200,
        'body': f'Stack {stack_name} creation initiated with template URL: {template_url}',
        'response': response
    }