# PALETTE 2 BETA/TEST PLUGIN

This OctoPrint plugin enables connection and communication between OctoPrint and your [Palette 2](https://www.mosaicmfg.com/products/palette-2).

This fork has a few little feature enhancements;
* Display Last Ping statistic on Printer Status Line via M117
    * Enable/Disable via Palette2 Settings panel
* Ability to control feed rates via M220 during Splices
    * Enable/Disable via Palette2 Settings panel
    * Set NORMAL/SLOW feed rate percentage via Palette2 Tab.
* Display when splice occurring as a status line in Palette2 information tab.
* Adjust settings on the Palette2 Tab without interrupting current job!

Details on the M220 and M117 commands can be found here;
https://github.com/prusa3d/Prusa-Firmware/wiki/Supported-G-codes

This has been only tested on a Original Prusa i3 Mk3, however others in the community have used this plugin successfully.

To be able to see the Advanced features, you must first enable it in the Palette2 Plugin Settings area by clicking the Spanner icon.

This is not warranted nor covered by any warranties by Mosaic Manufacturing and I have no Affiliation with them but for the fact I own and love their Palette2.

In order for this to work, your printer must support the following GCODE(s)
M220 and M117

# Installing
On your OctoPrint server,
1) Manually install this plugin via the Plugin Manager using the following URL:
`https://github.com/skellatore/palette2-plugin/archive/master.zip`
    * This will upgrade your current Palette2 Plugin.
    * At any time you can revert to the original Palette2 Plugin, however it will require you to restart octoprint.
4) Ensure version contains "1.3.2-P2PP-RC1"
5) To be able to see the Advanced features, you must first enable it in the Palette2 Plugin Settings (Spanner -> Palette2 -> Enable Advanced Options -> SAVE)
5) Navigate to the Palette2 Plugin Tab.
6) Adjust settings to suit your needs. These can be adjusted mid print without interrupting the print. Feedrate settings for the Splicing Speed will be in effect for the _next_ splice after the setting was modified.

# Known issues
 - None Reported

## Authors

[Mosaic Manufacturing Ltd.](https://www.mosaicmfg.com/)

Tim Brookman - Minor Modifications

## License

This project is licensed under Creative Commons Public Licenses - see the [LICENSE](https://gitlab.com/mosaic-mfg/canvas-plugin/blob/master/LICENSE) file for more details.
