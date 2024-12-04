IncludeScript("vpi.nut")
/*
local stringtofile = ::StringToFile;
local filetostring = ::FileToString;

// the terminal list (show)

// Just incase this script gets reloaded
if (!("VPI" in getroottable()))
{
	local script_whitelist = {
		"vpi.nut": [".interface"],
	}

	local extension_blacklist = [
		".interface",
	];

	local function GetFileExtension(file)
	{
		local index = null;
		for (local i = file.len() - 1; i >= 0; --i)
		{
			if (file[i] == '.')
			{
				index = i;
				break;
			}
		}
		
		if (index == null) return;
		return file.slice(index);
	}

	// Filter the source that called us in the VM stack
	local function ValidateCaller(src, file)
	{
		local extension = GetFileExtension(file);
		if (!extension || extension == "")
			return true;
		else if (extension_blacklist.find(extension) != null)
		{
			if (!(src in script_whitelist)) return false;
			if (script_whitelist[src].find(extension) == null) return false;
		}

		return true;
	}
		

	::StringToFile <- function(file, str) {
		if (typeof(file) != "string") return;
		if (typeof(str)  != "string") return;
		
		local callinfo = getstackinfos(2);
		if (!ValidateCaller(callinfo.src, file)) return;
		
		stringtofile(file, str);
	};

	::FileToString <- function(file) {
		if (typeof(file) != "string") return;
		
		local callinfo = getstackinfos(2);
		if (!ValidateCaller(callinfo.src, file)) return;
		
		return filetostring(file);
	};

	IncludeScript("vpi.nut")
}
*/