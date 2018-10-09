from os import system as system_call
from os import name as system_name
from os import execlp
from pathlib import Path
import signal
import getch
import argparse
import re


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
    exit(1)


def create_table(table, position, search):
    new_table = []
    match = re.match(r"d/(\S+)/(.*)", search)
    folder = ""
    if match:
        folder = match.groups()[0]
        search = match.groups()[1]

    for i in table:
        if i[2] and not folder and not search:
            if [' ', str('d/' + i[2]) + '/', ''] not in new_table:
                new_table.append([' ', str('d/' + i[2]) + '/', ''])

        elif (search and search.lower() in i[0].lower()) or (not search and not folder) or (folder and not search and folder == i[2]):
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


def print_output(table, position=0, search="", max_len=20, table_created=None):
    clear()
    print("\n\t\t\tServer List\n\n\t\t********************************\n\t\t* Type to search : {}\n\t\t********************************\n".format(search))

    for i in table_created:
        if i[0] is not " ":
            print("\t {}".format(i[0]), end=' ')
        else:
            print("\t   ", end=' ')
        match = re.match(r"d/(\S+)/", i[1])
        if match:
            print("+ {}".format(match.groups()[0]))
        else:
            print("{}{}{}".format(i[1], " " * (max_len - len(i[1])), i[2]))


def start_prompter(ssh_table, max_len=20, search="", system_argv=None):
    pos = 0
    tp = create_table(ssh_table, position=pos, search=search)
    if len(tp) == 0:
        execlp('ssh', 'ssh', '-oStrictHostKeyChecking=no', system_argv[0])

    print_output(ssh_table, position=pos, search=search, max_len=max_len, table_created=tp)
    while True:
        char = get_input()

        if char == 'UP':
            pos = pos - 1
        elif char == 'DOWN':
            pos = pos + 1
        elif char == 'ENTER':
            match = re.match(r"d/(\S+)/", tp[pos % len(tp)][1])
            if match:
                search = tp[pos % len(tp)][1]
            else:
                break
        elif char == 'DELETE':
            search = search[:-1]
        else:
            search += char

        tp = create_table(ssh_table, position=pos, search=search)
        print_output(ssh_table, position=pos, search=search, max_len=max_len, table_created=tp)

    if len(tp) == 0:
        exit()

    execlp('ssh', 'ssh', '-oStrictHostKeyChecking=no', tp[pos % len(tp)][1])


def main():
    parser = argparse.ArgumentParser(prog="Drop Menu of ~/.ssh/config file", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--add_server_file", type=argparse.FileType('r'), dest="additionnal_server", required=False,
                        help="Additionnal file to search server")
    args, system_argv = parser.parse_known_args()

    ssh_table, max_len = get_ssh_server()
    if args.additionnal_server:
        tp1, tp2 = get_ssh_server(Path(args.additionnal_server))
        ssh_table = ssh_table + tp1
        max_len = (max(max_len, tp2))
    all_host = [i[0] for i in ssh_table]
    search = ""
    if len(system_argv) < 2:
        if len(system_argv) == 1 and system_argv[0] in all_host:
            execlp('ssh', 'ssh', '-oStrictHostKeyChecking=no', system_argv[0])
        elif len(system_argv) == 1:
            search = system_argv[0]
    else:
        execlp('ssh', 'ssh', *system_argv)

    start_prompter(ssh_table, max_len, search, system_argv)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_caught)
    main()
