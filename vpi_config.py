import os

# This should be the same token returned in the GetSecret function in vpi.nut
# It's used to identify files created by VPI
SECRET = r""
if (not SECRET):
	raise RuntimeError("Please set your secret token")

genv = os.environ.get

SCRIPTDATA_DIR = genv("VPI_SCRIPTDATA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Team Fortress 2\tf\scriptdata")
if (not os.path.exists(SCRIPTDATA_DIR)): raise RuntimeError("SCRIPTDATA_DIR does not exist")

# Are you going to be interacting with a database?
DB_SUPPORT = True
if (DB_SUPPORT):
	DB = None

	DB_TYPE = "MySQL" # MySQL or SQLite

	if (DB_TYPE == "MySQL"):
		import aiomysql
		import argparse

		PARSER = argparse.ArgumentParser()
		PARSER.add_argument("--host", help="Hostname for database connection", type=str)
		PARSER.add_argument("-u", "--user", help="User for database connection", type=str)
		PARSER.add_argument("-p", "--port", help="Port for database connection", type=int)
		PARSER.add_argument("-db", "--database", help="Database to use", type=str)
		PARSER.add_argument("--password", help="Password for database connection", type=str)

		args = PARSER.parse_args()

		# Modify VPI_* with your environment variables if you named them something else
		DB_HOST     = args.host     if args.host     else genv("VPI_HOST",      "localhost")
		DB_USER     = args.user     if args.user     else genv("VPI_USER",      "user")
		DB_PORT	    = args.port     if args.port     else int(genv("VPI_PORT",  3306))
		DB_DATABASE	= args.database if args.database else genv("VPI_INTERFACE", "interface")
		DB_PASSWORD	= args.password if args.password else genv("VPI_PASSWORD", "9drty12")

		# Validation
		for env in [DB_HOST, DB_USER, DB_PORT, DB_DATABASE, SCRIPTDATA_DIR]:
			assert env is not None

		if (DB_PASSWORD is None):
			DB_PASSWORD = input(f"Enter password for {DB_USER}@{DB_HOST}:{DB_PORT} >>> ")
			print()

	elif (DB_TYPE == "SQLite"):
		import aiosqlite

        # Put the path to your .db file here
		DB_LITE = "interface.db"

	else:
		raise RuntimeError("DB_TYPE must be either 'MySQL' or 'SQLite'")