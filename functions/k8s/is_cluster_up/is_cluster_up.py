import boto3
import os
import json

def lambda_handler(event, context):
    cluster_name = os.environ['CLUSTER_NAME']
    eks = boto3.client('eks')
    
    try:
        response = eks.describe_cluster(name=cluster_name)
        cluster_status = response['cluster']['status']
        
        if cluster_status == 'ACTIVE':
            return {
                'statusCode': 200,
                'clusterUp': True,
                'body': json.dumps(f'Cluster {cluster_name} is active.')
            }
        else:
            return {
                'statusCode': 200,
                'clusterUp': False,
                'body': json.dumps(f'Cluster {cluster_name} is not active. Current status: {cluster_status}')
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'clusterUp': False,
            'body': json.dumps(f'Error checking cluster status: {str(e)}')
        }