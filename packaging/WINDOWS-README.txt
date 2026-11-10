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

Maintenance build 6:
Completed videos are skipped when their matching NFO and required images are
valid. Existing files are not rewritten. Mixed folders are checked per video.
This also avoids unnecessary requests when rerunning previously organized folders.
The setting in the Other Settings section defaults to Yes for existing INI files:
是否跳过已完成影片？ = 是
Set it to 否 when you intentionally want to refresh metadata or reorganize.

Maintenance build 7:
The observed DMM product name 13dsvr01936 is recognized as DSVR-1936.
Multipart file names are scanned in natural numeric order.
Existing INI and metadata caches can still be used.
HTTP 403 handling is unchanged: one delayed retry, then pause if still denied.

Maintenance build 8:
Actor links are parsed structurally instead of relying on adjacent HTML tags.
Actor names are escaped when writing NFO XML. Existing NFO/cache files are not
automatically refreshed. Infuse actor display still depends on client support.

Maintenance build 9:
Double-click RepairActors.bat to fill actors in existing NFO files.
Videos, file names and artwork are not changed by that mode.
A .nfo.before-actors.bak backup is saved before the first NFO modification.
Read JELLYFIN-ACTORS.md for library setup, refresh and actor browsing instructions.

Maintenance build 10:
New metadata comes from JavDB only. Default sites: javdb.com and javdb580.com.
Double-click ConfigureSites.bat to edit sites for organizing and actor repair.
Read JAVDB-SITES.md for configuration and failover rules.
Network/server errors may switch sites; access denials and rate limits do not.
JavDB may not provide every requested field. Unavailable descriptions remain empty.
