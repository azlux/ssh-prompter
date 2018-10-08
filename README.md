# ssh-prompter
SSH prompt list about all server into you ssh_config file with search
Additionnaly, the script can scan another ssh_config file.

### Screenshot
![ssh-prompter](https://raw.githubusercontent.com/azlux/ssh-prompter/master/Capture1.PNG)

### SSH-config configuration
SSH-Prompter manager folder.
- You need to add `Folder <folder_name>` into the Hosts you wanto into the ssh_config
- You need to add `IgnoreUnknown Folder` in the beginning of the file to avoid ssh errors.

### Install
```
git clone https://github.com/azlux/ssh-prompter.git
pip3 install -r requirements.txt
pip3 install getch
chmod + ssh.py
```

put `alias ssh="~/ssh-prompter/ssh.py"` into you `.bashrc`