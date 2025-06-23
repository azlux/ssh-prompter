//go:build windows
// +build windows

package tools

import (
	"fmt"
	"log/slog"
	"os"
)

func LaunchSSHArgs(args []string, logger *slog.Logger) {
	fmt.Println("Run on Windows, execlp unavailable, Do nothing !")
	fmt.Println("Command run: ssh", args)
	os.Exit(0)
}

func LaunchSSH(selected_host string, logger *slog.Logger) {
	fmt.Println("Run on Windows, execlp unavailable, Do nothing !")
	fmt.Println("Selected host is", selected_host)
	os.Exit(0)
}
