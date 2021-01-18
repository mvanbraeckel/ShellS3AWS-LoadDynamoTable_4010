#!/usr/bin/env python

'''
@author : Mitchell Van Braeckel
@id : 1002297
@date : 10/10/2020
@version : python 3.8-32 / python 3.8.5
@course : CIS*4010 Cloud Computing
@brief : A1 Part 2 - AWS DynamoDB ; Q1 - Table Creation from CSV (loading encodings CSV)

@note :
    Description: There are many CSV files containing info from the OECD about agricultural production, each for various regions around the world.
        NOTE: separated this script to load the encodings CSV to an AWS DynamoDB Table
        NOTE: does all the same file handling and is very similar to original loadTable.py
            - but hardcoded 'encodings.csv' file name and 'encodings' table name
            - of course, different structure to table (only has HASH partition key using 'code')

        NOTE: this file may not be used because I didn't know until it was too late to switch it...
'''

############################################# IMPORTS #############################################

# IMPORTS - 'pip install <import-package>'
import boto3
import csv
import os
import re
import sys
import time
from decimal import *

############################################ CONSTANTS ############################################

USAGE_STATEMENT = "Usage: py loadEncodingsTable.py"
CSV_FILENAME = "encodings.csv"
TABLE_NAME = "encodings"

############################## STATE VARIABLES, INITIALIZATION, MAIN ##############################

# MAIN - Declares global vars and state here, then load encodings CSV into AWS DynamoDB Table after validating file/table names and checking for errors
def main():
    #globals
    global dynamodb_client
    global dynamodb_resource

    # ========== ARGUMENTS ==========

    # Collect command line arguments when executing this python script
    argc = len(sys.argv)
    bad_usage_flag = False

    # Get hardcoded CSV file name and table name
    csv_filename = CSV_FILENAME
    table_name = TABLE_NAME
    
    # Check #of args
    if argc != 1:
        # Display err msg for too few args, but take what is possible
        bad_usage_flag = True
        print("Error: Too many arguments.")
    
    # Display all appropriate error messages regarding usage
    # NOTE: here, this is just to validate the hardcoded CSV file name and table name
    if not is_csv_fn_valid(csv_filename):
        # Note: also checks if file exists
        bad_usage_flag = True
    if not is_table_name_valid(table_name):
        bad_usage_flag = True
    
    # Exit with usage statement if flag has been triggered for any reason
    if bad_usage_flag:
        sys.exit(USAGE_STATEMENT)

    # ========== AWS DYNAMO DB ==========
    dynamodb_client = boto3.client("dynamodb")
    dynamodb_resource = boto3.resource("dynamodb")

    # Validate AWS DynamoDB credentials (by testing if 'list_tables()' works)
    try:
        dynamodb_client.list_tables()
    except Exception as e:
        print("Error: Invalid or expired credentials (or insufficient permissions to call 'list_tables()')")
        sys.exit(f"[ERROR] {e}")

    # Check if table already exists before attempting to create a new one, display err msg and exit if it does
    if table_exists(table_name):
        print(f"Error: Invalid table name '{table_name}' - table already exists.")
        sys.exit("ERROR: Terminating program because unable to create table with same name as an already existing table.")

    # Attempt to create the encodings table using given table name
    print("--Creating table... please wait...")
    try:
        table = create_dynamodb_encodings_table(table_name)
    except Exception as e:
        sys.exit(f"[ERROR] While creating table: {e}")
    # Attempt to wait for the table to finish creating and reach a successful state
    try:
        table.wait_until_exists()
    except Exception as e:
        sys.exit(f"[ERROR] While waiting for table to finish creating: {e}")
    print("...Table created successfully--")
    
    # Attempt to open the CSV file and read its contents, putting each row into the encodings table in batches of items
    print("--Populating table... please wait...")
    try:
        load_csv_into_encodings_table(csv_filename, table)
    except Exception as e:
        sys.exit(f"[ERROR] While loading CSV contents to table: {e}")
    print ("...Table populated--")

############################################ FUNCTIONS ############################################

# Checks CSV file name - returns true if valid, false otherwise, and prints info about why file name is invalid
def is_csv_fn_valid(csv_fn):
    valid_flag = True
    if len(csv_fn) < 5 or not csv_fn.endswith(".csv"):
        valid_flag = False
        print(f"Error: Invalid CSV file name '{csv_fn}' - must be at least 4 characters long and end with '.csv'.")
    elif not os.path.isfile(csv_fn):
        # Check if file exists
        valid_flag = False
        print(f"Error: Invalid CSV file name '{csv_fn}' - file does not exist.")
    return valid_flag

# Checks table name - returns true if valid, false otherwise, and prints info about why file name is invalid
def is_table_name_valid(table_name):
    valid_flag = True
    if len(table_name) < 3 or len(table_name) > 255:
        valid_flag = False
        print(f"Error: Invalid table name '{table_name}' - must be between 3 and 255 characters long (inclusive).")
    if re.search("[^a-zA-Z0-9_\\-\\.]+", table_name) != None:
        valid_flag = False
        print(f"Error: Invalid table name '{table_name}' - table names can consist only of alphanumeric, underscores (_), dashes/hyphens (-), and dots/periods (.).")
    return valid_flag

# Checks if table already exists - returns true if it does, otherwise false
def table_exists(table_name):
    tables = dynamodb_client.list_tables()['TableNames']
    return (table_name in tables)

# Creates the encodings table using given table name, returns the result
# Notice, HASH partition key = 'code' of encoding
# Notice, no RANGE sort key
# Notice, safeguard provisioning and billing
def create_dynamodb_encodings_table(table_name):
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'code',
                'KeyType': 'HASH'   #Partition key
            }
            # no sort key
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'code',
                'AttributeType': 'S'    #String
            }
            # no sort key
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    return table

# Loads given CSV contents and puts each row contents into the created encodings table in batches of items
def load_csv_into_encodings_table(csv_filename, table):
    # Also track time elapsed
    start_time = time.time()

    # Open the CSV file and read its contents
    with open(csv_filename, "r", newline='') as csv_file:
        csv_content = csv.reader(csv_file, delimiter=',')
        
        # Put each row from CSV file into the table as an item (in batches)
        with table.batch_writer() as batch:
            # Track row ID#
            row_id = 0
            for row in csv_content:
                row_id += 1
                print(f"-adding row item: {row_id} {row[0]} {row[1]} {row[2]}")
                
                batch.put_item(
                    Item={
                        'code': row[0],
                        'label': row[1],
                        'field': row[2]
                    }
                )

        # # # NOTE: left for testing purposes (comment out above batch version if using this)
        # # Put each row from CSV file into the table as an item (one at a time)
        # # Track row ID#
        # row_id = 0
        # for row in csv_content:
        #     row_id += 1
        #     print(f"-adding row item: {row_id} {row[0]} {row[1]} {int(row[2])}")

        #     table.put_item(
        #         Item={
        #             'code': row[0],
        #             'label': row[1],
        #             'field': row[2]
        #         }
        #     )
    csv_file.close()

    # Display total number of items added and time elapsed
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"...finished adding {row_id} items in {elapsed_time} seconds...")

###################################################################################################

main()

# ##### FOLLOWING TUTORIAL #####
# ----- CREATING A TABLE ----- -(starting slide 17 of 'Storage_AWS_DynamoDB.pdf')
# ----- LOADING DATA FROM A JSON FILE INTO A TABLE ----- (starting slide 20 of 'Storage_AWS_DynamoDB.pdf')
# ----- QUERY OPERATION ----- (starting slide 28 of 'Storage_AWS_DynamoDB.pdf')
# ----- SCAN OPERATION ----- (starting slide 30 of 'Storage_AWS_DynamoDB.pdf')
# ----- CREATE ITEM OPERATION ----- (starting slide 33 of 'Storage_AWS_DynamoDB.pdf')
# ----- DELETE ITEM OPERATION ----- (starting slide 35 of 'Storage_AWS_DynamoDB.pdf')
