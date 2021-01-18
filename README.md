# ShellS3AWS-LoadDynamoTable_4010
Uses Python3 Boto3 to create a "shell" for interacting with and managing AWS S3 buckets. Also, a second part uses the same language and library to create, load, and manipulate DynamoDB tables (Cloud Computing course A1)

# Info

- Name: Mitchell Van Braeckel
- Student ID: 1002297
- Course: CIS*4010
- Assignment: 1
- Brief: CLI AWS S3 Shell Program + AWS DynamoDB Load and Scan/Query Tables
- Due: (Extended) Wed Oct 14, 2020

## General

- All Python modules required (`pip install <import-package>`)
  - import boto3
  - import csv
  - import configparser
  - import os
  - import re
  - import sys
  - import time
  - from boto3.dynamodb.conditions import Key, Attr
  - from decimal import *

- For all appropriate commands:
  - I print usage statements in the program where appropriate for errors, but I don't specify 'py' or 'python3' or whatever in case someone needs to use something else when starting the Python script
  - All dir/file location paths should work for absolute and relative paths
  - All dir/file location paths should work for multi-level chaining

- Generally, I error check a lot, so most things won't break the program
  - You can search in any file for the following error messages `"Error` or `"ERROR` or `[ERROR]` to finderror messages I made
    - `"Error` standard I caught it starting
    - `"ERROR` exit type error message
    - `[ERROR]` is the `print_error` template starting

- DISCLAIMER: I received an extension to Wed Oct 14 2020 11:59:59 PM
  - Please email me at `mvanbrae@uoguelph.ca` if there are any issues with my submission (deadline, code, comments, understanding, how to run, etc.)

## Part 1: `awsS3Shell.py`

- Basic Commands and Flags NOT Handled
  - I think I covered everything (check usage statement on each command (ie. by sending too many args), each at least has a stub)

- Extra Commands or Flags
  - Not sure if I did anything extra for commands or flags, but I included file/content type and size of bucket (for `ls -l`)
  - I also have implemented absolute and relative path for all appropriate commands, as well as multi-level chaining

- Error conditions
  - All the basic required stuff
  - If you search for `print_error` you can see everything I caught and printed myself
    - Similarly, searching for `sys.exit` you can see every time where I exit the program myself after finding an error (sometimes I display err msg using this)
  - Generally, I error check a lot, so most things won't break the program

- Comments/Instructions for the Marker
  - See `awsS3Shell.py` for my notes about it (more detailed than this README, it is located top of the file with header comment)
  - I comment a lot, so you can use that to look for things I did, etc.
  - See `import` section for everything you need to `pip install` specifically for this file

  - `config.ini`
    - Requires proper AWS credentials (that are not expired) with sufficient permissions
      - AccessKey
      - SecretKey
      - SessionToken
      - Region

- `Usage: py awsS3Shell.py`
  - `Usage: login <optional-username>`
  - `Usage: (logout|quit|exit)`
    - Either of those 3 commands all work
  - `Usage: mkbucket <s3-bucket-name>`
  - `Usage: ls <-l>`
  - `Usage: cd <~, .., dir-name>`
    - NOTE: this is general base case acceptance, but I have implemented multi-level stuff (for abs and rel paths) (eg. `cd ../folder-a/folder-b`)
  - `Usage: mkdir <dir>`
  - `Usage: rmdir <dir>`
  - `Usage: upload <local-filename-source> <s3-object-name-destination>`
  - `Usage: download <s3-object-name-source> <local-filename-destination>`
  - `Usage: cp <s3-object-name-source> <s3-object-name-destination>`
  - `mv` command uses `cp` command and has same usage and other error messages (because we copy, then delete source)
    - `Usage: mv <s3-object-name-source> <s3-object-name-destination>` would be the difference if I made it specific
  - `Usage: rm <s3-object-name>`

## Part 2

Q1: `loadTable.py`

- Primary (Partition/HASH) Key: 'id' (the row number of the CSV file, ie. starts at 1)
- Sort (RANGE) Key: 'commodity' (the commodity in the table is the commodity code)
- Field/Attribute Names and Types: (where 'row' is an array of strings, representing a row in the CSV)
  - 'id': row_id
  - 'commodity': row[0]
  - 'variable': row[1]
  - 'year': int(row[2])
  - 'units': row[3]
  - 'mfactor': int(row[4])
  - 'value': Decimal(row[5]

- `encodings.csv` loaded by `loadTable.py`?
  - NO, see `loadEncodingsTable.py` supplementary script below

- `Usage: py loadTable.py <file-name.csv> <table-name>`
  - CSV file name and table name are optional
  - Both CSV file name and table name must be included together, or both absent
  - If no command line arguments, user is asked to input CSV file name then table name using prompts:
    - `"Please enter CSV file name: "`
    - `"Please enter table name: "`
  
Supplementary script `loadEncodingsTable.py`

- See `loadTable.py` for referenced notes, because `loadEncodingsTable.py` is very similar and used it as basis

- **NOTE**: Not used because didn't know it was worth 1 mark until too late (when I looked at submission marking scheme right before submitting)
  - Instead, `queryOECD.py` just loads the data straight from CSV

- Primary (Partition/HASH) Key: 'code' (the commodity code, ie. not the label 'Wheat' but the encoding code 'WT')
- Sort (RANGE) Key: does not have one
- Field/Attribute Names and Types: (where 'row' is an array of strings, representing a row in the CSV)
  - 'code': row[0]
  - 'label': row[1]
  - 'field': row[2]

- `Usage: py loadEncodingsTable.py`
  - Make sure the CSV file `encodings.csv` exists in same folder as the script and that a AWS DynamoDB table with name `encodings` doesn't already exist
    - NOTE: hardcoded CSV filename as `encodings.csv`
    - NOTE: hardcoded AWS DynamoDB table name as `encodings`

Q2: `queryOECD.py`

- encodings table read in by this program?
  - NO, but see `loadEncodingsTable.py` supplementary script above for creating and loading the table
  - NOTE: uses hardcoded `encodings.csv` that must be in the same folder as the script

- `Usage: py queryOECD.py`
  - NOTE: no actual command line argument checking or usage statement (forgot to do the command line argument stuff for this program, only noticing now when creating a proper `README.md`)
  - Only works via user input prompt for commodity
    - `"Commodity: "`
    - NOTE: this assumes perfect user input for commodity code or label
      - ie. it is case sensitive for commodity code/label input
  - NOTE: requires the 4 tables: `northamerica`, `canada`, `usa`, and `mexico` to exist already

Error Conditions

- All the basic required stuff
- If you search for `"Error` or `"ERROR` or `[ERROR]` you can see everything I caught and printed myself
  - Similarly, searching for `sys.exit` you can see every time where I exit the program myself after finding an error (sometimes I display err msg using this)
  - Honestly, searching `print(` is probably good enough
    - Although I do print some extra stuff just to see processes of what's going on
      - For example, Q1 I print creating table and table finished creating, as well as populating table (from CSV), items being added, when it finishes including number of items added and seconds elapsed to add them all (I add in batches by the way)
      - For example Q2, print some things like the tables that already exist (so we can manually see if the 4 tables we need exist) and the commodity encoding code (see what key was, or what code key label referred too, or None if bad input)
- Generally, I error check a lot, so most things won't break the program

Comments/Instructions for the Marker

- See `loadTable.py` for my notes about it (located top of file with header comment)
  - I comment a lot, so you can use that to look for things I did, etc.
  - See `import` section for everything you need to `pip install` specifically for this file

- See `loadTable.py` for referenced notes, because `loadEncodingsTable.py` is very similar and used it as basis
  - Comments and imports (besides code) are VERY similar to `loadTable.py` and mainly only the header comments is different

- See `queryOECD.py` for my notes about it (located top of file with header comment)
  - I comment a lot, so you can use that to look for things I did, etc.
  - See `import` section for everything you need to `pip install` specifically for this file
