This program combines Bias Frames into a master bias.  If run without parameters, a GUI
window opens.  If run given a list of file names as args, then those are immediately processed
without the UI interaction.

	Tutorial Video:   https://vimeo.com/419600403/b80420f982

Files with same dimensions can be manually selected for combination, or you can point the program
to a large set of files and have it automatically group them by dimensions or temperature
and produce a master dark for each of the grouped sets.

Preferences control how the files are combined and where the result goes. You should always run the
GUI version first, even if you intend to use the command line version, and use the Preferences
window to establish some of the behaviours that will happen when the command line is used.

Command line form:
MasterBiasMaker --option --option ...   <list of FITs files>
Options
    -g   or --gui               Force gui interface even though command line used

    Combination algorithm:  if none, uses GUI preferences
    -m   or --mean                  Combine files with simple mean
    -n   or --median                Combine files with simple median
    -mm  or --minmax <n>            Min-max clipping of <n> values, then mean
    -s   or --sigma <n>             Sigma clipping values greater than z-score <n> then mean

    -v   or --moveinputs <dir>      After successful processing, move input files to directory

    -t   or --ignoretype            Ignore the internal FITS file type (flat, bias, etc)
    
    -o   or --output <path>		    Output file to this location (default: with input files,
                                    used only if no "group" options are chosen)

    -gs  or --groupsize             Group files by size (dimensions and binning)
    -gt  or --grouptemperature <w>  Group files by temperature, with given bandwidth
    -mg  or --minimumgroup <n>      Ignore groups with fewer than <n> files
    -od  or --outputdirectory <d>   Directory to receive grouped master files

Examples:

MasterBiasMaker -s 2.0 -o result.fits *.fits
MasterBiasMaker  -s 2.0 -gs -gt 10 -od ./output-directory ./data/*.fits
