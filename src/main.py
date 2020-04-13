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


def get_col(datatype, ms=True):
	if ms:
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


class GenerateError:

	def __init__(self, args):
		config = util.get_config(args.config)
		logger = util.get_logger(config['debug'])

		# load the switchboard file
		alignment = data.load_data(config, logger)
		logger.info('Processing errors...')

		err_labels = ['INS', 'DEL', 'SUB_TREE', 'SUB_MS']
		result = list()

		# for each slash unit
		for i, row in alignment.iterrows():
			self.ix = defaultdict(int)

			current = ErrSeq()
			prev_error = False

			# for each part of the alignment
			for j in range(len(row['comb_ann'])):
				self.ix['ann'] = j
				label = row['comb_ann'][self.ix['ann']]

				# if it's first part of contraction or special char, do not use
				# TODO: check if this is too hacky
				special_tok = False
				for dtype, cond in [('ptb', False), ('ms', True)]:
					if self.ix[dtype] < len(row[get_col('name', cond)]):
						name = row[get_col('name', cond)][self.ix[dtype]]
						if name == 'None' or name.endswith('_a'):
							special_tok = True

				if not special_tok:
					# a new error or another error in current error sequence
					if label in err_labels:
						current = self.process_error(i, row, label, current, prev_error)
						prev_error = True

					# add the token after the error sequence
					elif prev_error:
						current = self.process_error(i, row, label, current, prev_error, last=True)
						current.make_summary()
						result.append(current)
						# start fresh
						prev_error = False
						current = ErrSeq()

				if util.is_ptb(label):
					self.ix['ptb'] += 1
					if not special_tok:
						self.ix['ptb_dtok'] += 1
				if util.is_ms(label):
					self.ix['ms'] += 1
					if not special_tok:
						self.ix['ms_dtok'] += 1

			# add an EOS token after the error sequence in needed
			if prev_error:
				current = self.process_error(i, row, label, current, prev_error, last=True, eos=True)
				current.make_summary()
				result.append(current)
			# start fresh
			prev_error = False
			current = ErrSeq()

		logger.info('Error sequences found: {}'.format(str(len(result))))
		# logger.debug(data.sample_results(result, 0))  TODO: debug

		data.write_tsv(config, logger, result)

	def process_helper(self, i, row, label, current_dtype, eos, ms=True):
		if ms:
			prefix = 'ms_'
		else:
			prefix = 'ptb_'

		eos_token = '<EOS>'
		token = eos_token
		shape = Lex.EOS.value

		if not eos:
			try:
				token = row[get_col('token', ms)][self.ix[prefix + 'dtok']]
				shape = row[get_col('shape', ms)][self.ix[prefix + 'dtok']]
			except IndexError as e:
				self.debug_report(e, row, i, label, ms)
				raise
		current_dtype.set_token(token, shape)
		current_dtype.set_score(0.40, 0.45)  # placeholder
		# score = row[get_col('score', ms)][self.ix[prefix + 'ngram_score']]
		# nn_score = row[get_col('nn_score', ms)][self.ix[prefix + 'nn_score']]
		# current_dtype.set_score(score, nn_score)
		return current_dtype

	def process_error(self, i, row, label, current, prev_error, last=False, eos=False):

		# add basic info if it's a new error
		if not prev_error:
			current.index = i
			current.transcriber = row['transcriber']

		# include info related to errors unless it's the following word
		if not last:
			current.add_type(row['comb_ann'][self.ix['ann']])

		# it's a ptb-related error or it's the following word
		if util.is_ptb(label) or last:
			current.ptb = self.process_helper(i, row, label, current.ptb, eos, ms=False)

		# it's an ms-related error or it's the following word
		if util.is_ms(label) or last:
			current.ms = self.process_helper(i, row, label, current.ms, eos, ms=True)

		return current

	def debug_report(self, e, row, i, label, ms=True):
		"""in case of indexing error, includes some useful info"""
		print('Index: {}'.format(i))

		if ms:
			label = 'ms'
		if not ms:
			label = 'ptb'

		print('{} error at label {}'.format(label, row['comb_ann']))
		print('PTB Name: {}\n IndexTok: {}'.format(row[get_col('name', ms=False)], self.ix['ptb']))
		print('PTB Sentence: {}\n IndexDtok: {}'.format(row[get_col('token', ms=False)], self.ix['ptb_dtok']))
		print('MS Name: {}\n IndexTok: {}'.format(row[get_col('name')], self.ix['ms']))
		print('MS Sentence: {}\n IndexDtok: {}'.format(row[get_col('token')], self.ix['ms_dtok']))


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config", help="experiment config file")
	args = parser.parse_args()
	GenerateError(args)
