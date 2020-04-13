#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Author: coman8@uw.edu

This script takes the switchboard file and does preprocessing so it can be used downstream.

- Special characters "//", "--" are removed
- "a_", "b_" prefix remove

For tagging:
- Sentences are printed word by word with a newline inbetween.
- Label is added to column 2 (required by NCRFpp decoder).
- Empty sentences are converted to "#" so we don't lose track when they need to be zipped back in.

For other use (language model)
- Sentences are printed sentence by sentence.
- Empty sentences are left blank.

"""


import argparse
import csv
from ast import literal_eval
import pandas as pd


def process_token(token):
	if token.startswith(('a_', 'b_')):
		return token[2:]
	return token


def is_special(token):
	return token == '//' or token.startswith('--')


def is_empty(sent):
	if not sent:
		return True
	return all([is_special(x) for x in sent])


def write_file(sentences, output):
	LABEL = 'SYM'
	EMPTY = '#'  # placeholder for tagger 
	
	sentences = [literal_eval(x) for x in sentences]
	writer = csv.writer(open(output, 'w'), delimiter='\t', lineterminator="\n")
	
	for sent in sentences:
		if is_empty(sent):
			sent = EMPTY
		else:
			# special char removal needed for lm which uses tokenized sentence!
			sent = [x for x in sent if not is_special(x)]
			sent = [process_token(x) for x in sent]
	
		if args.tagging:
			for token in sent:
				writer.writerow([token, LABEL])
			writer.writerow("")
		else:
			if sent == EMPTY:
				writer.writerow("")
			else:
				result = [' '.join(sent)]
				writer.writerow(result)
		

def main(args):
	df = pd.read_csv(args.file, delimiter='\t')
	
	label = ''
	ptb_sent = 'sentence'
	ms_sent = 'ms_sentence'
	
	if not args.tagging:
		label += '_dtok'
		ptb_sent += label
		ms_sent += label
		
	ptb_out = args.outdir + "swbd_ptb_sents" + label + ".txt"
	write_file(df[ptb_sent].tolist(), ptb_out)
	
	ms_out = args.outdir + "swbd_ms_sents" + label + ".txt"
	write_file(df[ms_sent].tolist(), ms_out)


if __name__=="__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("file", help="Alignments file")
	parser.add_argument("outdir", help="Output file directory")
	parser.add_argument("--tagging", "-t", action="store_true",
						help="Output word by word with tag for tagger decoding.")
	args = parser.parse_args()
	main(args)
