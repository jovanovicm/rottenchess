import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    nat_response = ec2.describe_nat_gateways()
    nat_gateways = nat_response.get('NatGateways', [])
    
    deleted_nat_gateways = []
    for nat in nat_gateways:
        nat_id = nat.get('NatGatewayId')
        try:
            ec2.delete_nat_gateway(NatGatewayId=nat_id)
            print(f"Deletion initiated for NAT gateway {nat_id}")
            deleted_nat_gateways.append(nat_id)
        except Exception as e:
            print(f"Error deleting NAT gateway {nat_id}: {e}")
    
    addresses_response = ec2.describe_addresses(
        Filters=[{'Name': 'domain', 'Values': ['vpc']}]
    )
    released_ips = []
    for address in addresses_response.get('Addresses', []):
        allocation_id = address.get('AllocationId')
        try:
            ec2.release_address(AllocationId=allocation_id)
            print(f"Released Elastic IP with allocation ID {allocation_id}")
            released_ips.append(allocation_id)
        except Exception as e:
            print(f"Error releasing Elastic IP {allocation_id}: {e}")
    
    return {
        'statusCode': 200,
        'deletedNatGateways': deleted_nat_gateways,
        'releasedIPs': released_ips
    }