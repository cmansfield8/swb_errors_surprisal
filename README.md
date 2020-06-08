# ms-swb-alignments
Code for processing data related to PTB/MS Switchboard error alignments and
generating suprisal values.

1. The alignments file can be found here:

https://github.com/vickyzayats/switchboard_corrected_reannotated 

2. Run pre-processing on the alignments:

sed -r "/'\"+([a-z]+)\"+'/ s//'\1'/g" $INPUT > $OUTPUT
python src/scripts/preprocessor.py -cd switchboard_corrected_reannotated processed_file

3A. Train POS tagger and decode on the alignments. See: 

https://github.com/cmansfield8/NCRFpp

3B. Fetch formatted tags files.  From the NCRFpp repo:

python utils/swb_processing/postprocess.py ncrfpp_output processed_file output_file {ptb, ms}

4.  Fetch LM scores files. See:

https://github.com/cmansfield8/lm_examples

5. Add config file (see /exp1/) and run main

python src/main.py config_file

Returns error list and surprisal scores for analysis.
