#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Pull errors from alignment with their surprisal LLR.

"""


import sys # TODO remove after debug
import argparse
from collections import defaultdict
import data, util
from errinfo import ErrSeq
	

def verify_token(token):
	return (not util.is_contraction(token) and not util.is_special_char(token))


def get_col(type, ms=True):
	if ms:
		data = 'ms'
	else:
		data = 'ptb'
	d = {
		('ptb', 'token'):'sentence',
		('ms', 'token'):'ms_sentence',
		('ptb', 'shape'):'ptb_shapes',
		('ms', 'shape'):'ms_shapes',
		('ptb', 'score'):'swb-ngram_ptb_scores',
		('ms', 'score'):'swb-ngram_ms_scores',
		('ptb', 'lstm_score'):'swb-lstm_ptb_scores',
		('ms', 'lstm_score'):'swb-lstm_ms_scores',
		}
	return d[(data, type)]
		

class GenerateError:

	def __init__(self, args):
		self.ms_forward= ['DEL', 'SUB_MS', 'CONT_MS']
		self.ptb_forward = ['INS', 'SUB_TREE', 'CONT_TREE']
		
		config = util.get_config(args.config)
		logger = util.get_logger(config['debug'])
		
		self.transcribers = util.read_metadata(config['metadata_file'])
		
		# load the switchboard file
		alignment = data.load_data(config, logger)
		logger.info('Processing errors...')
		
		err_labels = ['INS', 'DEL', 'SUB_TREE', 'SUB_MS']
		non_error='O'
		result = list()
		
		for i, row in alignment.iterrows():
			self.ix = defaultdict(int)
		
			current = ErrSeq()
			prev_error = False
			for j in range(len(row['comb_ann'])):
				self.ix['comb'] = j
				label = row['comb_ann'][j]
				current_token = row['comb_sentence'][j]
				is_token = verify_token(current_token)
				is_contraction = util.is_contraction(current_token)
							
				# the current error is either new or part of an error sequence
				if label in err_labels and is_token:
					current = self.process_error(i, row, label, current, prev_error)
					prev_error = True
					
				# the current token is not a valid error but it is part of the error sequence
				elif prev_error:
					# the error ends in a regular token - save it as the end of the sequence
					if label == non_error and is_token:
						current = self.process_error(i, row, label, current, prev_error, last=True)
						result.append(current)
						prev_error = False
						current = ErrSeq()
					# if error ends in a cont we will discard it
					if label.startswith('CONT'):
						prev_error = False
						current = ErrSeq()

				if label == non_error:
					self.ix['ptb'] += 1
					self.ix['ptb_score'] += int(is_token)
					self.ix['ms'] += 1
					self.ix['ms_score'] += int(is_token)
				elif label in self.ptb_forward:
					self.ix['ptb'] += 1
					self.ix['ptb_score'] += int(is_token)
				elif label in self.ms_forward:
					self.ix['ms'] += 1
					self.ix['ms_score'] += int(is_token)
			
			# the error is at the end of the sentence
			if prev_error:
				current = self.process_error(i, row, label, current, prev_error, last=True, eos=True)
				result.append(current)
			prev_error = False
			current = ErrSeq()
				
		logger.info('Error sequences found: {}'.format(str(len(result))))
		# logger.debug(data.sample_results(result, 0))
		
		# stats = get_statistics(results, logger)  TODO: run all the calculations, and the exceptions
		data.write_tsv(config, logger, result)
		
	
	def process_error(self, i, row, label, current, prev_error, last=False, eos=False):
		eos_token = '<EOS>'
		token = eos_token
		shape = eos_token
		
		if not prev_error:	# record aggregate info at start of error
			current.index=i
			current.transcriber=row['transcriber']
			
		if not last:  # get error type unless it's the word following the error
			current.add_type(row['comb_ann'][self.ix['comb']])
			
		if label in self.ptb_forward or last:  # hallucination/ptb sub/following word
			if not eos:
				try:
					token = row[get_col('token', ms=False)][self.ix['ptb']]
					shape = row[get_col('shape', ms=False)][self.ix['ptb_score']]
				except IndexError as e:
					self.print_report(e, row, i, label, ms=False)
					raise
			current.ptb.set_token(token, shape)
			
			current.ptb.set_score(0.40, 0.45)  # placeholder
			# score = row[get_col('score', ms=False)][self.ix['ptb_score']]
			# lstm_score = row[get_col('lstm_score', ms=False)][self.ix['ptb_score']]
			# current.ptb.set_score(score, lstm_score)
			
		if label in self.ms_forward or last:  # miss/ms sub/following word
			if not eos:
				try:
					token = row[get_col('token')][self.ix['ms']]
					shape = row[get_col('shape')][self.ix['ms_score']]
				except IndexError as e:
					self.print_report(e, row, i, label)
					raise
			current.ms.set_token(token, shape)
			
			# score = row[get_col('score')][self.ix['ms_score']]
			# stm_score = row[get_col('lstm_score')][self.ix['ms_score']]
			# current.ms.set_score(score, lstm_score)
			current.ms.set_score(0.20, 0.25)  # placeholder
		return current
		
	def print_report(self, e, row, i, label, ms=True):	# temporary debug
		print(e)
		print(i)
		if ms:
			print('ms')
		if not ms:
			print('ptb')
		print(label)
		print(row['comb_ann'])
		print('PTB Sentence: {}\n Index1: {}'.format(row[get_col('token', ms=False)], self.ix['ptb']))
		print('PTB Shape: {}\n Index2: {}'.format(row[get_col('shape', ms=False)], self.ix['ptb_score']))
		print('MS Sentence: {}\n Index1: {}'.format(row[get_col('token')], self.ix['ms']))
		print('MS Shape: {}\n Index2: {}'.format(row[get_col('shape')], self.ix['ms_score']))




if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config", help="experiment config file")
	args = parser.parse_args()
	GenerateError(args)
