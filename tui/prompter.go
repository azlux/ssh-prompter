package tui

import (
	"bufio"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
)

type HostItem struct {
	Host         string
	Hostname     string
	Folder       string
	FolderInName bool // set true if use a simple "/" instead of the config option Folder
}

var prefixFolder string = " 🗁  "

func emptyHostItem() HostItem {
	return HostItem{Host: "", Hostname: "", Folder: "", FolderInName: false}
}

func ParseSSHConfig(path string, logger *slog.Logger) ([]HostItem, bool) {
	file, err := os.Open(path)
	if err != nil {
		fmt.Println(err)
		return nil, false
	}
	defer file.Close()

	allHost := make([]HostItem, 0)
	var tpHost, tpHostname, tpFolder string
	var tpFolderInName bool = false

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		lineFields := strings.Fields(line)
		if len(lineFields) < 2 {
			continue
		}
		// loop if include found into config
		if strings.ToLower(lineFields[0]) == "include" {
			pathInclude := lineFields[1]
			if !(strings.HasPrefix(pathInclude, "/") || strings.HasPrefix(pathInclude, "~")) {
				home, _ := os.UserHomeDir()
				pathInclude = filepath.Join(home, ".ssh", pathInclude)
			} else if strings.HasPrefix(pathInclude, "~") {
				home, _ := os.UserHomeDir()
				pathInclude = strings.Replace(pathInclude, "~", home, 1)
			}
			logger.Debug("Including" + pathInclude)
			newhosts, _ := ParseSSHConfig(pathInclude, logger)
			allHost = append(allHost, newhosts...)
		} else if strings.ToLower(lineFields[0]) == "host" && !strings.Contains(lineFields[1], "*") {
			if tpHost != "" { // If exist, I already found the full config of previous one
				allHost = append(allHost, HostItem{Host: tpHost, Hostname: tpHostname, Folder: tpFolder, FolderInName: tpFolderInName})
				// reset for new Host config
				tpHost = ""
				tpHostname = ""
				tpFolder = ""
				tpFolderInName = false
			}
			tpHost = lineFields[1]
			if strings.Contains(tpHost, "/") {
				tmpSplit := strings.SplitN(tpHost, "/", 2)
				tpFolder = tmpSplit[0]
				tpHost = tmpSplit[1]
				tpFolderInName = true
			}
		} else if tpHost != "" && strings.ToLower(lineFields[0]) == "hostname" { // Host need to be found first into ssh config
			tpHostname = lineFields[1]
		} else if tpHost != "" && strings.ToLower(lineFields[0]) == "folder" { // Explicit entry Folder
			tpFolder = lineFields[1]
			tpFolderInName = false
		}
	}

	if tpHost != "" { // If exist, I save also the last one
		allHost = append(allHost, HostItem{Host: tpHost, Hostname: tpHostname, Folder: tpFolder, FolderInName: tpFolderInName})
	}

	return allHost, true
}

func StartPrompter(search string, allItems []HostItem) (HostItem, bool) {
	app := tview.NewApplication()
	ok := true
	widthList := 0

	// List to show
	list := tview.NewList().ShowSecondaryText(false)
	list.SetBorder(true).SetTitle(" Server List ").SetTitleAlign(tview.AlignCenter)

	// Status bar
	statusBar := tview.NewTextView().SetTextAlign(tview.AlignCenter).SetDynamicColors(true)

	// Function to update the list according to the filter
	updateList := func(filter string) {
		list.Clear()
		count := 0
		_, _, widthList, _ = list.GetInnerRect()
		all_dir := make([]string, 0)

		for i := range allItems {
			hostToPrint := ""
			if allItems[i].Folder != "" { //Manage a list of folder
				hostToPrint = allItems[i].Folder + "/" + allItems[i].Host
			} else {
				hostToPrint = allItems[i].Host
			}
			if filter == "" { // No Search requested
				if allItems[i].Folder != "" { //Manage a list of folder
					alreadyExist := false
					for j := range all_dir {
						if all_dir[j] == allItems[i].Folder {
							alreadyExist = true
						}
					}
					if !alreadyExist { // List of uniq folder
						all_dir = append(all_dir, allItems[i].Folder)
					}
				} else {
					count++
					nbSpace := max(widthList-len(hostToPrint)-len(allItems[i].Hostname)-2, 2)
					list.AddItem(fmt.Sprintf(" %s%s%s ", hostToPrint, strings.Repeat(" ", nbSpace), allItems[i].Hostname), "", 0, nil)
				}

			} else {

				if strings.Contains(strings.ToLower(hostToPrint), strings.ToLower(filter)) { // Search is requested
					count++
					nbSpace := max(widthList-len(hostToPrint)-len(allItems[i].Hostname)-2, 2)
					list.AddItem(fmt.Sprintf(" %s%s%s ", hostToPrint, strings.Repeat(" ", nbSpace), allItems[i].Hostname), "", 0, nil)
				}
			}
		}
		for i := len(all_dir) - 1; i >= 0; i-- { // Loop to print all folder on top
			count++
			list.InsertItem(0, fmt.Sprintf("%s%s", prefixFolder, all_dir[i]), "", 0, nil)
		}
		statusBar.SetText(fmt.Sprintf("[gray]%d entries, quit: CTRL+C", count))
	}

	scrollBar := tview.NewTextView()
	scrollBar.SetDynamicColors(true).
		SetTextAlign(tview.AlignLeft).
		SetBorder(false)

	updateScrollBar := func() {
		index := list.GetCurrentItem()
		total := list.GetItemCount() - 1

		if total == 0 { //Avoid divide by 0
			scrollBar.SetText("")
			return
		}
		_, _, _, height := list.GetInnerRect()
		height-- // last line doesn't count

		pos := int(float64(index) / float64(total) * float64(height))
		padding_top := 2
		bar := strings.Repeat("\n", padding_top)
		for i := 0; i <= height; i++ {
			if i == pos {
				bar += "[green]█\n"
			} else {
				bar += "[gray]│\n"
			}
		}
		scrollBar.SetText(bar)
	}

	// Search Input Field
	input := tview.NewInputField().
		SetLabel("Search: ").
		SetFieldWidth(20).
		SetChangedFunc(func(text string) {
			updateList(text)
			updateScrollBar()
		})

	// Moving into the list refresh the scrollbar
	list.SetChangedFunc(func(index int, mainText string, secondaryText string, shortcut rune) { updateScrollBar() }) // fake function to match the expected one

	// Action is something is selected
	list.SetSelectedFunc(func(index int, mainText string, secondaryText string, shortcut rune) {
		if strings.HasPrefix(mainText, prefixFolder) {
			// Get folder name
			dir := strings.TrimPrefix(mainText, prefixFolder)
			input.SetText(dir + "/")
			updateList(dir + "/")
			updateScrollBar()
		} else {
			app.Stop()
		}
	})

	// Vertical layout
	mainLayout := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(input, 1, 0, true).
		AddItem(list, 0, 1, false).
		AddItem(statusBar, 1, 0, false)

	// Horizontal center
	root := tview.NewFlex().
		AddItem(nil, 0, 1, false).
		AddItem(mainLayout, 0, 3, true). // List is half of the screen
		AddItem(scrollBar, 1, 1, false).
		AddItem(nil, 0, 1, false)

	app.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
		switch event.Key() {
		case tcell.KeyUp, tcell.KeyDown, tcell.KeyPgUp, tcell.KeyPgDn:
			app.SetFocus(list)
		case tcell.KeyEnter:
			app.SetFocus(list)
		case tcell.KeyCtrlC:
			ok = false
			app.Stop()
		default:
			app.SetFocus(input)
		}
		return event
	})

	app.SetBeforeDrawFunc(func(screen tcell.Screen) bool {
		newWidth, _ := screen.Size()
		if newWidth != widthList {
			widthList = newWidth
			if newWidth < 100 {
				// If the screen is too small
				// Removing the empty items to have the list fullscreen
				root.RemoveItem(nil)
			}
		}
		// If need of full screen background color override
		// screen.Clear()
		// screen.Fill(' ', tcell.StyleDefault.Background(tcell.ColorBlack))

		return false
	})

	app.SetAfterDrawFunc(func(screen tcell.Screen) { // Get size AFTER the first rendering to get the good width.
		updateList("") // Update the list
		input.SetText(search)
		updateScrollBar()
		app.SetAfterDrawFunc(nil) // Delete the hook after first run
	})

	if err := app.SetRoot(root, true).EnableMouse(false).Run(); err != nil {
		panic(err)
	}
	if !ok {
		return emptyHostItem(), ok
	}

	currentLine, _ := list.GetItemText(list.GetCurrentItem())                    // Get the brut selected line text
	currentLineHost := strings.Split(strings.TrimLeft(currentLine, " "), " ")[0] // remove the spaces and the hostname/IP at the end

	// Get the real HostItem behind the selection
	for i := range allItems {
		hostWithFolder := ""
		if allItems[i].Folder != "" { //Manage a list of folder
			hostWithFolder = allItems[i].Folder + "/" + allItems[i].Host
		} else {
			hostWithFolder = allItems[i].Host
		}
		if hostWithFolder == currentLineHost {
			// Return the Host
			return allItems[i], ok
		}
	}
	return emptyHostItem(), false
}
