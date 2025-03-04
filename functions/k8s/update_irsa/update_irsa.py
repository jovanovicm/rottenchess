import os
import json
import boto3

def lambda_handler(event, context):
    # Retrieve environment variables
    cluster_name = os.getenv("CLUSTER_NAME")
    aws_region = os.getenv("AWS_REGION")
    account_id = os.getenv("ACCOUNT_ID")
    irsa_role_name = os.getenv("IRSA_ROLE_NAME", "test-IRSAServiceRole")
    
    eks_client = boto3.client("eks", region_name=aws_region)
    iam_client = boto3.client("iam", region_name=aws_region)
    
    # Get EKS cluster info and extract the OIDC issuer URL
    cluster_info = eks_client.describe_cluster(name=cluster_name)
    oidc_issuer_url = cluster_info['cluster']['identity']['oidc']['issuer']
    # Remove the protocol to form the provider identifier
    oidc_provider = oidc_issuer_url.replace("https://", "")
    
    # Form the new provider ARN
    provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/{oidc_provider}"
    
    # List and delete all existing OIDC providers
    providers = iam_client.list_open_id_connect_providers()['OpenIDConnectProviderList']
    for provider in providers:
        try:
            iam_client.delete_open_id_connect_provider(OpenIDConnectProviderArn=provider['Arn'])
            print("Deleted OIDC provider:", provider['Arn'])
        except Exception as e:
            print(f"Error deleting provider {provider['Arn']}: {str(e)}")
    
    # Create a new OIDC provider
    try:
        create_response = iam_client.create_open_id_connect_provider(
            Url=oidc_issuer_url,
            ClientIDList=["sts.amazonaws.com"],
            ThumbprintList=["9e99a48a9960b14926bb7f3b02e22da0afd8c30a"]
        )
        print("OIDC provider created:", create_response)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error creating OIDC provider: {str(e)}")
        }
    
    # Build the trust policy with the new OIDC provider ARN
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": provider_arn
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
        # Update the IRSA role's trust policy
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
                "oidc_provider": oidc_provider,
                "oidc_provider_arn": provider_arn
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error updating IRSA role: {str(e)}")
        }