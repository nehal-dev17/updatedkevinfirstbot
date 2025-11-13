import boto3
import botocore
import os
from typing import Optional

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
CONVERSATION_TABLE = os.getenv("DDB_TABLE_CONVERSATIONS", "wellness_conversation")
PROFILE_TABLE = os.getenv("DDB_TABLE_PROFILES", "wellness_profile")

# Initialize AWS session and DynamoDB resource
_session: Optional[boto3.Session] = None
_dynamodb = None


def get_session():
    """Get or create AWS session"""
    global _session
    if _session is None:
        try:
            _session = boto3.Session(region_name=AWS_REGION)
        except Exception as e:
            raise RuntimeError(f"Failed to create AWS session: {str(e)}")
    return _session


def get_dynamodb():
    """Get or create DynamoDB resource"""
    global _dynamodb
    if _dynamodb is None:
        session = get_session()
        _dynamodb = session.resource('dynamodb')
    return _dynamodb


def get_conversations_table():
    """Get conversations table"""
    dynamodb = get_dynamodb()
    return dynamodb.Table(CONVERSATION_TABLE)


def get_profiles_table():
    """Get profiles table"""
    dynamodb = get_dynamodb()
    return dynamodb.Table(PROFILE_TABLE)


def init_db():
    """Initialize DynamoDB tables if they don't exist"""
    session = get_session()
    client = session.client('dynamodb')
    
    try:
        existing_tables = client.list_tables()['TableNames']
    except botocore.exceptions.NoCredentialsError:
        raise RuntimeError(
            "AWS credentials not found. Please set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY in your .env file or configure AWS credentials."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to list DynamoDB tables: {str(e)}")

    # Create conversations table
    if CONVERSATION_TABLE not in existing_tables:
        try:
            client.create_table(
                TableName=CONVERSATION_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'N'},  # Changed to Number
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {'Key': 'Application', 'Value': 'WellnessCompanion'},
                    {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'production')}
                ]
            )
            print(f"Creating table: {CONVERSATION_TABLE}")
            waiter = client.get_waiter('table_exists')
            waiter.wait(TableName=CONVERSATION_TABLE, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
            print(f"✓ Table created: {CONVERSATION_TABLE}")
        except client.exceptions.ResourceInUseException:
            print(f"Table already exists: {CONVERSATION_TABLE}")
        except Exception as e:
            raise RuntimeError(f"Failed to create conversations table: {str(e)}")

    # Create profiles table
    if PROFILE_TABLE not in existing_tables:
        try:
            client.create_table(
                TableName=PROFILE_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'N'}  # Changed to Number
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {'Key': 'Application', 'Value': 'WellnessCompanion'},
                    {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'production')}
                ]
            )
            print(f"Creating table: {PROFILE_TABLE}")
            waiter = client.get_waiter('table_exists')
            waiter.wait(TableName=PROFILE_TABLE, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
            print(f"✓ Table created: {PROFILE_TABLE}")
        except client.exceptions.ResourceInUseException:
            print(f"Table already exists: {PROFILE_TABLE}")
        except Exception as e:
            raise RuntimeError(f"Failed to create profiles table: {str(e)}")


def check_connection():
    """Check if DynamoDB connection is working"""
    try:
        client = get_session().client('dynamodb')
        client.list_tables()
        return True
    except Exception:
        return False