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


def get_gold_len(names):
	result = [(not x.endswith('_a') and not x == 'None') for x in names]
	return sum(result)


def verify_len(ix, tokens, gold_len, sym=False, eos=False):
	token_len = len(tokens)

	if eos:
		token_len -= 1

	try:
		assert token_len == gold_len
	except AssertionError as e:
		print('LENGTH MISMATCH: {}'.format(ix))
		print('-gold length: {}'.format(gold_len))
		print('-tokens: {}'.format(tokens))


def verify(align):
	for prefix in ['', 'ms_']:
		print('checking {}'.format('ptb' if prefix == '' else 'ms'))
		gold_len = prefix + 'len'
		names = prefix + 'names'
		align[gold_len] = align[names].apply(lambda x: get_gold_len(x))

		dtok = prefix + 'sentence_dtok'
		align.apply(lambda x: verify_len(x.name, x[dtok], x[gold_len]), axis=1)
		tag = prefix + 'tags'
		align.apply(lambda x: verify_len(x.name, x[tag], x[gold_len]), axis=1)
		shape = prefix + 'shapes'
		align.apply(lambda x: verify_len(x.name, x[shape], x[gold_len]), axis=1)
		ngram = prefix + 'scores-ngram'
		align.apply(lambda x: verify_len(x.name, x[ngram], x[gold_len], eos=True), axis=1)
		gru = prefix + 'scores-gru'
		align.apply(lambda x: verify_len(x.name, x[gru], x[gold_len], eos=True), axis=1)
		align.drop([gold_len], axis=1, inplace=True)


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
				turn_toks = int(df.loc[i - 1, 'turn']) + 1
			if row['turn'] != turn_toks:
				df.loc[i, 'turn'] = turn_toks
	return df


def read_metadata(metadata_file):
	df = pd.read_csv(metadata_file, header=0)
	df.index = df['FILE']
	d = df.to_dict()
	result = d['TRANSCRIBER']
	result = {k + ".trans": v for k, v in result.items()}
	return result


def merge_score(alignments, file):
	col_name = os.path.splitext(os.path.basename(file))[0]
	temp_df = read_tsv(file)
	temp_df = generate_index(temp_df)
	temp_df.rename(columns={'scores': col_name,}, inplace=True)
	df = alignments.join(temp_df[col_name])
	return df


def merge_models(align, config, logger):
	data_path = os.path.join(config['project_dir'], 'data')
	ptb_tags_file = os.path.join(data_path, 'swbd_ptb_tags.tsv')
	ms_tags_file = os.path.join(data_path, 'swbd_ms_tags.tsv')
	ptb_ngram_file = os.path.join(data_path, 'swbd_ptb_ngram_scores.tsv')
	ms_ngram_file = os.path.join(data_path, 'swbd_ms_ngram_scores.tsv')
	ptb_gru_file = os.path.join(data_path, 'swbd_ptb_' + config['nnmodel'] + '_scores.tsv')
	ms_gru_file = os.path.join(data_path, 'swbd_ms_' + config['nnmodel'] + '_scores.tsv')

	ptb_tags = read_tsv(ptb_tags_file)
	ms_tags = read_tsv(ms_tags_file)
	ms_tags.rename(columns={'tags': 'ms_tags', 'shapes': 'ms_shapes'}, inplace=True)
	ptb_ngram = read_tsv(ptb_ngram_file)
	ptb_ngram.rename(columns={'scores': 'scores-ngram'}, inplace=True)
	ms_ngram = read_tsv(ms_ngram_file)
	ms_ngram.rename(columns={'scores': 'ms_scores-ngram'}, inplace=True)
	ptb_gru = read_tsv(ptb_gru_file)
	ptb_gru.rename(columns={'scores': 'scores-gru'}, inplace=True)
	ms_gru = read_tsv(ms_gru_file)
	ms_gru.rename(columns={'scores': 'ms_scores-gru'}, inplace=True)

	ix_cols = ['file', 'speaker', 'turn', 'sent_num']
	logger.info('Size before merge: {}'.format(str(align.shape[0])))
	align = align.merge(ptb_tags, on=ix_cols)
	align = align.merge(ms_tags, on=ix_cols)
	logger.info('Size after tag merge: {}'.format(str(align.shape[0])))
	align = align.merge(ptb_ngram, on=ix_cols)
	logger.info('Size after ptb ngram merge: {}'.format(str(align.shape[0])))
	align = align.merge(ms_ngram, on=ix_cols)
	logger.info('Size after ms ngram merge: {}'.format(str(align.shape[0])))
	align = align.merge(ptb_gru, on=ix_cols)
	logger.info('Size after ptb gru merge: {}'.format(str(align.shape[0])))
	align = align.merge(ms_gru, on=ix_cols)
	logger.info('Size after ms gru merge: {}'.format(str(align.shape[0])))
	return align


def preprocess(config, logger):
	# load files
	alignments_file = os.path.join(config['project_dir'], 'data', config['alignments_file'])
	logger.info('Loading {}'.format(alignments_file))
	align = read_tsv(alignments_file)

	metadata_file = os.path.join(config['project_dir'], 'data', 'metadata.csv')
	logger.info('Loading {}'.format(metadata_file))
	transcribers = read_metadata(metadata_file)

	# add transcriber info
	align['transcriber'] = align['file'].apply(lambda x: transcribers[x])

	# merge the scores and tags
	logger.info('Merging scores and tags to alignments')
	align['file_num'] = align['file'].astype(str).str.slice(2, -6)
	align = merge_models(align, config, logger)

	# make sure all the lengths of tags and scores match the index
	logger.info('Verify indices of tags and scores')
	verify(align)

	# fix turns that have empty label
	align = label_empty_turns(align)

	# make a pretty index
	align = generate_index(align)
	logger.info(align.head())

	logger.debug('data.P info...')
	logger.debug(align.columns)
	logger.debug(align.shape)

	output = os.path.join(config['project_dir'], 'data.P')
	align.to_pickle(output)
	logger.info('Data written to: {}'.format(output))
	return align
	
	
def load_data(config, logger):
	data_file = os.path.join(config['project_dir'], 'data.P')

	if os.path.exists(data_file):
		logger.info('Loading {}'.format(data_file))
		alignments = pickle.load(open(data_file, 'rb'))
		return alignments
	else:
		return preprocess(config, logger)


def write_tsv(config, logger, results):
	output = os.path.join(config['project_dir'], 'swbd_errors.tsv')
	
	logger.info('Writing results file to {}'.format(output))
	writer = csv.writer(open(output, 'w'), delimiter='\t')
	
	# write the header
	writer.writerow([i for i in itertools.chain(results[0].get_header(), results[0].ptb.get_header('ptb'), results[0].ms.get_header('ms'))])

	for item in results:
		writer.writerow([i for i in itertools.chain(item.get_values(), item.ptb.get_values(), item.ms.get_values())])
