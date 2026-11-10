JavSDT maintenance build — Windows 10 x64

1. Extract the entire ZIP into a writable folder. Do not run inside the ZIP.
2. Double-click JavSDT.exe. No separate Python installation is needed.
3. First launch creates the default INI. Follow the console prompts.
4. Edit the INI to configure metadata site addresses, proxy and naming rules.
5. Test using COPIES of a few videos first: organizing can rename and move files.
6. Keep all distribution files together, including StaticFiles.
7. Report errors by copying the console output; remove private paths/API keys.

Legacy metadata site addresses may no longer work. This build fixes known
code defects; successful live scraping has not yet been confirmed.
Windows executable needs testing on the user's Windows 10 machine.

Second maintenance build:
Advertising domain prefixes such as 4k688.com@ are ignored during ID detection.
Failed sources no longer pause for Enter and are skipped for the current run.
For an existing INI, change the JavDB URL from javdb31.com to https://javdb.com/
and enable the appropriate proxy settings if required by your network.
Do not regenerate an existing INI just to change the URL.

Maintenance build 4:
Requests to each source are spaced by at least 3 seconds. HTTP sessions are reused.
If both primary sources are unavailable, the batch stops early. Files remaining
in the current directory are listed in the pending log, not counted as failures.
Other subdirectories have not been scanned at that point.
Successful metadata is cached even without translation credentials, and reused
for multipart videos. Preserve the metadata cache folder beside the program folder.
A 403 response still requires pausing until normal site access recovers.

Maintenance build 5:
JavDB temporary login notices or HTTP 403 responses get one delayed retry
using the same in-memory session. Default delay: 10 seconds.
Retry-After is respected; a delay over 60 seconds pauses this run instead.
A second failure pauses normally. No browser cookies or passwords are required.
