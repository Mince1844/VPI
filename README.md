# Overview
VPI (VScript-Python Interface) is a framework for calling Python functions from VScript in Team Fortress 2. With it server owners can create scripts which tell the server to perform some action, or query for information from a resource like a database.

VPI operates in a similar fashion to server-client architecture, with Python acting as the server and Squirrel acting as the client (though both technically reside on the game server). Call data is collected via interface functions in VScript and written to files in the game servers scriptdata directory, Python watches this directory, executes parsed calls, and sends response data back to any callbacks waiting in VScript if necessary via the same scriptdata directory.

# Installation
## Client
- Place **vpi.nut** and **mapspawn.nut** inside of your game servers **tf/scripts/vscripts/** directory

  **Note:** *If you already have an existing **mapspawn.nut**, copy paste the contents of this repos version into yours instead*
- Open **vpi.nut**, there is a section at the top containing variables you might want to modify
- Set your secret key
  - You will see a commented out function called `GenerateSecret`, uncomment this and save the file
  - Start a listen server and type this in console once you load in: `sv_cheats 1; ent_fire !self callscriptfunction GenerateSecret`
  - Copy the output and paste it into the string returned by the `GetSecret` function
  - **(Optional)** Comment out the `GenerateSecret` function again
- Place any script file names and their allowed interface functions (Python functions) they need to use inside the table `SOURCE_WHITELIST`
- **(Optional)** Modify any other settings as desired
## Server
- Install or update to **Python version 3.8** or newer
- Install dependencies
  - VPI supports MySQL and SQLite, if you plan on using a database install either one onto your server if necessary
  - Install database driver
    - For MySQL, install [aiomysql](https://pypi.org/project/aiomysql/)
    - For SQLite, install [aiosqlite](https://pypi.org/project/aiosqlite/)
  - **(Optional)** Install [colorama](https://pypi.org/project/colorama/) for colored console output
- Place **vpi.py**, **vpi_interfaces.py**, and **vpi_config.py** in any directory on your server (as long as they're all in the same one)
- Open **vpi_config.py**, this file contains variables you might want to modify
- Set the `SECRET` constant to the same token you generated for the client earlier
- Either create an environment variable named `SCRIPTDATA_DIR` pointing to your scriptdata dir, or change the default value in **vpi_config.py**
- Set up database info  (skip this if you don't need database usage)
  - Set `DB_SUPPORT` to `True`
  - Set `DB_TYPE` to either `"mysql"` or `"sqlite"`
  - If you're using MySQL:
    - You can provide database info three different ways:
      - Provide cmd args when running **vpi.py**: `python vpi.py --host hostname -u user -p 3306 -db database --password 123xyz`
      - Set the defined environment variables (`VPI_HOST`, `VPI_USER`, `VPI_PORT`, `VPI_INTERFACE`, `VPI_PASSWORD`)
      - Set the default values directly in the script
  - If you're using SQLite:
    - Set the value of `DB_LITE` to the path to your .db file
- **(Optional)** Modify any other settings as desired
- Create a Linux or Windows service to run **vpi.py** automatically

# Usage
- client interface functions
- server interface functions
- calling server functions
- chaining functions with callbacks
- performance considerations
  - minimize calls (consolidate information and make one big call instead of lots of small calls)
  - vscript perf spew convar (set to 5 to avoid i/o perf spam)

# Security
  TODO just realized on this note ill likely need to fully encrypt the files, scripts could try to take an existing file and change the values inside of it
  rather than trying to send a whole new file and guessing the identity
  alternatively the server will need to cross check the file modify time and time used to encrypt the identity

- use at your own risk, sensitive data (e.g. passwords, financial details, real names, etc) should not be recorded

- the challenges of securing the client and what threats are accounted for
- everything is local
- caller validation
- overriding mapspawn.nut
- securing stringtofile / filetostring
- ensuring interface functions are not wrapped
- interface function logic is separate from actual read/write operations
  - script think function handles this, the think function cannot be tampered with / changed because it solely provides the functionality of the program
  all the interface functions actually do is change tables
- information is not encrypted (maybe in the future), its plaintext json
- input/output is validated via a simply encrypted identity (secret token)

- what you should be aware of when using
  - maps with mapspawn.nut (not a security threat but it will prevent the script from loading and may invalidate pending calls by trying to modify files in scriptdata)
  - if you plan on allowing other people to have scripts on your server (e.g. potato uploader):
    do not place functions that interact with VPI in global scope, they should always be local and should never be callable from elsewhere in the VM
      (someone might spam call the function, or worse pass malicious arguments if the function takes parameters used in interface calls)
      if you absolutely must place it in the global scope, make sure the caller is your own script via getstackinfos(2).src inside the function
    - make sure you trust the person you're granting access in the whitelist
    - only give users access to functions they need, DO NOT GIVE ACCESS TO VPI_DB_RawExecute
      better yet if possible, create custom functions for them to use catered to their needs
