import boto3
import os

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name=os.getenv('AWS_REGION'))

    PUBLIC_SUBNET_ID = os.getenv('PUBLIC_SUBNET_ID')
    PRIVATE_ROUTE_TABLE_ID = os.getenv('PRIVATE_ROUTE_TABLE_ID')
    
    eip_response = ec2.allocate_address(Domain='vpc')
    allocation_id = eip_response['AllocationId']

    nat_response = ec2.create_nat_gateway(
        SubnetId=PUBLIC_SUBNET_ID,
        AllocationId=allocation_id
    )
    nat_gateway_id = nat_response['NatGateway']['NatGatewayId']
    
    # Wait for the NAT gateway to become available
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    print(f"NAT gateway {nat_gateway_id} is now available.")

    try:
        ec2.create_route(
            RouteTableId=PRIVATE_ROUTE_TABLE_ID,
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=nat_gateway_id
        )
        print(f"Default route created in route table {PRIVATE_ROUTE_TABLE_ID} pointing to NAT gateway {nat_gateway_id}")
    except Exception as e:
        if 'RouteAlreadyExists' in str(e):
            try:
                ec2.replace_route(
                    RouteTableId=PRIVATE_ROUTE_TABLE_ID,
                    DestinationCidrBlock='0.0.0.0/0',
                    NatGatewayId=nat_gateway_id
                )
                print(f"Default route in route table {PRIVATE_ROUTE_TABLE_ID} replaced with NAT gateway {nat_gateway_id}")
            except Exception as ex:
                print(f"Error replacing route in route table {PRIVATE_ROUTE_TABLE_ID}: {ex}")
        else:
            print(f"Error updating route table {PRIVATE_ROUTE_TABLE_ID}: {e}")
    
    return {
        'statusCode': 200,
        'natGatewayId': nat_gateway_id,
        'allocationId': allocation_id
    }