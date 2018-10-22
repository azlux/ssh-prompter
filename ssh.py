from os import system as system_call
from os import name as system_name
from os import execlp
from os import popen
from pathlib import Path
import signal
import getch
import argparse
import re

additional_config = ""
search = ""


def clear():
    _ = system_call('cls' if system_name == 'nt' else 'clear')


def get_input():
    char = getch.getch()
    tp = ord(char)
    if tp == 27:
        getch.getch()  # skip the [
        tp = ord(getch.getch())
        if tp == 65:
            return "UP"
        elif tp == 66:
            return 'DOWN'
        elif tp == 67:
            return ''  # RIGHT
        elif tp == 68:
            return ''  # LEFT
    elif tp == 10:
        return 'ENTER'
    elif tp == 127:
        return 'DELETE'
    else:
        return char


def ctrl_caught(signal, frame):
    print("\nSIGINT caught, quitting")
    _ = system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    exit(1)


def change_name(name):
    _ = system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} "' + name + '";fi')


def start_ssh(parameter):
    change_name(parameter)
    if additional_config:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no -F ' + additional_config + ' ' + parameter + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    else:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no ' + parameter + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')


def create_table_for_prompt(table, position):
    new_table = []
    match = re.match(r"d/(\S+)/(.*)", search)
    folder = ""
    search_tp = ""
    if match:
        folder = match.groups()[0]
        search_tp = match.groups()[1]

    for i in table:
        if i[2] and not folder and not search_tp:
            if [' ', str('d/' + i[2]) + '/', ''] not in new_table:
                new_table.append([' ', str('d/' + i[2]) + '/', ''])

        elif (search_tp and search_tp.lower() in i[0].lower()) or (not search_tp and not folder) or (folder and not search_tp and folder == i[2]):
            i2 = i.copy()
            i2.insert(0, ' ')
            new_table.append(i2)

    if new_table:
        new_table[position % len(new_table)][0] = "->"
    return new_table


def get_ssh_server(path=Path(Path.home() / ".ssh/config")):
    all_ssh = []
    max_length = 0
    if path.is_file():
        with open(path) as f:
            host = ""
            hostname = ""
            folder = ""
            for line in f:
                line = line.strip()
                if "Host " in line:
                    if host:
                        all_ssh.append([host, hostname, folder])
                        if len(host) > max_length:
                            max_length = len(host)
                        host = ""
                        hostname = ""
                        folder = ""
                if "Host " in line and len(line.split(" ")) == 2:
                    host = line.split(" ")[1]
                elif host:
                    if "HostName" in line and len(line.split(" ")) == 2:
                        hostname = line.split(" ")[1]
                    elif "Folder" in line and len(line.split(" ")) == 2:
                        folder = line.split(" ")[1]
            all_ssh.append([host, hostname, folder])
        return all_ssh, max_length + 4


def print_prompt(table, max_len=20):
    clear()
    print("\n\n\t\t\tServer List\n\n\t\t********************************\n\t\t* Type to search : {}\n\t\t********************************\n".format(search))

    for i in table:
        if i[0] is not " ":
            print("\t {}".format(i[0]), end=' ')
        else:
            print("\t   ", end=' ')
        match = re.match(r"d/(\S+)/", i[1])
        if match:
            print("+ {}".format(match.groups()[0]))
        else:
            print("{}{}{}".format(i[1], " " * (max_len - len(i[1])), i[2]))


def start_prompter(ssh_table, max_len=20, system_argv=None):
    pos = 0
    global search
    table = create_table_for_prompt(ssh_table, position=pos)
    if len(table) == 0:
        start_ssh(system_argv[0])

    print_prompt(table, max_len=max_len)
    while True:
        char = get_input()

        if char == 'UP':
            pos = pos - 1
        elif char == 'DOWN':
            pos = pos + 1
        elif char == 'ENTER':
            if len(table) == 0:
                exit()
            match = re.match(r"d/(\S+)/", table[pos % len(table)][1])
            if match:
                search = table[pos % len(table)][1]
            else:
                break
        elif char == 'DELETE':
            search = search[:-1]
        else:
            search += char

        table = create_table_for_prompt(ssh_table, position=pos)
        print_prompt(table, max_len=max_len)

    if len(table) == 0:
        exit()
    start_ssh(table[pos % len(table)][1])


def main():
    parser = argparse.ArgumentParser(prog="Drop Menu of ~/.ssh/config file", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--add-config-file", type=str, dest="additional_config", required=False,
                        help="Additionnal config file to search server")
    args, system_argv = parser.parse_known_args()

    ssh_server, max_len = get_ssh_server()
    if args.additional_config:
        global additional_config
        additional_config = args.additional_config
        tp1, tp2 = get_ssh_server(Path(args.additional_config))
        ssh_server = ssh_server + tp1
        max_len = (max(max_len, tp2))
    all_host = [i[0] for i in ssh_server]
    if len(system_argv) < 2:
        if len(system_argv) == 1 and system_argv[0] in all_host:
            start_ssh(system_argv[0])
        elif len(system_argv) == 1:
            global search
            search = system_argv[0]
    else:
        execlp('ssh', 'ssh', *system_argv)

    rows, _ = popen('stty size', 'r').read().split()
    start_prompter(ssh_server, max_len, system_argv)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_caught)
    main()
