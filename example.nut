
local cb = function(response, error) {
    if (error || typeof(response) != "array" || !response.len())
    {
        printl(response);
        return;
    }

    foreach (i, row in response)
    {
        local s = "";
        foreach (j, col in row)
            s += format("%s%s", col.tostring(), (j != row.len() - 1) ? "," : "");

        printl(format("Row %d: [%s]", i+1, s));
    }
};

// Urgent Async Call with table
//VPI.AsyncCall({func="VPI_DB_RawExecute", kwargs={query="select name from custom"}, callback=cb, urgent=true});

// Normal Async Call with VPICallInfo instance
//VPI.AsyncCall(VPI.Call("VPI_DB_RawExecute", {query="insert into custom values (null, 'bob', 1989, 'pizza')"}, cb));

// Urgent Chain Call with tables
/*
local calls = [
	{func="VPI_DB_RawExecute", kwargs={query="insert into custom values (null, 'bob', 1989, 'pizza')"}},
	{func="VPI_DB_RawExecute", kwargs={query="select * from custom where name='bob'"}},
];
VPI.ChainCall(calls, cb, true);
*/

// User functions

/*
VPI.AsyncCall({
    func="VPI_DB_UserInsertOrUpdate",
    kwargs={
        table="user_a_tres",
        values=[123, 1, 0, 0]
        update_values={"t.wins":"t.wins + n.wins"}
    },
    callback=cb,
    urgent=true
});
*/

