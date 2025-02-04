# Description
TVH IPTV Checker is a small script comparing the actual tvheadend configuration (IPTV service URLs) with the according source in the internet. 
For some reason, tvheadend does not adapt changes automatically, so I wrote this litte script.  
Since tvheadend doesn't provide an api for modifying the services automatically, the script sends out an informational email with a list of deviations it found.  
The correction in tvheadend then needs to be done manually in the web UI.
# Installation
- Make sure python3 is installed on your system and pip is available
- TVHeadend must be running with API activated and using DigestAuth (was the default in my installation)
- Copy all the files to some folder
- Adjust the variables in .bash_tvh
- Change into the folder and execute
  ```pip install --user -r requirements.txt```
- To schedule a job in Linux, place this line in your crontab (`crontab -e`) and adopt to your needs:  
  ```45 16 * * * /home/pi/run_tvh_checker.sh | logger -t check_tvh_networks```  
  Explanation:
  - ```45 16 * * *``` will execute the script at 16:45 each day
  - ```/home/pi/``` is the path to the script (adopt to suit your environment)
  - ```| logger -t check_tvh_networks``` will cause the output to appear in the syslog tagged with 'check_tvh_networks'.
# Working Principle
- Reads the IPTV networks from tvheadend and the URL for the according m3u playlist.
- Downloads the playlist for each network.
- Reads the muxes (services) belonging to the network and compares the configured command (which includes the streaming URL) with the one from the playlist.
- Builds a list with the differences it discoverd.
- Connects to the SMPT server and sends an email containing that list.
- Protocols everything to stdout