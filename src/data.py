#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Preprocessing on the alignment dataset and
processing for tsv output.
"""


import os
import csv
import itertools
from ast import literal_eval
import pickle
import pandas as pd


def read_tsv(tsv_file, header=0):
	"""Given a tsv file reads and returns as pandas dataframe."""
	df = pd.read_csv(tsv_file, sep='\t', header=header, quotechar="\"")
	
	# convert strings of lists to lists
	for col_name in df.columns:
		if str(df.iloc[0][col_name]).startswith('[') and \
		   str(df.iloc[0][col_name]).endswith(']'):
			df[col_name] = df[col_name].apply(lambda x: literal_eval(x))
			
	return df


def generate_index(df):
	df.index = df['file_num'].astype(str) + '_' \
			   + df['turn'].astype(int).astype(str) + '_' \
			   + df['sent_num'].astype(str)
	df.index.name = 'index'
	return df
	

def get_turn_num(token):
	return int(token.split("_")[0][3:])


def label_empty_turns(df):
	problem_turn = ["sw4103.trans", "sw4108.trans", "sw4171.trans", "sw4329.trans", "sw4617.trans"]
	for i, row in df.iterrows():
		if row['file'] in problem_turn:
			if not set(row['ms_names']) == {'None'} and \
			   set(row['names']) == {'None'}:
				# use ms names
				turn_toks = get_turn_num(row['ms_names'][0])
			elif set(row['ms_names']) == {'None'} and \
			   not set(row['names']) == {'None'}:
				# use ptb names
				turn_toks = get_turn_num(row['names'][0])
			else:
				# completely empty case
				turn_num = int(df.loc[i - 1, 'turn']) + 1
			if row['turn'] != turn_num:
				df.loc[i, 'turn'] = turn_num
	return df


def merge_score(alignments, file):
	col_name = os.path.splitext(os.path.basename(file))[0]
	temp_df = read_tsv(file)
	temp_df = generate_index(temp_df)
	temp_df.rename(columns={'scores': col_name,}, inplace=True)
	df = alignments.join(temp_df[col_name])
	return df


def read_metadata(metadata_file):
	df = pd.read_csv(metadata_file, header=0)
	df.index = df['FILE']
	d = df.to_dict()
	result = d['TRANSCRIBER']
	result = {k + ".trans": v for k, v in result.items()}
	return result
	

def preprocess(config, logger):
	logger.info('Loading {}'.format(config['alignments_file']))
	alignments = read_tsv(config['alignments_file'])
	
	logger.info('Loading {}'.format(config['metadata_file']))
	transcribers = read_metadata(config['metadata_file'])
	
	# fix turns that have empty label
	alignments = label_empty_turns(alignments)
	
	# add index for easy search and debugging
	alignments['file_num'] = alignments['file'].astype(str).str.slice(2, -6)
	alignments = generate_index(alignments)
	
	# add transcriber info
	alignments['transcriber'] = alignments['file'].apply(lambda x: transcribers[x])
	
	for file in os.listdir(config['score_dir']):
		if file.endswith('_scores.tsv'):
			alignments = merge_score(alignments, os.path.join(config['score_dir'], file))
			logger.info('Merged scores file: {}'.format(file))

	output = os.path.join(config['project_dir'], "data.P")
	alignments.to_pickle(output)
	logger.info('Data written: {}'.format(output))
	
	logger.debug('data.P info...')
	logger.debug(alignments.head())
	logger.debug(alignments.shape)
	return alignments
	
	
def load_data(config, logger):
	data_file = os.path.join(config['project_dir'], 'data.P')
	
	if os.path.exists(data_file):
		logger.info('Loading {}'.format(data_file))
		alignments = pickle.load(open(data_file, 'rb'))
		return alignments
	else:
		return preprocess(config, logger)
		

def sample_results(results, i):
	header = [i for i in itertools.chain(results[i].get_header(), results[i].ptb.get_header('ptb'), results[i].ms.get_header('ms'))]
	header = ' '.join(header)
	value = [i for i in itertools.chain(results[i].get_values(), results[i].ptb.get_values(), results[i].ms.get_values())]
	value = ' '.join(value)

	return header + '\n' + value


def write_tsv(config, logger, results):
	output = os.path.join(config['project_dir'], 'swb_errors_surprisal.tsv')
	
	logger.info('Writing results file to {}'.format(output))
	writer = csv.writer(open(output, 'w'), delimiter='\t')
	
	# write the header
	writer.writerow([i for i in itertools.chain(results[0].get_header(), results[0].ptb.get_header('ptb'), results[0].ms.get_header('ms'))])

	for item in results:
		writer.writerow([i for i in itertools.chain(item.get_values(), item.ptb.get_values(), item.ms.get_values())])