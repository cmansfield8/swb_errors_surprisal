# ms-swb-alignments
Code for processing data related to PTB/MS Switchboard error alignments and
generating suprisal values.

1. The alignments file can be found here:

https://github.com/vickyzayats/switchboard_corrected_reannotated 

2. Run pre-processing on the alignments:

sed -r "/'\"+([a-z]+)\"+'/ s//'\1'/g" $INPUT > $OUTPUT
python src/scripts/preprocess.py -cd alignments_file processed_file

3. Run POS tagger and scripts: 

https://github.com/cmansfield8/NCRFpp

4. Add LM scores (more on that later)

5. Add config file (see /exp1/) and run main

python src/main.py config_file

6. Finished!

Returns error list and surprisal scores for analysis.
