import os
import json
import boto3

def lambda_handler(event, context):
    cluster_name = os.getenv("CLUSTER_NAME")
    aws_region = os.getenv("AWS_REGION")
    account_id = os.getenv("ACCOUNT_ID")
    irsa_role_name = os.getenv("IRSA_ROLE_NAME", "test-IRSAServiceRole")
    
    eks_client = boto3.client("eks", region_name=aws_region)
    iam_client = boto3.client("iam", region_name=aws_region)
    
    cluster_info = eks_client.describe_cluster(name=cluster_name)
    oidc_issuer_url = cluster_info['cluster']['identity']['oidc']['issuer']
    oidc_provider = oidc_issuer_url.replace("https://", "")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{account_id}:oidc-provider/{oidc_provider}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringLike": {
                        f"{oidc_provider}:sub": "system:serviceaccount:*:*"
                    }
                }
            }
        ]
    }
    trust_policy_json = json.dumps(trust_policy)
    
    try:
        iam_client.update_assume_role_policy(
            RoleName=irsa_role_name,
            PolicyDocument=trust_policy_json
        )
        role_arn = iam_client.get_role(RoleName=irsa_role_name)['Role']['Arn']
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "IRSA role updated successfully.",
                "roleArn": role_arn,
                "oidc_provider": oidc_provider
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error updating IRSA role: {str(e)}")
        }