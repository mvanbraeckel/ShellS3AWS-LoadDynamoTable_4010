General
- N/A

Python Modules
- boto3
- python3
- AWS CLI
- The following Python Standard Libraries are used:
    - configparser
    - re
    - csv
    - time
    - os.path

Part 1: awsS3Shell.py Program

=== Basic Commands and Flags NOT Handled ===
- mv does not support moving whole directories (not sure if this was required)

=== Extra Commands or Flags ===
- cd supports multiple levels (e.g. cd ../dir1/dir2/..)
- all commands support local and absolute paths (where applicable)
    - this includes cd, mkdir/rmdir, rm/cp/mv, upload/download

=== Error Conditions ===
- all Error Actions and Messages specified in the assignment document are handled except for:
    - "You do not have permission to execute the command."
    - the program assumes the user has permission to access all buckets and objects

- login will fail under the following conditions:
    - more than 1 argument is passed
    - username does not exist in config.ini
    - AccessKey, SecretKey, or Region values are missing
    - unable to call list_buckets() with the given credentials

- cd will fail under the following conditions:
    - number of arguments passed is not 1
    - the bucket for the resulting path does not exist
    - the resulting directory does not exist or is a non-directory (i.e. file)

- mkbucket will fail under the following conditions:
    - number of arguments passed is not 1
    - bucket name is invalid according to AWS bucket naming guidelines
    - the bucket name already exists (either globally or under the user's AWS account)
    - creating a bucket while working directory is NOT root

- mkdir will fail under the following conditions:
    - number of arguments passed is not 1
    - user tries to create a directory at root (instead of a bucket)
    - the directory already exists

- rmdir will fail under the following conditions:
    - number of arguments passed is not 1
    - user tries to remove a directory at root
    - directory does not exist or is a non-directory (i.e. file)
    - directory is not empty

- rm will fail under the following conditions:
    - number of arguments passed is not 1
    - user tries to remove an object at root
    - file does not exist or is a directory

- cp will fail under the following conditions:
    - number of arguments passed is not 2
    - user tries to copy a bucket
    - user tries to copy an object into root
    - source object does not exist
    - user tries to copy a directory (not supported)

- mv will fail under the following conditions:
    - number of arguments passed is not 2
    - user tries to move a bucket
    - user tries to move an object into root
    - source object does not exist
    - user tries to move a directory (not supported)

- upload will fail under the following conditions:
    - number of arguments passed is not 2
    - local file with specified filename does not exist
    - user tries to upload to root

- download will fail under the following conditions:
    - number of arguments passed is not 2
    - local file with specified filename already exists
    - user tries to download a bucket

=== Comments/Instructions for the Marker ===
- shell may break or exhibit weird behavior if calling rmdir on a folder that the working directory is in
- dirs and files can have the same name
- directory and object names cannot have spaces
- spaces in arguments are not supported (e.g. mkdir "Test Folder")
- you can copy/move to a directory that doesn't exist
- config.ini should work without SessionToken but has not been tested as I don't have a non-educational AWS account to verify this
- regions other than us-east-1 have not been tested
- arguments which accept absolute/local paths view the following as equivalent: 'dir1/dir2' and '/dir1/dir2/'
    - any leading or trailing '/' are ignored
- when calling mv, cp, or upload, the destination argument must be the resulting name (does not accept a directory like Linux does)

Part 2: DynamoDB

=== loadTable.py Program ===
- Running this program: run without any command line arguments (inputs through STDIN)
- Primary Key: ID (Partition Key) + Commodity (Sort Key)
- Field/Attribute Names: ID, Commodity, Variable, Year, Units, Mfactor, Value
- encodings.csv loaded by loadTable.py: no
- if no: program that does and how it is run
    - N/A (queryOECD.py will read the csv file)

=== queryOECD.py Program ===
- Running this program: run without any command line arguments (inputs through STDIN)
- encodings table read in by this program: yes

=== Error Conditions ===
- loadTable.py and queryOECD.py will fail on start if the AWS credentials are invalid
- loadTable.py will fail if the table name already exists
- queryOECD.py will fail if the inputted commodity does not exist

Comments/Instructions for the Marker
- encodings.csv MUST be in the same directory as queryOECD.py (it is not loaded into a table)
- queryOECD.py assumes the tables are named as follows:
    - northamerica
    - canada
    - usa
    - mexico