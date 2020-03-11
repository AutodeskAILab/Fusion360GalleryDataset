# Fusion360Server
Example server running inside Fusion 360 as an add-in.

## Setup
1. Open Fusion
2. Go to Tools tab > Add-ins > Scripts and Add-ins
3. In the popup, select the Add-in panel, click the green '+' icon and select the directory of the repo
4. Click 'Run' to start the server
5. Optionally select 'Run on startup' if you want the server to start when Fusion does

## Testing
After completing the above setup and ensuring you have the `requests` module installed via pip.
```
cd /path/to/Fusion360Server
python test.py
```

You should see output like:
```
Sending get request to Fusion 360...
Get Response <Response [200]>
Sending post request to Fusion 360...
Post Response <Response [200]>
```