# ssh-prompter
ssh-prompter lists all servers contained in your ssh_config file with search feature.

### Screenshot
![ssh-prompter](https://raw.githubusercontent.com/azlux/ssh-prompter/master/Capture1.PNG)

### SSH-config configuration
SSH-Prompter manager can folder view :
- You need to add `Folder <folder_name>` into the Hosts you wanto into the ssh_config
- You need to add `IgnoreUnknown Folder` in the beginning of the file to avoid ssh errors.

SSH-Prompter support the Import instruction if you use it into the ssh_config file.

### Install

You need at least the version 7.3p1 of ssh.
```
git clone https://github.com/azlux/ssh-prompter.git
chmod + ssh.py
```

put `alias ssh="~/ssh-prompter/ssh.py"` into you `.bashrc`
