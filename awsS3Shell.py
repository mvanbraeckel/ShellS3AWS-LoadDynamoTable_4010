#!/usr/bin/env python

'''
@author : Mitchell Van Braeckel
@id : 1002297
@date : 10/09/2020
@version : python 3.8-32 / python 3.8.5
@course : CIS*4010 Cloud Computing
@brief : A1 Part 1 - AWS S3 Storage ; Python file for CLI

@note :
    Description: Use AWS Boto3 SDK for Python to create an "S3 Shell" that allows user to manipulate S3 buckets and objects as if they were actually a file system:
        See the following required functions:
        a) login <username>
        --> logging in first logs out, then tries to login with new user ==> so if new user fails to login, nobody will be logged in (just need to successfully login to fix this)
        b) logout/quit/exit
        c) mkbucket <S3 bucket name>
        d) ls <-l>
        --> added bucket size to -l flag and say bucket file/content type is 's3-bucket'
        e) dir-like commands - pwd, cd <~ or .. or dir name>, mkdir, rmdir
        --> pwd displayed always as part of CLI prompt
        --> added relative or abs paths, and multi-level commands for cd
        --> mkdir only meets requirements and a little bit of extra multi-level pathing, although a little odd (it only creates using key and not any in-between necessary folders)
            --> folders inside folders have their name/key displayed in relevance to the bucket they are both from
            --> ls -l can let you see the current folder (where you just called the command), but name/key is just '.'
        f) types of copy - upload <local filename> <S3 obj name>, download <S3 obj name> <local filename>, cp <S3 obj name> <S3 obj name>
        g) mv <S3 obj name> <S3 obj name>
        h) rm <obj name>

    Error Actions & Messages: For the following error conditions, the shell should print out an appropriate error message, not attempt the command, and continue to wait for another command:
        - Trying to execute a command without logging in first
        - Using a command that is not listed here
        - The command does not have the appropriate number of parameters
        - Either a bucket name or object name is incorrect (i.e. the bucket or object does not exist)
        - You do not have permission to execute the command, eg. if you try to mkbucket and the bucket name is not unique, the command will fail

        NOTE: Most (if not all) errors are handled so the program should not terminate or crash
        --> This includes the mentioned things for extra bonus marks
        --> This includes checking if things properly exist before doing stuff (for almost everything)
            --> Sometimes behaves a little odd though, ie. it's there but cannot see it unless each of its parents also exist
    
    General Extra:
        - I think I got absolute and relative path for all of the things (at least the majority of them)
        - I also think I handle and catch pretty much every error that's likely to occur (as well as general safeguarding)
        - I handle and check session timeout before executing commands

        NOTE: I wasn't sure what it meant about S3 object in the general case, so I treated it as the S3 object(s) that weren't covered yet
        --> i.e. not bucket and not dir/folder objects
        --> it also uses rules like the others, eg. where you cannot manipulate root level adding or removing (unless you are making a bucket)
'''

# Won't do these because already working with no time
# TODO - Improvement: check files names with spaces and quotes (ie. let args have spaces if they do "" around it)
# TODO - Improvement: allow rm to work on buckets and/or object dir/folder
# TODO - Improvement: explcitly check if dest location (and all its parents exist)
# TODO - Improvement: add extra flags, eg. rmdir to remove folder and files, etc

############################################# IMPORTS #############################################

# IMPORTS - 'pip install <import-package>'
import boto3
import configparser
import os
import re

############################################ CONSTANTS ############################################

# CONFIG CONSTANTS
CONFIG_FILE = "config.ini"
DEFAULT = "DEFAULT"
ACCESS_KEY = "AccessKey"
SECRET_KEY = "SecretKey"
SESSION_TOKEN = "SessionToken"
REGION = "Region"

# DIRECTORY CONSTANTS
ROOT_DIR = ["s3:"]

# COMMAND CONSTANTS
LOGIN_CMD = "login"
TERMINATE_CMD_GROUP = ["logout", "quit", "exit"]
MKBUCKET_CMD = "mkbucket"
LS_CMD = "ls"
PWD_CMD = "pwd"
CD_CMD = "cd"
MKDIR_CMD = "mkdir"
RMDIR_CMD = "rmdir"
UPLOAD_CMD = "upload"
DOWNLOAD_CMD = "download"
CP_CMD = "cp"
MV_CMD = "mv"
RM_CMD = "rm"

############################## STATE VARIABLES, INITIALIZATION, MAIN ##############################

# MAIN - Declares global vars and state here, then runs the S3 Shell CLI program loop until user terminates
def main():
    global terminate_flag
    global session
    global s3_client
    global s3_resource
    global curr_wd
    global commands

    terminate_flag = False
    session = None
    s3_client = None
    s3_resource = None
    curr_wd = ROOT_DIR.copy()
    commands = {
        LOGIN_CMD: login,
        TERMINATE_CMD_GROUP[0]: set_terminate,
        TERMINATE_CMD_GROUP[1]: set_terminate,
        TERMINATE_CMD_GROUP[2]: set_terminate,
        MKBUCKET_CMD: mkbucket,
        LS_CMD: ls,
        PWD_CMD: pwd,
        CD_CMD: cd,
        MKDIR_CMD: mkdir,
        RMDIR_CMD: rmdir,
        UPLOAD_CMD: upload,
        DOWNLOAD_CMD: download,
        CP_CMD: cp,
        MV_CMD: mv,
        RM_CMD: rm
    }

    print("\n=== S3 Shell Started ===\n")

    # Continue to run S3 shell program until user exits/quits/logs out
    while not terminate_flag:
        # Display command line prompt, collect user command input (strip it, split on spaces) separately, removing empty items from arguments
        user_input = input(f"{get_pwd_string()}> ").strip().split(" ")
        cmd = user_input[0]
        args = filter_empty_strings(user_input)

        # Must login before using any commands other than to terminate S3 shell program
        # Display err msg if not logged in first, or command is invalid - execute valid commands
        # Check session is still valid before executing the command
        if cmd in commands.keys():
            if cmd != LOGIN_CMD and cmd not in TERMINATE_CMD_GROUP:
                if session is None:
                    print_error(cmd, "Must login first.")
                    continue
                else:
                    if not validate_session():
                        print_error(args[0], "Session Failure - AWS access credentials expired, please login again to continue.")
                        continue
            try:
                commands[cmd](args=args)
            except Exception as e:
                print_error(args[0], e)
                continue
        else:
            print_error(cmd, "Invalid command.")
            continue

    print("\n=== S3 Shell Stopped ===")

######################################## COMMAND FUNCTIONS ########################################

# a) Logs out signed-in user, if there is one, then attempts to login as specified user from config, DEFAULT otherwise
# --> Authenticates using config keys and region (and optional session token)
def login(args):
    # Bring in global vars (to be changed)
    global session
    global s3_client
    global s3_resource

    # Reset state
    session = None
    s3_client = None
    s3_resource = None

    # Parse config for auth credentials
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # Check for optional <username> arg, DEFAULT otherwise
    username = DEFAULT
    if len(args) > 2:
        print_error(args[0], "Usage: login <optional-username>")
        return
    elif len(args) == 2:
        username = args[1]

    # Display message for bad given username, then stop and fail login attempt
    try:
        config[username]
    except:
        print_error(args[0], f"Login Failed - AWS access credentials profile username '{username}' does not exist in config or is not configured properly.")
        return

    # Retrieve auth credentials from config for given username
    try:
        access_key = config[username][ACCESS_KEY]
        secret_key = config[username][SECRET_KEY]
        region = config[username][REGION]
    except:
        print_error(args[0], f"Login Failed - AWS access credentials profile username '{username}' configuration is invalid.")
        return
    # Retrieve optional session token from config separately if it exists
    try:
        session_token = config[username][SESSION_TOKEN]
    except:
        session_token = None

    # Create session using config credentials for DEFAULT or given username, using it to create a client and resource
    # When attempting to provision S3 session, client, and resource, display err msg and reset if err occurs
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region
        )
        s3_client = session.client("s3")
        s3_resource = session.resource("s3")
    except:
        print_error(args[0], f"Login Failed - AWS access credentials for profile username '{username}' are invalid.")
        session = None
        s3_client = None
        s3_resource = None
        return

    # Validate Credentials, display message for success and failure
    if not validate_session():
        session = None
        s3_client = None
        s3_resource = None
        print_error(args[0], "Session Failure - AWS access credentials invalid, expired, or insufficient permissions to call 'list_buckets()'.")
    else:
        print(f"{args[0]}: Successful session login using profile username '{username}'.")

# b) Sets the termination flag to terminate shell program (logout not required)
def set_terminate(args):
    # Check #of args
    if len(args) != 1:
        print_error(args[0], "Usage: (logout|quit|exit)")
        return

    global terminate_flag
    terminate_flag = True

# c) Makes S3 bucket at the "root" level of the "file system directory tree"
# Note: could improve by allowing optional region param??
def mkbucket(args):
    # Validate bucket name - check #of args, then for valid bucket name
    if len(args) != 2:
        print_error(args[0], "Usage: mkbucket <s3-bucket-name>")
        return
    
    bucket_name = args[1]
    bad_bucket_name_flag = False
    # Only allow new buckets in root dir
    if not is_root_dir():
        print_error(args[0], "Invalid location - must be in root directory to use this command (i.e. can only create buckets in root directory).")
        bad_bucket_name_flag = True
    # Must conform to S3 bucket name rules
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        print_error(args[0], "Invalid bucket name - Bucket names must be between 3 and 63 characters long (inclusive).")
        bad_bucket_name_flag = True
    if re.search("[^a-z0-9\\.\\-]+", bucket_name) != None:
        print_error(args[0], "Invalid bucket name - Bucket names can consist only of lowercase letters, numbers, dots/periods (.), and dashes/hyphens (-).")
        bad_bucket_name_flag = True
    if not bucket_name[0].isalnum() or not bucket_name[0].islower() or not bucket_name[len(bucket_name)-1].isalnum() or not bucket_name[len(bucket_name)-1].islower():
        print_error(args[0], "Invalid bucket name - Bucket names must begin and end with a letter or number.")
        bad_bucket_name_flag = True
    if re.search("[^0-9\\.]+", bucket_name) == None:
        print_error(args[0], "Invalid bucket name - Bucket names must not be formatted as an IP address, so they cannot only consist of numbers and dots/periods (.).")
        bad_bucket_name_flag = True
    if bucket_name[0:4] == "xn--":
        print_error(args[0], "Invalid bucket name - Bucket names cannot begin with 'xn--'.")
        bad_bucket_name_flag = True
    if re.search("\\.{2,}", bucket_name) != None:
        print_error(args[0], "Invalid bucket name - Bucket names cannot have consecutive dots/periods (.).")
        bad_bucket_name_flag = True
    if re.search("(\\-\\.)+", bucket_name) != None or re.search("(\\.\\-)+", bucket_name) != None:
        print_error(args[0], "Invalid bucket name - Bucket names cannot use dots/periods (.) adjacent to dashes/hyphens (-).")
        bad_bucket_name_flag = True
    # Check if user already has bucket with the given name
    if bucket_exists(bucket_name):
        print_error(args[0], f"Invalid bucket name - Bucket names must be unique, you already have a bucket with the name '{bucket_name}'.")
        bad_bucket_name_flag = True

    # Skip bucket creation attempt if name issue is already found
    if bad_bucket_name_flag:
        return

    # Bucket names must be unique, but we will catch and handle this (and any other errors) when attempting to create bucket
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except Exception as e:
        print_error(args[0], f"Bucket creation failure - cannot create bucket '{bucket_name}', most likely not globally unique.")
        print_error(args[0], e)
        return

# Displays S3 buckets (if root) or objects in a bucket, long form if '-l' optional flag is added (object name, size, file type, and creation date)
# Note: Displays paths using Unix-style '/' notation
def ls(args):
    # Check #of args and for optional '-l' flag arg
    long_flag = False
    if len(args) > 2:
        print_error(args[0], "Usage: ls <-l>")
        return
    elif len(args) == 2:
        if args[1] == "-l":
            long_flag = True
        else:
            print_error(args[0], "Invalid argument.")
            return

    # Display buckets when called from root dir, and objects (for the PWD) when called from within a bucket
    if is_root_dir():
        print_buckets(long_flag)
    else:
        print_bucket_objects(long_flag)

# Displays the present working dir (current position in "directory tree") and use the Unix / format.
# Note: Shell displays "root" of the tree (at the bucket level) as 's3:/' (extra '/')
def pwd(args):
    print(get_pwd_string())

# Changes the "directory" allowing traversal "up" and "down" the "tree" of buckets and object folders like navigating file systems
# Able to go to root dir using '~', a sibling directory by specifying the directory name, up to parent (as long as not root) using '..'
# Also able to chaing and use multiple level commands, as well as relative or absolute paths
def cd(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 2:
        print_error(args[0], "Usage: cd <~, .., dir-name>")
        return
    dir_arg = args[1]

    # Attempt to convert the given path string to a list version
    try:
        list_path = convert_path_list(dir_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    # Validate path as list
    if len(list_path) < 1:
        print_error(args[0], "Empty path (should at least contain root).")
        return
    elif list_path[0] != ROOT_DIR[0]:
        print_error(args[0], "Invalid root element of path (was not 's3:').")
        return

    # Check for logical errors with given path
    dir_error_flag = False
    if len(list_path) > 1:
        # Check bucket exists at this path (for the user)
        if not bucket_exists(get_bucket_name(list_path)):
            print_error(args[0], f"No such bucket '{get_bucket_name(list_path)}'.")
            # print_error(args[0], f"{dir_arg}: No such file or directory")
            dir_error_flag = True
        
        # Check if key exists as a directory (folder)
        elif len(list_path) > 2 and not key_exists(get_bucket_name(list_path), get_obj_key(list_path) + '/'):
            # Check if key exists as a file (for specific error message)
            if key_exists(get_bucket_name(list_path), get_obj_key(list_path)):
                print_error(args[0], f"{dir_arg}: Not a directory.")
            else:
                print_error(args[0], f"{dir_arg}: No such file or directory.")
            dir_error_flag = True

    # Set new working dir (as long as no error was found)
    if not dir_error_flag:
        global curr_wd
        curr_wd = list_path

# Create an object folder (directory), as long as not in root level directory (ie. must be in a bucket, does not create a bucket)
def mkdir(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 2:
        print_error(args[0], "Usage: mkdir <dir>")
        return
    dir_arg = args[1]

    # Attempt to convert the given path string to a list version
    try:
        list_path = convert_path_list(dir_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    
    # Validate path as list (after root and bucket)
    if len(list_path) < 3:
        print_error(args[0], "Invalid location - cannot create directories at root.")
        return

    # Get the bucket name, and object key for given path
    bucket = get_bucket_name(list_path)
    obj_key = get_obj_key(list_path) + '/'

    # Check if dir already exists, display err msg if true
    if key_exists(bucket, obj_key):
        print_error(args[0], f"Invalid name - directory {dir_arg} already exists.")
        return

    # Attempt to create the new folder in given path
    try:
        s3_client.put_object(
            Bucket = bucket,
            Key = obj_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Remove (delete) an object folder (directory), as long as not in root level directory (ie. must be in a bucket, does not remove/delete a bucket)
def rmdir(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 2:
        print_error(args[0], "Usage: rmdir <dir>")
        return
    dir_arg = args[1]

    # Attempt to convert the given path string to a list version
    try:
        list_path = convert_path_list(dir_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    
    # Validate path as list (after root and bucket)
    if len(list_path) < 3:
        print_error(args[0], "Invalid location - cannot remove directories at root.")
        return

    # Get the bucket name, and object key for given path
    bucket = get_bucket_name(list_path)
    obj_key = get_obj_key(list_path) + '/'

    # Check if dir does not exist (or is not a dir), display err msg if true
    if not key_exists(bucket, obj_key):
        # Check if key exists as a file
        if key_exists(bucket, obj_key[:-1]):
            print_error(args[0], f"Remove failed for '{dir_arg}' - Not a directory.")
        else:
            print_error(args[0], f"Remove failed for '{dir_arg}' - No such file or directory.")
        return

    # Ensure dir is empty before removing, display err msg if not empty
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=obj_key
    )
    if response['KeyCount'] > 1:
        print_error(args[0], f"Remove failed for '{dir_arg}' - Directory not empty.")
        return

    # Attempt to Delete the dir folder object
    try:
        s3_client.delete_object(
            Bucket=bucket,
            Key=obj_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Uploads (copies) a file from local file system to S3 object store, using either the total "path" or assume it is in the object "directory" (folder) of PWD (for S3 object)
def upload(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 3:
        print_error(args[0], "Usage: upload <local-filename-source> <s3-object-name-destination>")
        return
    local_src = args[1]
    dest_arg = args[2]

    # Check if file does not exist, display error message
    if not os.path.isfile(local_src):
        print_error(args[0], f"Upload failed for '{local_src}' - No such file.")
        return

    # Attempt to convert the given path string to a list version for the destination
    try:
        dest_list_path = convert_path_list(dest_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    
    # Validate path as list for destination (after root and bucket)
    if len(dest_list_path) < 3:
        print_error(args[0], f"Upload failed - Cannot upload to root.")
        return

    # Get the bucket name, and object key for given path of destination
    dest_bucket = get_bucket_name(dest_list_path)
    dest_key = get_obj_key(dest_list_path)

    # Attempt to upload the local filename source to S3 object (bucket or dir)
    try:
        s3_client.upload_file(
            Filename = local_src,
            Bucket = dest_bucket,
            Key = dest_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Downloads (copies) a file from S3 object store to local file system, using either the total "path" or assume it is in the object "directory" (folder) of PWD (for S3 object)
def download(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 3:
        print_error(args[0], "Usage: download <s3-object-name-source> <local-filename-destination>")
        return
    src_arg = args[1]
    local_dest = args[2]

    # Check if file does not exist, display error message
    if os.path.isfile(local_dest):
        print_error(args[0], f"Download failed - Local filename '{local_dest}' already exists.")
        return

    # Attempt to convert the given path string to a list version for the source
    try:
        src_list_path = convert_path_list(src_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    
    # Validate path as list for source (after root and bucket)
    if len(src_list_path) < 3:
        print_error(args[0], f"Download failed for '{local_dest}' - Cannot download a bucket.")
        return
    
    # Get the bucket name, and object key for given path of source
    src_bucket = get_bucket_name(src_list_path)
    src_key = get_obj_key(src_list_path)

    # Attempt to download the S3 object (not bucket or dir) to local filename source location
    try:
        s3_client.download_file(
            Filename = local_dest,
            Bucket = src_bucket,
            Key = src_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Moves/Copies an object from s3 location to another (does not delete source object), using either the total "path" or assume it is in the object "directory" (folder) of PWD (for both params)
# Note: this removes/deletes objects other than buckets and folders (eg. files)
def cp(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 3:
        print_error(args[0], "Usage: cp <s3-object-name-source> <s3-object-name-destination>")
        return
    src_arg = args[1]
    dest_arg = args[2]

    # Attempt to convert the given path string to a list version for the source
    try:
        src_list_path = convert_path_list(src_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    # Validate path as list for source (after root and bucket)
    if len(src_list_path) < 3:
        print_error(args[0], "Invalid location - cannot copy buckets/objects from root.")
        return
    # Get the bucket name, and object key for given path of source
    src_bucket = get_bucket_name(src_list_path)
    src_key = get_obj_key(src_list_path)

    
    # Attempt to convert the given path string to a list version for the destination
    try:
        dest_list_path = convert_path_list(dest_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    # Validate path as list for source (after root and bucket)
    if len(dest_list_path) < 3:
        print_error(args[0], "Invalid location - cannot copy objects to root.")
        return
    # Get the bucket name, and object key for given path of destination
    dest_bucket = get_bucket_name(dest_list_path)
    dest_key = get_obj_key(dest_list_path)

    # Check if object does not exist (or is a dir), display err msg if true
    if not key_exists(src_bucket, src_key):
        print_error(args[0], f"Copy failed for source '{src_arg}' - No such file or directory.")
        return
    elif src_key.endswith('/'):
        print_error(args[0], f"Copy command does not support moving directories.")
        return

    # Attempt to Copy from source to destination
    try:
        s3_client.copy_object(
            CopySource={
                'Bucket': src_bucket,
                'Key': src_key
            },
            Bucket=dest_bucket,
            Key=dest_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Moves/Copies an object from s3 location to another (deletes source object), using either the total "path" or assume it is in the object "directory" (folder) of PWD (for both params)
# Note: this removes/deletes objects other than buckets and folders (eg. files)
def mv(args):
    # Check #of args
    if len(args) != 3:
        print_error(args[0], "Usage: mv <s3-object-name-source> <s3-object-name-destination>")
        return

    # Copy source to destination
    cp(args)

    # Then, delete source after copying
    # Note: already validated this stuff in cp
    src_arg = args[1]

    # Attempt to convert the given path string to a list version for the source
    try:
        src_list_path = convert_path_list(src_arg)
    except Exception as e:
        print_error(args[0], e)
        return
    # Get the bucket name, and object key for given path
    src_bucket = get_bucket_name(src_list_path)
    src_key = get_obj_key(src_list_path)

    # Attempt to Delete the non-dir/folder object
    try:
        s3_client.delete_object(
            Bucket=src_bucket,
            Key=src_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

# Removes/Deletes a named S3 object, using either the total "path" or assume it is in the object "directory" (folder) of PWD
# Note: this removes/deletes objects other than buckets and folders (eg. files)
def rm(args):
    # Check #of args, and copy dir arg to var
    if len(args) != 2:
        print_error(args[0], "Usage: rm <s3-object-name>")
        return
    obj_arg = args[1]
    
    # Attempt to convert the given path string to a list version
    try:
        list_path = convert_path_list(obj_arg)
    except Exception as e:
        print_error(args[0], e)
        return
        
    # Validate path as list (after root and bucket)
    if len(list_path) < 3:
        print_error(args[0], "Invalid location - cannot remove buckets/objects at root.")
        return

    # Get the bucket name, and object key for given path
    bucket = get_bucket_name(list_path)
    obj_key = get_obj_key(list_path)

    # Check if object does not exist (or is a dir), display err msg if true
    if not key_exists(bucket, obj_key):
        if key_exists(bucket, obj_key + '/'):
            print_error(args[0], f"Remove failed for '{obj_arg}' - Is a directory.")
        else:
            print_error(args[0], f"Remove failed for '{obj_arg}' - No such file or directory.")
        return

    # Attempt to Delete the non-dir/folder object
    try:
        s3_client.delete_object(
            Bucket=bucket,
            Key=obj_key
        )
    except Exception as e:
        print_error(args[0], e)
        return

######################################## HELPER FUNCTIONS ########################################

# Filters out all empty strings from a list of strings
def filter_empty_strings(str_list):
    return list(filter(lambda item: item, str_list))

# Template used to print an error message using given command and message info
def print_error(cmd, msg):
    print(f"[ERROR] {cmd}: {msg}")

# ========== LOGIN ==========
# Validates session by checking if session-based client can call list_buckets()
def validate_session():
    # Will fail if session is bad because it cannot call list_buckets()
    try:
        s3_client.list_buckets()
        return True
    except:
        return False

# ========== PWD ==========
# Retrieves the PWD as a string
def get_pwd_string():
    # Checks if PWD is root dir 's3:', and adds '/' if so to make it 's3:/'
    pwd = ROOT_DIR[0]
    if is_root_dir():
        return pwd + "/"
    
    # Not root dir, so create path using folder chain for CWD
    for folder in curr_wd[1:]:
        pwd += f"/{folder}"
    return pwd

# Returns true if given path is root dir, false otherwise
# Note: defaults to PWD if no path is given
def is_root_dir(path=None):
    if path is None:
        path = curr_wd
    return path == ROOT_DIR

# ========== MKBUCKET ==========
# Returns true if the given bucket name exists (owned by the logged in user), otherwise false
def bucket_exists(bucket_name):
    # Immediately return if bucket name is empty
    if bucket_name is None or bucket_name == "":
        return False

    # Get the list of buckets and check if any of their names match
    response = s3_client.list_buckets()
    if 'Buckets' in response:
        for bucket in response['Buckets']:
            if bucket['Name'] == bucket_name:
                return True
    return False

# ========== LS ==========
# Prints the buckets if 'ls' is called from root dir
# Note: if long_flag was set (defaults to False), print the long form with more info (creation date)
# NOTE: Improved by adding size of bucket (by accumulating for each object in bucket) and added 's3-bucket' as file/content type for all buckets
def print_buckets(long_flag=False):
    # Get the list of buckets and check that at least 1 bucket exists (print nothing if no buckets)
    bucket_response = s3_client.list_buckets()
    if 'Buckets' not in bucket_response:
        return
    buckets = bucket_response['Buckets']
    if len(buckets) == 0:
        return

    # Construct output string to print to user about buckets, then print using the lists of stored data from buckets
    output = ""
    bucket_names = []
    bucket_sizes = []
    biggest_bucket = ""
    create_dt_list = []

    for bucket in buckets:
        # Format: -dir- <bucket-size> <creation-date-time> <bucket-name>; where creation-date-time only shows up for -l flag
        if long_flag:
            # Accumulate size of each object in bucket to get bucket size
            size = 0
            curr_bucket = s3_resource.Bucket(bucket['Name'])
            for obj in curr_bucket.objects.all():
                size += obj.size
            bucket_sizes.append(f"{size}")
            # Track biggest bucket size to use for output string padding
            if len(f"{size}") > len(biggest_bucket):
                biggest_bucket = f"{size}"

            # Get bucket creation date-time
            create_dt_list.append(f"{bucket['CreationDate']}")

        # Always get bucket name
        bucket_names.append(f"{bucket['Name']}")
    
    # Build output to display based on normal or long format
    for i in range(len(bucket_names)):
        if long_flag:
            output += "s3-bucket\t"
            output += "{:<{}s}".format(bucket_sizes[i], len(biggest_bucket)) + "\t"
            output += f"{create_dt_list[i]}\t"
        else:
            output += "-dir-\t"
        output += f"{bucket_names[i]}\n"
    print(output.strip("\n"))

# Prints the bucket objects if 'ls' is not called from root dir
# Note: if long_flag was set (defaults to False), print the long form with more info (file type, size, creation date-time, name)
def print_bucket_objects(long_flag=False):
    # Get the bucket name, and object key for current location PWD bucket
    bucket = get_bucket_name()
    dir_key = get_obj_key()
    # Ensure that dir key has a '/' if empty
    if dir_key is None:
        dir_key = ''
    else:
        dir_key += '/'

    # Get list of objects in the bucket within the PWD and check that at least 1 object exists (print nothing if no objects)
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=dir_key
    )
    objects = []
    if 'Contents' in response:
        objects = response['Contents']
    if len(objects) == 0:
        return

    # Construct output string to print to user about bucket objects, then print using the lists of stored data from bucket objects
    output = ""
    content_types = []
    sizes = []
    create_dt_list = []
    obj_keys = []

    # Used to determine longest in each column before building output
    longest_content_type = ""
    longest_size = ""
    longest_dt = ""
    longest_obj_key = ""

    for obj in objects:
        obj_key = obj["Key"]
        # Skip printing PWD name (only for normal form)
        if obj_key == dir_key and not long_flag:
            continue

        # Split object key (excluding PWD dir key) by '/'
        key_split = obj_key[len(dir_key):].split('/')
        if len(key_split) == 1 or (len(key_split) == 2 and key_split[1] == ''):
            # Check if it refers to current dir, change it to '.'
            # We only do this for '-l' flag though, because normal 'ls' does not display it (so continue and skip loop)
            obj_display_key = obj["Key"]
            if obj_key == dir_key:
                if long_flag:
                    obj_display_key = "."
                else:
                    continue

            # Always create a row for each object
            ct = str(s3_client.get_object(Bucket=bucket, Key=obj_key)['ContentType'])
            content_types.append(ct)
            s = str(obj["Size"])
            sizes.append(s)
            dt = str(obj["LastModified"])
            create_dt_list.append(dt)
            obj_keys.append(str(obj_display_key))

            # Check if any are greater than current longest
            if len(ct) > len(longest_content_type):
                longest_content_type = ct
            if len(s) > len(longest_size):
                longest_size = s
            if len(dt) > len(longest_dt):
                longest_dt = dt
            if len(obj_display_key) > len(longest_obj_key):
                longest_obj_key = obj_display_key

    # Build output to display based on normal or long format (content type, size, creation date-time, object name)
    for i in range(len(obj_keys)):
        if long_flag:
            output += "{:<{}s}".format(content_types[i], len(longest_content_type)) + "\t"
            output += "{:<{}s}".format(sizes[i], len(longest_size)) + "\t"
            output += "{:<{}s}".format(create_dt_list[i], len(longest_dt)) + "\t"
            output += "{:<{}s}".format(obj_keys[i], len(longest_obj_key)) + "\n"
        else:
            # Display directory with identifier tag prefix, otherwise no prefix
            if obj_keys[i].endswith('/'):
                output += "-dir-\t"
            else:
                output += "\t"
            output += f"{obj_keys[i]}\n"
    # Print the built output as long as there was at least one object
    if len(obj_keys) > 0:
        print(output.strip("\n"))

# ========== CD ==========
# Convert a string path (local or absolute) into a list
def convert_path_list(path):
    list_path = []
    # Set list path we start with to relative if not an absolute path
    if not is_abs_path(path):
        list_path = curr_wd.copy()
    
    # Split given path by '/' and filter out empty strings
    split_path = path.split('/')
    split_path = filter_empty_strings(split_path)
    # Go through each piece of given path dir, accounting for '~' and '..'
    for split_str in split_path:
        if split_str == '~':
            # Set to root 'dir'
            list_path = ROOT_DIR.copy()
        elif split_str == '..':
            # Go 'up' one 'dir'
            if not is_root_dir(list_path):
                list_path = list_path[:-1]
        else:
            # Go 'down' one more towards specified 'dir'
            list_path.append(split_str)
    return list_path

# Returns true if the given path (either list or string versions) is an absolute path
def is_abs_path(path):
    # Raise errors for bad paths to be handled by call to this function
    # Split string version path by '/' to check if it has absolute path symbol '~'
    if path is None:
        raise TypeError("is_abs_path(): path is None.")
    elif type(path) == str:
        path = path.split('/')
    elif type(path) != list:
        raise TypeError(f"is_abs_path(): received bad path of type {type(path)}.")

    if len(path) == 0:
        return False
    return (path[0] == "~" or path[0] == "s3:")

# Retrieves bucket name from given path (or None if path is root dir)
# Note: By default, looks at PWD if no path given
def get_bucket_name(list_path=None):
    if list_path is None:
        list_path = curr_wd

    if is_root_dir(list_path):
        return None
    else:
        return list_path[1]
    #return None if is_root_dir(list_path) else list_path[1]

# Returns true if the given key exists as an object in the given bucket
# Note: determine if key exists for bucket by successful call for get_object()
def key_exists(bucket, key):
    try:
        s3_client.get_object(
            Bucket=bucket,
            Key=key
        )
        return True
    except:
        return False

# Retrieves the key of the object from a given path (or None if path is not long enough)
# Note: By default, looks at PWD if no path given
def get_obj_key(list_path=None):
    if list_path is None:
        list_path = curr_wd
    if len(list_path) < 3:
        return None

    # Start list path after root and bucket
    obj_key = ""
    for path_str in list_path[2:]:
        obj_key += f"{path_str}/"
    obj_key = obj_key.strip('/') #remove extra '/' on end (if present)

    return obj_key

###################################################################################################

main()