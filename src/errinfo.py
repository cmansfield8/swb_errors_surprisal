#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Objects used to store and average information about errors.

"""


from enum import Enum
import util


class Err(Enum):
	INS = 0
	DEL = 1
	SUB = 2
	MIX = 3

	
class Lex(Enum):
	EOS = -2
	MIX = -1
	FUNC = 0
	CON = 1
	DISC = 2
	OTHER = 3


class Trans:

	def __init__(self):
		self.tokens = list()
		self.nn_scores = list()
		self.ngram_scores = list()
		self.shapes = list()
		self.disf = list()

	def set_token(self, token, shape, split=False):
		if not split:
			self.tokens.append(token)
		self.shapes.append(Lex(int(shape)).name)

	def set_score(self, ngram_value, nn_value):
		self.ngram_scores.append(ngram_value)
		self.nn_scores.append(nn_value)

	def set_disf(self, d):
		self.disf.append(d)

	def get_header(self, dtype):
		if dtype == 'ptb':
			prefix = ''
		else:
			prefix = 'ms_'
		keys = list(self.__dict__.keys())
		return [prefix + x for x in keys]
		
	def get_values(self):
		return list(self.__dict__.values())


class ErrSeq:

	def __init__(self):
		self.index = None
		self.transcriber = None
		self.error_type = None
		self.avg_shape = None
		self.sup = None
		self.nn_sup = None
		self.top_n = None
		self.disf = False
		self.disf_prev = False
		self.disf_next = False
		self.del_edge = False
		self.types = list()

		self.ptb = Trans()
		self.ms = Trans()

	def _summarize_shape(self, shapes):
		if len(set(shapes[:-1])) == 1:
			self.avg_shape = shapes[0]
		else:
			self.avg_shape = Lex.MIX.name

	def _summarize_type(self):
		t = set(self.types)
		if 'INS' not in t and 'DEL' not in t:
			self.error_type = Err.SUB.name
		elif 'SUB_MS' not in t and 'DEL' not in t:
			self.error_type = Err.INS.name
		elif 'SUB_MS' not in t and 'INS' not in t:
			self.error_type = Err.DEL.name
		else:
			self.error_type = Err.MIX.name

	def _get_surprisal_value(self, dtype):
		if dtype == 'ptb':
			s1, s2 = self.ptb, self.ms
		else:
			s1, s2 = self.ms, self.ptb
		self.sup = util.get_sup_diff(s1.ngram_scores, s2.ngram_scores)
		self.nn_sup = util.get_sup_diff(s1.nn_scores, s2.nn_scores)

	def _check_top_n(self, tokens, top_n):
		if len(tokens) == 2 and tokens[0] in top_n:
			self.top_n = tokens[0]
		else:
			self.top_n = False

	def _set_disfluencies(self, disfluencies, temp):
		nondisf = {'C', 'O'}
		temp = [x not in nondisf for x in disfluencies]
		endpoint = len(disfluencies)-1
		if temp[0]:
			self.disf_prev = True
		if endpoint > 0 and any(temp[1:endpoint]):
			self.disf = True
		if endpoint > 0 and temp[endpoint]:
			self.disf_next = True


	def make_summary(self, top_n, dtype):
		if dtype == 'ptb':
			temp = self.ptb
		else:
			temp = self.ms
		self._summarize_type()
		self._summarize_shape(temp.shapes)
		self._set_disfluencies(temp.disf, temp)
		self._check_top_n(temp.tokens, top_n)
		self._get_surprisal_value(dtype)


	def add_type(self, value):
		self.types.append(value)

	# does not include list or ptb and ms Trans objects
	def get_header(self):
		return list(self.__dict__.keys())[:12]

	# does not include list or ptb and ms Trans objects
	def get_values(self):
		return list(self.__dict__.values())[:12]
