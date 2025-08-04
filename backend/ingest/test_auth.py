import boto3

session = boto3.Session()
credentials = session.get_credentials()

print("Access Key:", credentials.access_key[:10] + "..." if credentials.access_key else None)
print("Has Secret Key:", bool(credentials.secret_key))
print("Session Token:", bool(credentials.token))

# Get the identity
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print("\nWho am I:", identity['Arn'])