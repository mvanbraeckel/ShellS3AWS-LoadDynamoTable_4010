#!/usr/bin/env python

'''
@author : Mitchell Van Braeckel
@id : 1002297
@date : 10/10/2020
@version : python 3.8-32 / python 3.8.5
@course : CIS*4010 Cloud Computing
@brief : A1 Part 2 - AWS DynamoDB ; Q2 - Query OECD

@note :
    Description: There are many CSV files containing info from the OECD about agricultural production, each for various regions around the world.
        Queries all 4 tables (northamerica, canada, usa, mexico -table names) based on a commodity (code key or label),
        looking for all common variables between CAN, USA, and MEX, outputting all results (for all years) in a table,
        then output the specific NA definition 'hit' results and probable conclusion for NA definition per variable,
        as well as an overall conclusion for NA definition

        NOTE: forgot to add ability to specify commodity as cmd line arg instead of STDIN

        NOTE: assume year range is 2010 to 2029 (inclusive)
        NOTE: assume perfect user input for commodity and variables
            - however, if input commodity that's not a valid commodity code or label, exits program with error message
        NOTE: NA definition hit refers to if the calculated sum from different tables of CAN, USA, MEX are equal to that of NA (CAN+USA, CAN+USA+MEX, or Neither)
'''

'''
    IMPROVEMENT: Use 'encodings' table instead of the CSV file
'''

############################################# IMPORTS #############################################

# IMPORTS - 'pip install <import-package>'
import boto3
import csv
import sys
from boto3.dynamodb.conditions import Key, Attr

############################################ CONSTANTS ############################################

# TABLE CONSTANTS
NORTH_AMERICA = "northamerica"
CANADA = "canada"
USA = "usa"
MEXICO = "mexico"
TABLE_LIST = [NORTH_AMERICA, CANADA, USA, MEXICO]
YEAR_RANGE = range(2010, 2030)

# OTHER CONSTANTS
OUTPUT_FORMAT = "{:<8}{:<18}{:<18}{:<18}{:<18}{:<18}{:<18}{:<10}"
ENCODINGS_CSV = "encodings.csv"
#ENCODINGS_TABLE_NAME = "encodings"
USAGE_STATEMENT = "Usage: py queryOECD.py <commodity-code|commodity-label>"

############################## STATE VARIABLES, INITIALIZATION, MAIN ##############################

# MAIN - Declares global vars and state here, then ask for commodity (check both key/label),
#           look for all common variables between CAN, USA, and MEX, outputting all results (for all years) in a table,
#           then output the specific NA definition 'hit' results and probable conclusion for NA definition
def main():
    #globals
    global dynamodb_client
    global dynamodb_resource
    global na_table
    global canada_table
    global usa_table
    global mexico_table
    global total_can_usa
    global total_can_usa_mex
    global total_neither

    # ========== ARGUMENTS ==========

    # Collect command line arguments when executing this python script
    argc = len(sys.argv)
    bad_usage_flag = False
    
    # Check #of args (deal with it later tho)
    # 1 optional arg for commodity, otherwise prompt user for it
    if argc > 2:
        bad_usage_flag = True
        print("Error: Too many arguments.")
    
    # Exit with usage statement if flag has been triggered for any reason
    if bad_usage_flag:
        sys.exit(USAGE_STATEMENT)

    # ========== AWS DYNAMO DB ==========

    # Init AWS DynamoDB client and resource (NOTE: these are global)
    dynamodb_client = boto3.client("dynamodb")
    dynamodb_resource = boto3.resource("dynamodb")

    # Validate AWS DynamoDB credentials (by testing if 'list_tables()' works)
    try:
        dynamodb_client.list_tables()
    except Exception as e:
        print("Error: Invalid or expired credentials (or insufficient permissions to call 'list_tables()')")
        sys.exit(f"[ERROR] {e}")

    # Check the 4 tables exist, then get them all
    err_output = ""
    table_list = dynamodb_client.list_tables()['TableNames']

    print(f"Existing Tables: {table_list}")

    for t in TABLE_LIST:
        if t not in table_list:
            err_output += f"Error: Invalid table name '{t}' - table does not exist.\n"
    
    # Print all tables that did not exist, then exit
    if err_output != "":
        print(err_output.strip("\n"))
        sys.exit("ERROR: Terminating program because unable to get table that does not exist.")

    # Get all tables (after checking they exist) (NOTE: these are global)
    na_table = dynamodb_resource.Table(NORTH_AMERICA)
    canada_table = dynamodb_resource.Table(CANADA)
    usa_table = dynamodb_resource.Table(USA)
    mexico_table = dynamodb_resource.Table(MEXICO)

    # Open the encodings CSV file and read its contents
    commodity_encodings_dict = {}
    variable_encodings_dict = {}
    with open(ENCODINGS_CSV, "r", newline='') as csv_file:
        csv_content = csv.reader(csv_file, delimiter=',')

        # if field is var or commodity, set a key-value pair between code and label (in the respective map)
        for row in csv_content:
            if row[2] == "variable":
                variable_encodings_dict[row[0]] = row[1]
            elif row[2] == "commodity":
                commodity_encodings_dict[row[0]] = row[1]
    csv_file.close()

    # Check args for commodity now, otherwise prompt user
    if argc == 2:
        commodity_input = sys.argv[1]
    else:
        # Ask user for commodity
        commodity_input = input("Commodity: ").strip()
    
    # Check if input exists as code key, otherwise try to convert assumed label to code key (if not a label, code will be None after)
    if commodity_input.upper() in commodity_encodings_dict:
        commodity_code = commodity_input.upper()
    else:
        commodity_code = convert_dict_label_to_code_key(commodity_input, commodity_encodings_dict)

    # Check if commodity found a code or None
    print(f"ENCODING: {commodity_code}")
    if commodity_code is None:
        print(f"Error: Commodity '{commodity_input}' was not found.")
        sys.exit("ERROR: Terminating program because input does not exist as an encoding commodity code or label.")

    # Init total accumulators for each category
    total_can_usa = 0
    total_can_usa_mex = 0
    total_neither = 0

    # iterate through each variable and analyze data (if applicable)
    for var in variable_encodings_dict.keys():
        if is_common_variable(commodity_code, var):
            output_table(commodity_code, var, variable_encodings_dict, commodity_encodings_dict)

    # Determine the NA definition for this variable based on #of 'hits' per year
    max_hits = max(total_can_usa, total_can_usa_mex, total_neither)
    if total_can_usa == max_hits:
        na_defn = "CAN+USA"
    elif total_can_usa_mex == max_hits:
        na_defn = "CAN+USA+MEX"
    else:
        na_defn = "Neither"

    print(f"Overall North America Definition Results: {total_can_usa} CAN+USA, {total_can_usa_mex} CAN+USA+MEX, {total_neither} Neither")
    print(f"Conclusion for all {commodity_encodings_dict[commodity_code]} variables = {na_defn}\n")

############################################ FUNCTIONS ############################################

# Converts the label of a dict into its code key, returns None if not a label
def convert_dict_label_to_code_key(label, encodings_dict):
    # Get the key of the label if the label exists in the dict as a value
    if label in list(encodings_dict.values()):
        return list(encodings_dict.keys())[list(encodings_dict.values()).index(label)]
    else:
        return None

# Check if a commodity code + variable is common across all 4 tables, return true if it is
def is_common_variable(commodity_code, variable):
    return (has_commodity_and_variable(na_table, commodity_code, variable) and
        has_commodity_and_variable(canada_table, commodity_code, variable) and
        has_commodity_and_variable(usa_table, commodity_code, variable) and
        has_commodity_and_variable(mexico_table, commodity_code, variable))

# Check if a table has data for commodity code + variable (ie. scan table), returns true if at least 1 item is found
def has_commodity_and_variable(table, commodity_code, variable):
    response = table.scan(
        FilterExpression = Attr('commodity').eq(commodity_code) & Attr('variable').eq(variable)
    )
    return response['Count'] > 0

# Retrieves and outputs table data based on commodity and variable and analyze for NA definition
def output_table(commodity_code, variable, variable_encodings_dict, commodity_encodings_dict):
    # Bring in globals to modify
    global total_can_usa
    global total_can_usa_mex
    global total_neither

    # Init local accumulators
    temp_can_usa = 0
    temp_can_usa_mex = 0
    temp_neither = 0

    # Print table headers: common variable (for commodity code) across all 4 tables, and table column names
    print(f"Variable: {variable_encodings_dict[variable]}")
    print(OUTPUT_FORMAT.format("Year", "North America", "Canada", "USA", "Mexico", "CAN+USA", "CAN+USA+MEX", "NA Defn"))

    # Retrieve all data, from all years (ie. the items from the scan)
    na_scan_data = na_table.scan(
        FilterExpression=Attr('commodity').eq(commodity_code) & Attr('variable').eq(variable)
    )['Items']
    can_scan_data = canada_table.scan(
        FilterExpression=Attr('commodity').eq(commodity_code) & Attr('variable').eq(variable)
    )['Items']
    usa_scan_data = usa_table.scan(
        FilterExpression=Attr('commodity').eq(commodity_code) & Attr('variable').eq(variable)
    )['Items']
    mex_scan_data = mexico_table.scan(
        FilterExpression=Attr('commodity').eq(commodity_code) & Attr('variable').eq(variable)
    )['Items']

    # Sort each scan data by key
    na_scan_data.sort(key=data_sort)
    can_scan_data.sort(key=data_sort)
    usa_scan_data.sort(key=data_sort)
    mex_scan_data.sort(key=data_sort)

    # Analyze data
    for year in YEAR_RANGE:
        # For each relevant year, calculate total value using multiplication factor
        i = year - 2010
        na_value = na_scan_data[i]['value'] * (10**na_scan_data[i]['mfactor'])
        can_value = can_scan_data[i]['value'] * (10**can_scan_data[i]['mfactor'])
        usa_value = usa_scan_data[i]['value'] * (10**usa_scan_data[i]['mfactor'])
        mex_value = mex_scan_data[i]['value'] * (10**mex_scan_data[i]['mfactor'])

        # Calc temp sums for the CAN+USA and CAN+USA+MEX columns
        temp_can_usa_value = can_value + usa_value
        temp_can_usa_mex_value = can_value + usa_value + mex_value

        # Determine OECD def of NA, by checking if the temp calc sums from scan data calc values are equivalent to CAN+USA sum, CAN+USA+MEX sum, or Neither
        # Note: accumulate the #of accurate NA def 'hits'
        if temp_can_usa_value == na_value:
            na_defn = 'CAN+USA'
            temp_can_usa += 1
        elif temp_can_usa_mex_value == na_value:
            na_defn = 'CAN+USA+MEX'
            temp_can_usa_mex += 1
        else:
            na_defn = 'Neither'
            temp_neither += 1

        # Print table row for current year
        print(OUTPUT_FORMAT.format(year, na_value, can_value, usa_value, mex_value, temp_can_usa_value, temp_can_usa_mex_value, na_defn))

    # Determine the NA definition for this variable based on #of 'hits' per year
    max_hits = max(temp_can_usa, temp_can_usa_mex, temp_neither)
    if temp_can_usa == max_hits:
        na_defn = "CAN+USA"
    elif temp_can_usa_mex == max_hits:
        na_defn = "CAN+USA+MEX"
    else:
        na_defn = "Neither"

    print(f"North America Definition Results: {temp_can_usa} CAN+USA, {temp_can_usa_mex} CAN+USA+MEX, {temp_neither} Neither")
    print(f"Therefore we can conclude North America = {na_defn}\n")

    # Accumulate global totals using temp local accumulators for NA definition 'hits'
    total_can_usa += temp_can_usa
    total_can_usa_mex += temp_can_usa_mex
    total_neither += temp_neither

# Sorter Helper for queried data by year
def data_sort(elem):
    return elem['year']

###################################################################################################

main()
