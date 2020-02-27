#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Pull errors from alignment with their surprisal LLR.

"""


import argparse
import data, util
from collections import defaultdict


def get_base(token):
	SPECIAL_PREFIX = ('a_', 'b_')
	if token.startswith(SPECIAL_PREFIX):
		return token[2:]
	return token


def is_contraction(token):
	CONTRACTION_PREFIX = ("\'", "n\'t")
	return get_base(token).startswith(CONTRACTION_PREFIX)
	
	
def is_empty(sent):
	return not sent or all([is_special_char(x) for x in sent])


def is_special_char(token):
	return token == '//' or token.startswith('--')
	

def iterate_score(token):
	return int(not is_contraction(token) and not is_special_char(token))


def main(args):
	ms_forward= ['DEL', 'SUB_MS', 'CONT_MS']
	ptb_forward = ['INS', 'SUB_TREE', 'CONT_TREE']
	all_forward=['O']
	
	config = util.get_config(args.config)
	logger = util.get_logger(config['debug'])
	alignment = data.load_data(config, logger)


	for i, row in alignment.iterrows():
		ix = defaultdict(int)
		
		for j in range(len(row['comb_ann'])):
			label = row['comb_ann'][j]
			if label in all_forward:
				ix['ptb'] += 1
				ix['ptb_score'] += iterate_score(row['comb_sentence'][j])
				ix['ms'] += 1
				ix['ms_score'] += iterate_score(row['comb_sentence'][j])
			elif label in ptb_forward:
				ix['ptb'] += 1
				ix['ptb_score'] += iterate_score(row['comb_sentence'][j])
			elif label in ms_forward:
				ix['ms'] += 1
				ix['ms_score'] += iterate_score(row['comb_sentence'][j])


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config", help="experiment config file")
	args = parser.parse_args()
	main(args)
