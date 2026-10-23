package main

import (
	"os"
	"path/filepath"
	"strings"

	"log/slog"

	"github.com/azlux/ssh-prompter/tools"
	"github.com/azlux/ssh-prompter/tui"
	"github.com/phsym/console-slog"
	flag "github.com/spf13/pflag"
)

var logger *slog.Logger

func initLog(level slog.Level) {
	var addSource bool = (level == slog.LevelDebug)
	logger = slog.New(console.NewHandler(os.Stderr, &console.HandlerOptions{Level: level, AddSource: addSource}))
}

func LaunchSSHItemHost(hostItem tui.HostItem) {
	if hostItem.Folder != "" && hostItem.FolderInName {
		tools.LaunchSSH(hostItem.Folder+"/"+hostItem.Host, logger)
	} else {
		tools.LaunchSSH(hostItem.Host, logger)
	}
}

func main() {
	var addr_debug *bool = flag.Bool("prompter-debug", false, "Some debug log for ssh-prompter")
	flag.CommandLine.ParseErrorsAllowlist.UnknownFlags = true
	flag.Parse()

	// Log
	if *addr_debug {
		initLog(slog.LevelDebug)
		logger.Debug("Debug log enabled")
	} else {
		initLog(slog.LevelInfo)
	}

	// Part to check if use of specific ssh args
	// This action will bypass the prompter

	// Build a set of known flags
	knownFlags := make(map[string]*flag.Flag)
	flag.CommandLine.VisitAll(func(f *flag.Flag) {
		knownFlags["--"+f.Name] = f
	})

	sshArgs := make([]string, 0, len(os.Args)-1)
	hasUnknown := false

	// Parse all args starting with -
	// Compare with knowFlags
	for i := 1; i < len(os.Args); i++ {
		arg := os.Args[i]

		if !strings.HasPrefix(arg, "--") { // don't need to check simple dash
			sshArgs = append(sshArgs, arg)
			continue
		}

		flagName := arg
		if index := strings.IndexByte(flagName, '='); index >= 0 {
			flagName = flagName[:index] // for --args=data
		}

		if f, ok := knownFlags[flagName]; ok { // ssh-prompter known flags
			// for --flag=value
			if strings.Contains(arg, "=") {
				continue
			}
			// for --flag value, skip the next params because it's the value
			if f.Value.Type() != "bool" && i+1 < len(os.Args) && !strings.HasPrefix(os.Args[i+1], "-") {
				i++
			}
			continue
		}

		// If here, there are args for the real ssh command
		hasUnknown = true
		sshArgs = append(sshArgs, arg)
	}

	args := flag.Args()
	if len(args) > 1 || hasUnknown {
		tools.LaunchSSHArgs(sshArgs, logger)
	}

	var searchText string = ""
	var searchResultCounter int = 0
	var searchFoundExactHost bool = false
	var searchResultHost tui.HostItem
	if len(args) == 1 {
		searchText = args[0]
	}

	// Starting here
	path, _ := os.UserHomeDir()
	allItems, ok := tui.ParseSSHConfig(filepath.Join(path, "/.ssh/config"), logger)
	if !ok {
		logger.Error("No " + path + "/.ssh/config file found")
		os.Exit(1)
	}

	if searchText != "" { // Searching only if the user have request a host
		for i := range allItems {
			if strings.Contains(strings.ToLower(allItems[i].Host), strings.ToLower(searchText)) {
				searchResultHost = allItems[i]
				searchResultCounter += 1
				if strings.EqualFold(allItems[i].Host, searchText) {
					searchFoundExactHost = true
					break
				}
			}
		}
	}

	if searchResultCounter == 0 && searchText != "" {
		//Launch standard SSH if nothing exist into the config file
		logger.Debug("No result during search, back to standars SSH")
		tools.LaunchSSH(searchText, logger)
	} else if searchFoundExactHost {
		logger.Debug("Found direct Host, running SSH without TUI")
		LaunchSSHItemHost(searchResultHost)
	} else {
		// Launch the TUI prompt
		selected_host, ok := tui.StartPrompter(searchText, allItems)
		if ok {
			logger.Debug("SSH requested for " + selected_host.Host)
			LaunchSSHItemHost(selected_host)
		} else {
			logger.Debug("Exiting requested")
		}
	}
}
