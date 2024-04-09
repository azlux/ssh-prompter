#!/usr/bin/env python3
from os import system as system_call, popen
from os import execlp
from pathlib import Path
import signal
import argparse
import re
import curses
import filecmp
from typing import Optional

search = ""
args: Optional[argparse.ArgumentParser] = None


def ctrl_caught(signal, frame):
    print("\nSIGINT caught, quitting")
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi')
    try:
        curses.endwin()
    except curses.error:
        pass
    exit(1)


def change_name(name):
    system_call('if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} "' + name + '";fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;"' + name + '"\007";fi')


def start_ssh(host, ip="", port=22):
    change_name(host)
    if not args.color:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no ' + host + ';if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;$(hostname)\007";fi')
    else:
        execlp('/usr/bin/env', '/usr/bin/env', 'bash', '-c',
               'ssh -oStrictHostKeyChecking=no ' + host + ' | ct ;if [ -n "$TMUX" ]; then tmux rename-window -t${TMUX_PANE} $(hostname);fi; if [ -n "$SECURECRT" ]; then echo -n "\033]2;$(hostname)\007";fi')


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
    if path.is_file():
        with open(path) as f:
            host = ""
            hostname = ""
            folder = ""
            port = 22
            for line in f:
                line = line.strip()
                if len(line) > 0 and line[0] != "#":
                    if 'include' in line.lower() and len(line.split(" ")) == 2:
                        path_include = line.split(" ")[1]
                        if path_include[0] in ['/', '~']:
                            pass
                        else:
                            path_include = "~/.ssh/" + path_include
                        new_ssh = get_ssh_server(path=Path(path_include).expanduser())
                        all_ssh = all_ssh + new_ssh
                    if "host " in line.lower() and "*" not in line.lower():
                        if host:
                            all_ssh.append([host, hostname, folder, port])
                            host = ""
                            hostname = ""
                            folder = ""
                            port = 22
                    if "host " in line.lower() and len(line.split(" ")) == 2 and "*" not in line.lower():
                        host = line.split(" ")[1]
                    elif host:
                        if "hostname" in line.lower() and len(line.split(" ")) == 2:
                            hostname = line.split(" ")[1]
                        elif "folder" in line.lower() and len(line.split(" ")) == 2:
                            folder = line.split(" ")[1]
                        elif "port" in line.lower() and len(line.split(" ")) == 2:
                            port = int(line.split(" ")[1])
            all_ssh.append([host, hostname, folder, port])
        return all_ssh
    else:
        exit(f"No file  found at {path}")


def start_prompter(ssh_table, system_argv=None):
    global search
    previous_search = search
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
    max_box_width = min(width, 80)

    box_position_y = title_position_y + 3
    box_x_end = width - (width - max_box_width)
    position_x = max(min(width - box_x_end-10, 50), 0)

    max_lines = max(height - box_position_y - 3, 5)

    box_search = curses.newwin(3, box_x_end, title_position_y, position_x)
    box_search.box()

    box = curses.newwin(max_lines + 2, box_x_end, box_position_y, position_x)
    box.keypad(True)
    box.box()

    cursor_position = 0
    cursor_top = 0
    all_entries = len(table) - 1

    while True:
        # screen.erase()
        box.erase()
        box.border(0)
        box_search.erase()
        box_search.border(0)
        box_search.addstr(0, 3, "Server List")
        box_search.addstr(1, 5, "Type to search : {}".format(search))
        # box_search.addstr(2, 5, f"debug: cursor_top:{cursor_top} cursor_position:{cursor_position} max:{max_lines} all:{all_entries}")
        # box_search.addstr(2, 5, f"debug: max:{max_lines} height:{height}  width:{width}")
        scroll_nb = int((cursor_position * min(max_lines, all_entries)) / all_entries) if all_entries > 0 else 0
        for nb, val in enumerate(table[cursor_top:cursor_top + max_lines]):
            if nb >= max_lines:
                break
            if nb == cursor_position - cursor_top:
                color = curses.A_REVERSE
            else:
                color = curses.A_NORMAL

            match_folder = re.match(r"d/(\S+)/", val[0])
            if match_folder:
                box.addstr(nb + 1, 2, f"+ {match_folder.groups()[0]}", color)
            else:
                scroll = ' '
                if all_entries > max_lines:
                    if (nb - 1 <= scroll_nb <= nb + 1) or (scroll_nb < 2 and nb < 3) or (scroll_nb > max_lines - 2 and nb > max_lines - 2):
                        scroll = '#'
                    else:
                        scroll = '|'
                number_space = min(80, box_x_end) - len(val[0]) - len(val[1]) - 5
                box.addnstr(nb + 1, 2, f"{val[0]}{' ' * number_space}{val[1]}", box_x_end - 4, color)
                box.addnstr(nb + 1, box_x_end - 2, f"{scroll}", box_x_end - 2)

        # screen.refresh()
        box.refresh()
        box_search.refresh()
        char = box.getch()

        if char == curses.KEY_UP:
            if len(table) > 0 and cursor_position > 0:
                if cursor_position <= cursor_top + 5 and cursor_top != 0:
                    cursor_top -= 1
                    cursor_position -= 1
                else:
                    cursor_position -= 1
        elif char == curses.KEY_DOWN:
            if len(table) > 0 and cursor_position < all_entries:
                if cursor_position - cursor_top >= max_lines - 5:
                    cursor_top += 1
                    cursor_position += 1
                else:
                    cursor_position += 1
        elif char == curses.KEY_PPAGE:
            if len(table) > 0 and cursor_position > 0:
                cursor_top -= min(max_lines - 1, cursor_top)
                cursor_position -= min(max_lines - 1, cursor_position)

        elif char == curses.KEY_NPAGE:
            if len(table) > 0 and cursor_position < all_entries:
                cursor_top += min(max_lines - 1, all_entries - cursor_position)
                cursor_position += min(max_lines - 1, all_entries - cursor_position)

        elif char == curses.KEY_RIGHT or char == curses.KEY_LEFT:
            pass
        elif char == curses.KEY_ENTER or char == 10:
            if len(table) == 0:
                curses.endwin()
                exit()
            match = re.match(r"d/(\S+)/", table[cursor_position % len(table)][0])
            if match:
                search = table[cursor_position % len(table)][0]
            else:
                break
        elif char == curses.KEY_DC or char == 127 or char == curses.KEY_BACKSPACE:
            search = search[:-1]
        elif char == 27:  # ESC
            curses.endwin()
            exit()
        else:
            search += chr(char)

        if previous_search != search:
            table = create_table_for_prompt(ssh_table)
            previous_search = search
            all_entries = len(table) - 1
            cursor_position = 0
            cursor_top = 0

    curses.endwin()

    if len(table) == 0:
        exit()
    start_ssh(table[cursor_position][0], table[cursor_position][1], port=int(table[cursor_position][3]))


def main():
    parser = argparse.ArgumentParser(prog="Drop Menu of ~/.ssh/config file", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--fallback", action="store_true", dest="fallback", required=False, help="USELESS")
    parser.add_argument("--color", action="store_true", dest="color", required=False, help="enable coloring the output")
    global args
    args, system_argv = parser.parse_known_args()

    ssh_server = get_ssh_server()
    all_host = [i[0].lower() for i in ssh_server]
    if len(system_argv) < 2:
        if len(system_argv) == 1 and system_argv[0].lower() in all_host:
            start_ssh(ssh_server[all_host.index(system_argv[0].lower())][0],
                      ssh_server[all_host.index(system_argv[0].lower())][1],
                      port=ssh_server[all_host.index(system_argv[0].lower())][3])
        elif len(system_argv) == 1:
            global search
            search = system_argv[0]
    else:
        execlp('ssh', 'ssh', *system_argv)

    start_prompter(ssh_server, system_argv)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_caught)
    main()
