#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Pull errors from alignment with their surprisal LLR.

"""

import sys  # TODO remove after debug
import argparse
from collections import defaultdict
import data
import util
from errinfo import ErrSeq, Lex


def verify_sequence(sequence):
	return True


# if is empty sentence: # make these all enums
#	return 1
# elif is end deletion:
#	return 2
# elif lif label.startswith('CONT'):
#	return 3


def verify_token(token):
	return not util.is_contraction(token) and not util.is_special_char(token)


def get_col(datatype, is_ms=True):
	if is_ms:
		data = 'ms'
	else:
		data = 'ptb'
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
		logger = util.get_logger(config['debug'])

		# load the switchboard file
		alignment = data.load_data(config, logger)
		alignment = alignment.head(40)  # TESTING
		logger.info('Processing errors...')

		err_labels = ['INS', 'DEL', 'SUB_TREE', 'SUB_MS']
		result = list()  # list of structured error objects

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
				if self.ix['ptb'] < len(row[get_col('name', is_ms=False)]):
					name = row[get_col('name', is_ms=False)][self.ix['ptb']]
				if self.ix['ms'] < len(row[get_col('name')]):
					ms_name = row[get_col('name')][self.ix['ms']]
				if name == 'None' and ms_name == 'None':
					self.flags.special_tok = True
				# so we don't dupe tokenized token scores
				if name.endswith('_a'):
					self.flags.ptb_split = True
				if ms_name.endswith('_a'):
					self.flags.ms_split = True

				if not self.flags.special_tok:
					# a new error or another error in current error sequence
					if label in err_labels:
						current = self.process_error(i, row, label, current)
						self.flags.prev_error = True

					# add the token after the error sequence
					elif self.flags.prev_error:
						current = self.process_error(i, row, label, current)
						# on to new errors if it's not a split
						if not self.flags.ptb_split and not self.flags.ms_split:
							current.make_summary()
							result.append(current)
							self.flags.prev_error = False
							current = ErrSeq()

				if util.is_ptb(label):
					self.ix['ptb'] += 1
					if not self.flags.special_tok and not self.flags.ptb_split:
						self.ix['ptb_dtok'] += 1
				if util.is_ms(label):
					self.ix['ms'] += 1
					if not self.flags.special_tok and not self.flags.ms_split:
						self.ix['ms_dtok'] += 1

			# add an EOS token after the error sequence in needed
			if self.flags.prev_error:
				label = util.get_norm_label()
				self.flags.eos = True
				current = self.process_error(i, row, label, current)
				current.make_summary()
				result.append(current)

		logger.info('Error sequences found: {}'.format(str(len(result))))
		# logger.debug(data.sample_results(result, 0))  TODO: debug

		data.write_tsv(config, logger, result)

	def process_helper(self, i, row, current_dtype, is_ms=True):
		if is_ms:
			prefix = 'ms_'
		else:
			prefix = 'ptb_'

		eos_token = '<EOS>'
		token = eos_token
		shape = Lex.EOS.value

		if not self.flags.eos:
			try:
				token = row[get_col('token', is_ms)][self.ix[prefix + 'dtok']]
				shape = row[get_col('shape', is_ms)][self.ix[prefix + 'dtok']]
			except IndexError as e:
				self.debug_report(e, row, i, is_ms)
				raise

		current_dtype.set_token(token, shape)
		current_dtype.set_score(0.40, 0.45)  # placeholder
		# score = row[get_col('score', is_ms)][self.ix[prefix + 'ngram_score']]
		# nn_score = row[get_col('nn_score', is_ms)][self.ix[prefix + 'nn_score']]
		# current_dtype.set_score(score, nn_score)
		return current_dtype

	def process_error(self, i, row, label, current):
		# add basic info if it's a new error
		if not self.flags.prev_error:
			current.index = i
			current.transcriber = row['transcriber']

		# always add annotation info
		current.add_type(label)

		# it's a ptb-related error or it's the following word
		if util.is_ptb(label) or util.non_error(label):
			if not self.flags.ptb_split:
				current.ptb = self.process_helper(i, row, current.ptb, is_ms=False)

		# it's an ms-related error or it's the following word
		if util.is_ms(label) or util.non_error(label):
			if not self.flags.ms_split:
				current.ms = self.process_helper(i, row, current.ms)

		return current

	def debug_report(self, e, row, i, ms=True):
		"""in case of indexing error, includes some useful info"""
		print('Index: {}'.format(i))

		if ms:
			label = 'ms'
		else:
			label = 'ptb'

		print('{} data error at alignment: {}'.format(label, row['comb_ann']))
		print('PTB Name: {}\n IndexTok: {}'.format(row[get_col('name', ms=False)], self.ix['ptb']))
		print('PTB Sentence: {}\n IndexDtok: {}'.format(row[get_col('token', ms=False)], self.ix['ptb_dtok']))
		print('MS Name: {}\n IndexTok: {}'.format(row[get_col('name')], self.ix['ms']))
		print('MS Sentence: {}\n IndexDtok: {}'.format(row[get_col('token')], self.ix['ms_dtok']))


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config", help="experiment config file")
	args = parser.parse_args()
	GenerateError(args)
