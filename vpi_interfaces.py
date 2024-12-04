import asyncio
import functools
import re

# Note:
# All interface functions should be decorated with either WrapDB or WrapInterface
# Otherwise any errors that occur will not be handled gracefully and brick the entire program

# Remove problematic characters from strings (return copy)
def SanitizeString(string):
	sanitized = re.sub("[\0\x1a;]", "", string)
	return sanitized

# Sanitize the strings in an object (dict or list) (return copy)
def SanitizeObj(o):
	t = type(o)
	if (t is str): return SanitizeString(o)
	elif (t is not list and t is not dict): return o

	obj = None

	if (t is list):
		obj = []
		for e in o:
			obj.append(SanitizeObj(e))
	elif (t is dict):
		obj = {}
		for key, val in o.items():
			k = SanitizeObj(key)
			v = SanitizeObj(val)
			obj[k] = v
	else:
		obj = o

	return obj

# Make sure we're trying to access a user table that we have access to (is associated with our script.nut name)
# user_<script_name>_<name>
def ValidateUserTable(info, table):
	if (type(table) is not str): raise ValueError

	table = SanitizeString(table)
	table = table.split('_')
	if (len(table) < 3 or table[0] != "user" or table[1] != info["script"][:-4]):
		raise PermissionError
	table = '_'.join(table)

	if (not table or not len(table)): raise ValueError

	return table

# Wrapper for DB interface functions
def WrapDB(func):
	@functools.wraps(func)
	async def inner(info, pool):
		conn   = await pool.acquire()
		cursor = await conn.cursor()

		result = None
		error  = None

		try:
			result = await func(info, cursor)
		except Exception as e:
			# Client expects error responses to start with [VPI ERROR]
			error = f"[VPI ERROR] ({func.__name__}) :: {type(e).__name__}"
			print(error)
			print(e)
		finally:
			await cursor.close()
			if (error is None):
				await conn.commit()
			pool.release(conn)

			if (error is None): return result
			else:				return error

	return inner

# Wrapper for generic interface functions
def WrapInterface(func):
	@functools.wraps(func)
	async def inner(*args, **kwargs):
		result = None
		error  = None

		try:
			result = await func(*args, **kwargs)
		except Exception as e:
			# Client expects this to start with [VPI ERROR]
			error = f"[VPI ERROR] ({func.__name__}) :: {type(e).__name__}"
			print(error)
			print(e)
		finally:
			if (error is None): return result
			else:				return error

	return inner


# Arbitrary SQL execution
# *** DO NOT GIVE USERS ACCESS TO THIS ***
# kwargs:
# 	required:
#		query  (string) -- Query to execute
# 	optional:
#		format (array)  -- Values to insert into query on %s as '<val>'
@WrapDB
async def VPI_DB_RawExecute(info, cursor):
	# While we already defined a whitelist on the client, this is here
	# to ensure this is not exposed unintentionally (e.g. from empty client whitelist)
	source_whitelist = ["vpi.nut", "a.nut"] # Script names go here
	if (not len(source_whitelist)): raise PermissionError
	if (info["script"] not in source_whitelist): raise PermissionError

	kwargs = info["kwargs"]
	query  = kwargs["query"]
	form   = kwargs["format"] if "format" in kwargs else None

	if (type(query) is not str or (form is not None and type(form) is not list)): raise ValueError

	await cursor.execute(query, form)

	return await cursor.fetchall()


########################################## USER FUNCTIONS #########################################
# Admin or server owner will need to create DB tables as needed by users manually
# (or define interface functions for such a purpose themselves, but it is recommended to do it manually for security and DB integrity)

# User tables must follow a specific name format to be accessible by user interface functions: user_<script_name>_<name> (See: ValidateUserTable)
# E.g. user_contracts_players for client user script contracts.nut

# This is to isolate client scripts to only accessing their associated tables
# As a result you may also have tables in the same database that do not start with 'user' for administrative or other purposes


# Simple SELECT statement wrapper for users
# kwargs:
# 	required:
# 		table (string) -- String table name to select from
# 	optional:
# 		columns       (array)      -- Columns to select, * if not provided
# 		filter_column (string)     -- Column to filter results by (WHERE)
# 		filter_op     (string)     -- Operator for value (> < >= <= = != <>)
# 		filter_value  (string|int) -- Value for filter
@WrapDB
async def VPI_DB_UserSelect(info, cursor):
	kwargs = SanitizeObj(info["kwargs"])

	# FROM
	table = ValidateUserTable(info, kwargs["table"])

	# SELECT
	columns = kwargs["columns"] if "columns" in kwargs else []

	# WHERE
	filter_column = kwargs["filter_column"] if "filter_column" in kwargs else None
	filter_op     = kwargs["filter_op"]     if "filter_op"     in kwargs else "="
	filter_value  = kwargs["filter_value"]  if "filter_value"  in kwargs else None

	# Construct query
	s_columns = "*"
	if (type(columns) is list and len(columns)):
		s_columns = ','.join([s for s in columns if type(s) is str])

	s_filter = ""
	# We only care if all of them are specified
	# filter_value can be something other than str (e.g. int 0) so we check against None instead of truthy
	if (filter_column and filter_op and filter_value is not None):
		s_filter = f"WHERE {filter_column} {filter_op} '{filter_value}'"

	await cursor.execute(f"SELECT {s_columns} FROM {table} {s_filter}")

	return await cursor.fetchall()

# Simple INSERT statement wrapper for users
# kwargs:
# 	required:
# 		table  (string) -- String table name to select from
# 		values (array)  -- Values to insert, can be single list or list of lists for multiple values
# 	optional:
# 		columns (array) -- Array of string column names
@WrapDB
async def VPI_DB_UserInsert(info, cursor):
	kwargs = SanitizeObj(info["kwargs"])

	# INTO
	table = ValidateUserTable(info, kwargs["table"])

	# INSERT
	columns = kwargs["columns"] if "columns" in kwargs else None

	# VALUES
	values = kwargs["values"]
	if (type(values) is not list or not len(values)): raise ValueError

	# Convert to sublist if needed
	if (not all([type(v) is list for v in values])):
		values = [values]

	# Construct query
	s_columns = ""
	if (type(columns) is list and len(columns)):
		','.join([s for s in columns if type(s) is str])

	s_values = "VALUES " + ','.join([f"({','.join([str(v) for v in vals])})" for vals in values])

	await cursor.execute(f"INSERT INTO {table} {s_columns} {s_values}")

	return cursor.rowcount

# Simple UPDATE statement wrapper for users
# kwargs:
# 	required:
# 		table (string) -- String table name to select from
# 	optional:
# 		values        (table)      -- Columns to set to what values
# 		filter_column (string)     -- Column to filter results by (WHERE)
# 		filter_op     (string)     -- Operator for value (> < >= <= = != <>)
# 		filter_value  (string|int) -- Value for filter
@WrapDB
async def VPI_DB_UserUpdate(info, cursor):
	kwargs = SanitizeObj(info["kwargs"])

	# UPDATE
	table = ValidateUserTable(info, kwargs["table"])

	# SET
	values = kwargs["values"]
	if (type(values) is not dict or not len(values)): raise ValueError

	# WHERE
	filter_column = kwargs["filter_column"] if "filter_column" in kwargs else None
	filter_op     = kwargs["filter_op"]     if "filter_op"     in kwargs else "="
	filter_value  = kwargs["filter_value"]  if "filter_value"  in kwargs else None

	# Construct query
	s_values = ','.join([f"{col} = {val}" for col, val in values.items()])

	s_filter = ""
	# We only care if all of them are specified
	# filter_value can be something other than str (e.g. int 0) so we check against None instead of truthy
	if (filter_column and filter_op and filter_value is not None):
		s_filter = f"WHERE {filter_column} {filter_op} '{filter_value}'"

	await cursor.execute(f"UPDATE {table} SET {s_values} {s_filter}")

	return cursor.rowcount

# INSERT ON DUPLICATE KEY UPDATE wrapper for users
# kwargs:
# 	required:
# 		table         (string) -- String table name to select from
# 		values        (array)  -- Values to insert, can be single list or list of lists for multiple values
# 		update_values (table)  -- What values to set columns to on duplicate key. t. and n. can be used as shorthand
# 								  for the table name and values label respectively (e.g. "t.wins": "t.wins + n.wins")
# 	optional:
# 		columns (array) -- Array of string column names
@WrapDB
async def VPI_DB_UserInsertOrUpdate(info, cursor):
	kwargs = SanitizeObj(info["kwargs"])

	# INTO
	table = ValidateUserTable(info, kwargs["table"])

	# INSERT
	columns = kwargs["columns"] if "columns" in kwargs else None

	# VALUES
	values = kwargs["values"]
	if (type(values) is not list or not len(values)): raise ValueError

	# Convert to sublist if needed
	if (not all([type(v) is list for v in values])):
		values = [values]

	# ON DUPLICATE KEY UPDATE
	update_values = kwargs["update_values"]
	if (type(update_values) is not dict or not len(update_values)): raise ValueError

	formatted_update = {}
	for col, val in update_values.items():
		col = str(col).replace("t.", f"{table}.")
		val = str(val).replace("t.", f"{table}.").replace("n.", f"new.")
		formatted_update[col] = val

	# Construct query
	s_columns = ""
	if (type(columns) is list and len(columns)):
		','.join([s for s in columns if type(s) is str])

	s_values = "VALUES " + ','.join([f"({','.join([str(v) for v in vals])})" for vals in values])
	s_update = ','.join([f"{col} = {val}" for col, val in formatted_update.items()])

	print(f"INSERT INTO {table} {s_columns} {s_values} AS new ON DUPLICATE KEY UPDATE {s_update}")

	await cursor.execute(f"INSERT INTO {table} {s_columns} {s_values} AS new ON DUPLICATE KEY UPDATE {s_update}")

	return cursor.rowcount # todo this is a little wonky on this query for some reason

# Simple DELETE statement wrapper for users
# kwargs:
# 	required:
# 		table (string)             -- String table name to select from
# 		filter_column (string)     -- Column to filter results by (WHERE)
# 		filter_value  (string|int) -- Value for filter
# 	optional:
# 		filter_op (string) -- Operator for value (> < >= <= = != <>)
#       wipe      (bool)   -- Ignore filter and delete the entirety of table contents
@WrapDB
async def VPI_DB_UserDelete(info, cursor):
	kwargs = SanitizeObj(info["kwargs"])

	# FROM
	table = ValidateUserTable(info, kwargs["table"])

	wipe = True if "wipe" in kwargs and kwargs["wipe"] else False
	if (wipe):
		await cursor.execute(f"DELETE FROM {table}")
		return

	# WHERE
	# Note: These are required unlike above interface functions unless wipe is specified
	filter_column = kwargs["filter_column"]
	filter_op     = kwargs["filter_op"] if "filter_op" in kwargs else "="
	filter_value  = kwargs["filter_value"]

	# Construct query
	s_filter = ""
	# We only care if all of them are specified
	# filter_value can be something other than str (e.g. int 0) so we check against None instead of truthy
	if (filter_column and filter_op and filter_value is not None):
		s_filter = f"WHERE {filter_column} {filter_op} '{filter_value}'"

	await cursor.execute(f"DELETE FROM {table} {s_filter}")

	return cursor.rowcount