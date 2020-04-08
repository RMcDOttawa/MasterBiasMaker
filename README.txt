This program combines Bias Frames into a master bias.  If run without parameters, a GUI
window opens.  If run given a list of file names as args, then those are immediately processed without the UI interaction.

Preferences control how they are combined and where the result goes. You should always run the GUI version first, even if you intend to use the command line version, and use the Preferences window to establish some of the behaviours that will happen when the command line is used.

Command line form:
MasterBiasMaker --option --option ...   <list of FITs files>
Options
    -g   or --gui               Force gui interface even though command line used

    Precalibration options: if none given, uses what is set in GUI preferences
    -np  or --noprecal          No precalibration of input files
    -p   or --pedestal <n>      Precalibrate by subtracting pedestal value <n>
    -b   or --bias <path>       Precalibrate by subtracting bias file <path>

    Combination algorithm:  if none, uses GUI preferences
    -m   or --mean              Combine files with simple mean
    -n   or --median            Combine files with simple median
    -mm  or --minmax <n>        Min-max clipping of <n> values, then mean
    -s   or --sigma <n>         Sigma clipping values greater than z-score <n> then mean

    -v   or --moveinputs <dir>  After successful processing, move input files to directory

    -t   or --ignoretype        Ignore the internal FITS file type (flat, bias, etc)
    -f   or --ignorefilter      Ignore the internal FITS filter name
    
    -o   or --output <path>		Output file to this location (default: with input files)

Examples:

MasterBiasMaker -s 2.0 biasfolder/*.fits
