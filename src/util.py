#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
General useful scripts for error analysis.
"""


import logging
import math
import yaml
import pandas as pd


def get_config(config_file):
	with open(config_file, 'r') as stream:
		return yaml.safe_load(stream)


def get_logger(debug):
	if debug:
		level = logging.DEBUG
	else:
		level = logging.INFO
		
	logger = logging.getLogger()
	logger.setLevel(level)
	
	ch = logging.StreamHandler()
	ch.setLevel(level)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	ch.setFormatter(formatter)

	logger.addHandler(ch)
	return logger


def read_metadata(metadata_file):
	df = pd.read_csv(metadata_file, header=0)
	df.index = df['FILE']
	d = df.to_dict()
	result = d['TRANSCRIBER']
	result = {k + ".trans": v for k, v in result.items()}
	return result


def is_special_char(token):
	return token == '//' or token.startswith('--')


def get_token_base(token):
	SPECIAL_PREFIX = ('a_', 'b_')
	if token.startswith(SPECIAL_PREFIX):
		return token[2:]
	return token


def is_contraction(token):
	CONTRACTION_PREFIX = ("\'", "n\'t")
	return get_token_base(token).startswith(CONTRACTION_PREFIX)
	
		
def get_sup_diff(l1, l2):
	t1 = sum([math.log2(x) for x in l1])
	t2 = sum([math.log2(x) for x in l2])
	return t1/len(l1) - t2/len(l2)


def ms_labels():
	return {'DEL', 'SUB_MS', 'CONT_MS'}


def ptb_labels():
	return {'INS', 'SUB_TREE', 'CONT_TREE'}


def err_labels(dtype):
	if dtype == 'ptb':
		return {'INS', 'SUB_TREE', 'SUB_MS'}
	else:
		return {'DEL', 'SUB_TREE', 'SUB_MS'}


#def err_labels():
#	return {'INS', 'DEL', 'SUB_TREE', 'SUB_MS'}


def non_error():
	return {'O', 'CONT'}


def get_norm_label():
	return 'O'


def is_ptb(label):
	return label in ptb_labels() or label in non_error()


def is_ms(label):
	return label in ms_labels() or label in non_error()