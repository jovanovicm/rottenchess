import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    endpoints = ec2.describe_vpc_endpoints()
    
    interface_endpoints = []

    for endpoint in endpoints['VpcEndpoints']:
        if endpoint['VpcEndpointType'] == 'Interface':
            interface_endpoints.append(endpoint['VpcEndpointId'])

    for endpoint_id in interface_endpoints:
        ec2.delete_vpc_endpoints(
            VpcEndpointIds=[endpoint_id]
        )

    return {
        'statusCode': 200,
    }
