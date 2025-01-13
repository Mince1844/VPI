# Overview
VPI (VScript-Python Interface) is a system for communication between a VScript Squirrel VM and Python backend for a Team Fortress 2 game server.

# Installation
- In the server's /tf/scripts/vscripts/ directory, place **vpi.nut** in there. If you already have a **mapspawn.nut**, just copy the contents of the file provided in this repo to that one, otherwise copy that over too.
- python, aiomysql, mysql server
- Put **vpi.py** and **vpi_interfaces.py** anywhere you like on the server, just make sure they're in the same directory and set your system to automatically run vpi.py as a service.
- Update **vpi_interfaces.py** with any custom interface functions you may want to call from on the client side with VScript, there are some DB functions
# Usage


# Security
