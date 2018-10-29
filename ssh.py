from os import system as system_call
from os import name as system_name
from os import execlp
from os import popen
from pathlib import Path
import signal
import argparse
import re
import curses

additional_config = ""
search = ""


def clear():
    system_call('cls' if system_name == 'nt' else 'clear')


def ctrl_caught(signal, frame):
    print("\nSIGINT caught, quitting")
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    curses.endwin()
    exit(1)


def change_name(name):
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} "' + name + '";fi')


def start_ssh(parameter):
    change_name(parameter)
    if additional_config:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no -F <(cat ~/.ssh/config ' + additional_config + ') ' + parameter + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    else:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no ' + parameter + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')


def create_table_for_prompt(table):
    new_table = []
    match = re.match(r"d/(\S+)/(.*)", search)
    folder = ""
    search_tp = search
    if match:
        folder = match.groups()[0]
        search_tp = match.groups()[1]

    for i in table:
        if i[2] and not folder and not search_tp:
            if [str('d/' + i[2]) + '/', ''] not in new_table:
                new_table.append([str('d/' + i[2]) + '/', ''])

        elif (search_tp and search_tp.lower() in i[0].lower()) or (not search_tp and not folder) or (folder and not search_tp and folder == i[2]):
            i2 = i.copy()
            new_table.append(i2)
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


def start_prompter(ssh_table, max_len=20, system_argv=None):
    position = 0
    global search
    table = create_table_for_prompt(ssh_table)
    if len(table) == 0:
        start_ssh(system_argv[0])

    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.start_color()

    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

    curses.curs_set(0)

    height, width = screen.getmaxyx()
    title_position_y = 1

    box_y = 64
    box_position_y = title_position_y + 5
    box_position_x = max(int((width - 64) / 2 - 1), 0)

    max_row = max(height - box_position_y - 3, 5)

    box = curses.newwin(max_row + 2, box_y, box_position_y, box_position_x)
    box.keypad(1)
    box.box()

    while True:
        screen.erase()
        box.erase()
        box.border(0)
        screen.addstr(title_position_y, box_position_x, "Server List")
        screen.addstr(title_position_y + 1, box_position_x, "*" * 15)
        screen.addstr(title_position_y + 2, box_position_x, "* Type to search : {}".format(search))
        screen.addstr(title_position_y + 3, box_position_x, "*" * 15)
        for p, val in enumerate(table):
            if p > max_row:
                break
            if p == position:
                color = curses.color_pair(1)
            else:
                color = curses.A_NORMAL

            match = re.match(r"d/(\S+)/", val[0])

            if match:
                box.addstr(p + 1, 2, "+ {}".format(match.groups()[0]), color)
            else:
                box.addstr(p + 1, 2, "{}{}{}".format(val[0], " " * (max_len - len(val[0])), val[1]), color)

        screen.refresh()
        box.refresh()
        char = box.getch()

        if char == curses.KEY_UP:
            position = (position - 1) % len(table)
        elif char == curses.KEY_DOWN:
            position = (position + 1) % len(table)
        elif char == curses.KEY_ENTER or char == 10:
            if len(table) == 0:
                exit()
            match = re.match(r"d/(\S+)/", table[position % len(table)][0])
            if match:
                search = table[position % len(table)][0]
            else:
                break
        elif char == curses.KEY_DC or char == 127:
            search = search[:-1]
        elif char == 27:
            curses.endwin()
            exit()
        else:
            search += chr(char)

        table = create_table_for_prompt(ssh_table)
        if len(table): position = position % len(table)

    curses.endwin()

    if len(table) == 0:
        exit()
    start_ssh(table[position % len(table)][0])


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
        max_len = min(max(max_len, tp2), 50)
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
