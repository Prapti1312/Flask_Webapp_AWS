from pymysql import connections
import os
import boto3
from config import *

output = {}
table = 'registration_table';

def establish_connection(obj):
    db_conn = connections.Connection(
        host=obj.get('host'),
        user=obj.get('user'),
        port=obj.get('port'),
        password=obj.get('password'),
        db=obj.get('db')
    )
    return db_conn
 



