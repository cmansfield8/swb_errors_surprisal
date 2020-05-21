#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Pull errors from alignment with their surprisal LLR and various features.

"""


import argparse
from collections import defaultdict
import pickle
import data
import util
from errinfo import ErrSeq, Lex


def get_col(datatype, dtype):
	if dtype == 'ptb':
		data = 'ptb'
	else:
		data = 'ms'
	d = {
		('ptb', 'token'): 'sentence_dtok',
		('ms', 'token'): 'ms_sentence_dtok',
		('ptb', 'name'): 'names',
		('ms', 'name'): 'ms_names',
		('ptb', 'shape'): 'shapes',
		('ms', 'shape'): 'ms_shapes',
		('ptb', 'score'): 'scores-ngram',
		('ms', 'score'): 'ms_scores-ngram',
		('ptb', 'nn_score'): 'scores-gru',
		('ms', 'nn_score'): 'ms_scores-gru',
		('ms', 't-token'): 'ms_sentence',  # tokenized ms sentence
		('ptb', 'disf'): 'tag',
		('ms', 'disf'): 'ms_disfl'
	}
	return d[(data, datatype)]


class ErrorFlags:

	def __init__(self, special_tok=True, prev_error=False, eos=False, split=False, ms_split=False):
		self.special_tok = special_tok
		self.prev_error = prev_error
		self.eos = eos
		self.ptb_split = split
		self.ms_split = ms_split

	def reset(self):
		self.special_tok = False
		self.eos = False
		self.ptb_split = False
		self.ms_split = False


class GenerateError:

	def __init__(self, args):
		config = util.get_config(args.config)
		self.logger = util.get_logger(config['debug'])

		# load the switchboard file
		alignment = data.load_data(config, self.logger)
		self.logger.info('Processing errors...')

		result = list()	 # list of structured error objects
		top_n = self.get_top_word()

		# for each utterance
		for i, row in alignment.iterrows():
			self.ix = defaultdict(int)
			self.flags = ErrorFlags()
			current = ErrSeq()

			# for each token of the alignment
			for j in range(len(row['comb_ann'])):
				self.flags.reset()
				self.ix['ann'] = j
				label = row['comb_ann'][self.ix['ann']]

				# check special conditions
				name, ms_name = '', ''
				if self.ix['ptb'] < len(row[get_col('name', 'ptb')]):  # length check in case its EOS
					name = row[get_col('name', 'ptb')][self.ix['ptb']]
				if self.ix['ms'] < len(row[get_col('name', 'ms')]):
					ms_name = row[get_col('name', 'ms')][self.ix['ms']]
				if name == 'None' and ms_name == 'None':
					self.flags.special_tok = True  # it's a slash unit, for instance
				if name.endswith('_a'):  # so we don't dupe detokenized scores
					self.flags.ptb_split = True
				if ms_name.endswith('_a'):
					self.flags.ms_split = True

				if not self.flags.special_tok:
					# a new error or another error in current error sequence
					if label in util.err_labels(config['dtype']):
						current = self.process_error(i, row, label, current)
						self.flags.prev_error = True

					# add the token after the error sequence
					elif self.flags.prev_error:
						current = self.process_error(i, row, label, current)
						# on to new errors if it's not a split
						if not self.flags.ptb_split and not self.flags.ms_split:
							current.make_summary(top_n, config['dtype'])
							result.append(current)
							self.flags.prev_error = False
							current = ErrSeq()

				# iterate through our pointers
				if util.is_ptb(label):
					self.ix['ptb'] += 1
					if not self.flags.special_tok:
						self.ix['ptb_disf'] += 1
						if not self.flags.ptb_split:
							self.ix['ptb_dtok'] += 1
				if util.is_ms(label):
					self.ix['ms'] += 1
					if not self.flags.special_tok:
						self.ix['ms_disf'] += 1
						if not self.flags.ms_split:
							self.ix['ms_dtok'] += 1

			# add an EOS token after the error sequence in needed
			if self.flags.prev_error:
				label = util.get_norm_label()
				self.flags.eos = True
				current = self.process_error(i, row, label, current)
				current.make_summary(top_n, config['dtype'])
				result.append(current)

		self.logger.info('Error sequences found: {}'.format(str(len(result))))

		data.write_tsv(config, self.logger, result)

	def process_helper(self, i, row, temp, dtype):
		eos_token = '<EOS>'
		token = eos_token
		shape = Lex.EOS.value
		disf = 'O'

		if not self.flags.eos:
			try:
				token = row[get_col('token', dtype)][self.ix[dtype + '_dtok']]
				shape = row[get_col('shape', dtype)][self.ix[dtype + '_dtok']]
				if row[get_col('disf', dtype)]:  # IF DISFLUENCY INFO IS PRESENT - TEMP DUE TO BUG
					disf = row[get_col('disf', dtype)][self.ix[dtype + '_disf']]  # disfluency is mapped to tokenized version
				# handle previous disfluencies
				if row[get_col('disf', dtype)]:  # IF DISFLUENCY INFO IS PRESENT - TEMP DUE TO BUG
					if not self.flags.prev_error:
						prev_disf = 'O'
						if self.ix[dtype + '_disf'] > 1:
							prev_disf = row[get_col('disf', dtype)][self.ix[dtype + '_disf'] - 1]
						temp.set_disf(prev_disf)
			except IndexError as e:
				self.debug_report(e, row, i, dtype)
				token = ''
				shape = ''
				disf = ''
		temp.set_token(token, shape, disf)

		try:
			score = row[get_col('score', dtype)][self.ix[dtype + '_dtok']]
			nn_score = row[get_col('nn_score', dtype)][self.ix[dtype + '_dtok']]
		except IndexError as e:
			self.debug_report(e, row, i, dtype)
			score = 0.01
			nn_score = 0.01
		temp.set_score(score, nn_score)

		return temp

	def process_error(self, i, row, label, current):
		# add basic info if it's a new error
		if not self.flags.prev_error:
			current.index = i
			current.transcriber = row['transcriber']

		# always add annotation info
		current.add_type(label)

		# it's a ptb-related error or it's the following word
		if util.is_ptb(label) or label in util.non_error():
			if not self.flags.ptb_split:
				current.ptb = self.process_helper(i, row, current.ptb, 'ptb')

		# it's an ms-related error or it's the following word
		if util.is_ms(label) or label in util.non_error():
			if not self.flags.ms_split:
				current.ms = self.process_helper(i, row, current.ms, 'ms')
				# mark if it's a special case - deletion at an edge
				if label == 'DEL' and (self.ix['ann'] == 0 or self.ix['ann'] == len(row['comb_ann'])-1):
					current.del_edge = True
		return current

	def get_top_word(self):
		f = 'data/top-n.P'
		try:
			return pickle.load(open(f, 'rb'))
		except FileNotFoundError:
			self.logger.error('Top n file missing at: /data/top-n.P')
			exit()

	def debug_report(self, e, row, i, dtype):
		"""in case of indexing error, includes some useful info"""
		self.logger.debug('INDEX ERROR {}'.format(e))
		self.logger.debug('Index: {}'.format(i))
		self.logger.debug('{} data error at alignment: {}'.format(dtype, row['comb_ann']))
		self.logger.debug('PTB Disf: {}\nLen: {} IndexTok: {}'.format(row[get_col('disf', 'ptb')], len(row[get_col('disf', 'ptb')]), self.ix['ptb']))
		self.logger.debug('PTB Sentence: {}\nLen: {} IndexDtok: {}'.format(row[get_col('token', 'ptb')], len(row[get_col('token', 'ptb')]), self.ix['ptb_dtok']))
		self.logger.debug('MS Disf: {}\nLen: {} IndexTok: {}'.format(row[get_col('disf', 'ms')], len(row[get_col('disf', 'ms')]), self.ix['ms']))
		self.logger.debug('MS Sentence: {}\nLen: {} IndexDtok: {}'.format(row[get_col('token', 'ms')], len(row[get_col('token', 'ms')]), self.ix['ms_dtok']))


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config", help="experiment config file")
	args = parser.parse_args()
	GenerateError(args)
