# Overview
- what is it
- what does it allow server owners to do
- how does it generally function at a high level
  - files and their roles (vpi.py, vpi_config.py, vpi_interfaces.py, vpi.nut)
  - server / client architecture
  - general overview of what server / client do separately and how they interact

# Installation
- server / client
- installing client
- server dependancies
- installing server
- configuration
  - environment variables / cmd options
  - setting a secret
  - overview of what is configurable
  - running as a service

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
