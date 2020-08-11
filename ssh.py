#! /usr/bin/env python3.6

from os import system as system_call
from os import name as system_name
from os import execlp
from os import popen
from pathlib import Path
import signal
import argparse
import re
import curses
import socket

search = ""
args = None


def ctrl_caught(signal, frame):
    print("\nSIGINT caught, quitting")
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    try:
        curses.endwin()
    except curses.error:
        pass
    exit(1)


def is_ssh_open(host, ip, port):
    if not ip:
        ip = host
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((ip, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except (socket.gaierror, socket.herror):
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    finally:
        s.close()


def change_name(name):
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} "' + name + '";fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;"' + name + '"\007";fi')


def start_ssh(host, ip="", port=22, ping=True):
    change_name(host)
    if not args.fallback or not ping or (args.fallback and is_ssh_open(host, ip, port)):
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no ' + host + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;$(hostname)\007";fi')
    else:
        if not ip:
            ip = host
        print("***CONNEXION EN TELNET ***\n")
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c', 'telnet ' + ip + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;$(hostname)\007";fi')


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
            port = 22
            ping = True
            for line in f:
                line = line.strip()
                if len(line) > 0 and line[0] != "#" :
                    if 'include' in line.lower() and len(line.split(" ")) == 2:
                        path_include = line.split(" ")[1]
                        if path_include[0] in ['/', '~']:
                            pass
                        else:
                            path_include = "~/" + path_include
                        new_ssh, new_max = get_ssh_server(path=Path(path_include).expanduser())
                        all_ssh = all_ssh + new_ssh
                        max_length = max(new_max, max_length)
                    if "host " in line.lower() and "*" not in line.lower():
                        if host:
                            all_ssh.append([host, hostname, folder, port, ping])
                            if len(host) > max_length:
                                max_length = len(host)
                            host = ""
                            hostname = ""
                            folder = ""
                            port = 22
                            ping = True
                    if "host " in line.lower() and len(line.split(" ")) == 2 and "*" not in line.lower():
                        host = line.split(" ")[1]
                    elif host:
                        if "hostname" in line.lower() and len(line.split(" ")) == 2:
                            hostname = line.split(" ")[1]
                        elif "folder" in line.lower() and len(line.split(" ")) == 2:
                            folder = line.split(" ")[1]
                        elif "port" in line.lower() and len(line.split(" ")) == 2:
                            port = int(line.split(" ")[1])
                        elif "proxy" in line.lower() and len(line.split(" ")) > 1:
                            ping = False
            all_ssh.append([host, hostname, folder, port, ping])
        return all_ssh, max_length


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
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_CYAN, -1)

    curses.curs_set(0)

    height, width = screen.getmaxyx()
    title_position_y = 1

    box_y = 64
    box_position_y = title_position_y + 3
    position_x = max(int((width - 64) / 3 - 1), 0)

    max_row = max(height - box_position_y - 3, 5)

    box_search = curses.newwin(3, box_y, title_position_y, position_x)
    box_search.box()

    box = curses.newwin(max_row + 2, box_y, box_position_y, position_x)
    box.keypad(1)
    box.box()

    while True:
        screen.erase()
        box.erase()
        box.border(0)
        box_search.erase()
        box_search.border(0)
        box_search.addstr(0, 3, "Server List")
        box_search.addstr(1, 5, "Type to search : {}".format(search))
        for p, val in enumerate(table):
            if p > max_row:
                break
            if p == position:
                color = curses.A_REVERSE
            else:
                color = curses.A_NORMAL

            match = re.match(r"d/(\S+)/", val[0])

            if match:
                box.addstr(p + 1, 2, "+ {}".format(match.groups()[0]), color)
            else:
                box.addstr(p + 1, 2, "{}{}{}".format(val[0], " " * (max_len - len(val[0])), val[1]), color)

        screen.refresh()
        box.refresh()
        box_search.refresh()
        char = box.getch()

        if char == curses.KEY_UP:
            if len(table) > 0:
                position = (position - 1) % len(table)
        elif char == curses.KEY_DOWN and len(table) > 0:
            if len(table) > 0:
                position = (position + 1) % len(table)
        elif char == curses.KEY_RIGHT or char == curses.KEY_LEFT:
            pass
        elif char == curses.KEY_ENTER or char == 10:
            if len(table) == 0:
                curses.endwin()
                exit()
            match = re.match(r"d/(\S+)/", table[position % len(table)][0])
            if match:
                search = table[position % len(table)][0]
            else:
                break
        elif char == curses.KEY_DC or char == 127 or char == curses.KEY_BACKSPACE:
            search = search[:-1]
        elif char == 27:
            curses.endwin()
            exit()
        else:
            search += chr(char)

        table = create_table_for_prompt(ssh_table)
        if len(table):
            position = position % len(table)

    curses.endwin()

    if len(table) == 0:
        exit()
    start_ssh(table[position % len(table)][0], table[position % len(table)][1], port=table[position % len(table)][3], ping=table[position % len(table)][4])


def main():
    parser = argparse.ArgumentParser(prog="Drop Menu of ~/.ssh/config file", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--fallback", action="store_true", dest="fallback", required=False, help="fallback into Telnet if ssh is not open")
    global args
    args, system_argv = parser.parse_known_args()

    ssh_server, max_len = get_ssh_server()
    all_host = [i[0].lower() for i in ssh_server]
    if len(system_argv) < 2:
        if len(system_argv) == 1 and system_argv[0].lower() in all_host:
            start_ssh(ssh_server[all_host.index(system_argv[0].lower())][0],
                      ssh_server[all_host.index(system_argv[0].lower())][1],
                      port=ssh_server[all_host.index(system_argv[0].lower())][3],
                      ping=ssh_server[all_host.index(system_argv[0].lower())][4])
        elif len(system_argv) == 1:
            global search
            search = system_argv[0]
    else:
        execlp('ssh', 'ssh', *system_argv)

    rows, _ = popen('stty size', 'r').read().split()
    start_prompter(ssh_server, max_len + 4, system_argv)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_caught)
    main()
