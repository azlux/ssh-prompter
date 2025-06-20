//go:build !windows
// +build !windows

package tools

import (
	"log/slog"
	"os"
	"os/exec"

	"golang.org/x/sys/unix"
)

func changeTMUXName(name string, logger *slog.Logger) bool {
	// Manage TMUX
	_, haveTmux := os.LookupEnv("TMUX")
	if haveTmux {
		logger.Debug("TMUX detected, trigger the rename")
		exec.Command("tmux", "rename-window", name).Run()
		return true
	}
	return false
}

func LaunchSSHArgs(args []string, logger *slog.Logger) {
	binary, err1 := exec.LookPath("ssh")
	if err1 != nil {
		logger.Error("Searching SSH executable failed ", "err", err1)
	}

	argv := append([]string{"ssh"}, args...)

	err2 := unix.Exec(binary, argv, os.Environ())
	if err2 != nil {
		logger.Error("Error during executing ssh command", "err", err2)
		os.Exit(1)
	}

}
func LaunchSSH(selected_host string, logger *slog.Logger) {

	haveTMUX := changeTMUXName(selected_host, logger)

	// args to pass to the ssh executable bin
	var args = make([]string, 0)
	var binaryToRun string

	if haveTMUX {

		args = []string{"bash", "-c", "trap 'tmux set-window-option automatic-rename on' EXIT SIGHUP SIGTERM; ssh -oStrictHostKeyChecking=accept-new " + selected_host}
		binary, err := exec.LookPath("bash")
		if err != nil {
			logger.Error("Error searching 'bash'", "err", err)
			return
		}
		binaryToRun = binary
	} else {
		args = []string{"ssh -oStrictHostKeyChecking=accept-new", selected_host}
		binary, err := exec.LookPath("ssh")
		if err != nil {
			logger.Error("Error searching 'ssh'", "err", err)
			return
		}
		binaryToRun = binary
	}

	env := os.Environ()
	err := unix.Exec(binaryToRun, args, env)
	if err != nil {
		logger.Error("Erreur lors de l'exécution de 'ssh'", "err", err)
		os.Exit(0)
	}
}
