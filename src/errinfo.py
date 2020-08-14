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
		self.top_n = None
		self.shapes = list()
		self.avg_shape = None
		self.disf = list()
		self.disf_current = False
		self.disf_prev = False
		self.disf_next = False
		self.nn_scores = list()
		self.ngram_scores = list()
		self.ngram_sup = None
		self.nn_sup = None

	def set_token(self, token, shape, split=False):
		if not split:
			self.tokens.append(token)
		if token.endswith('-'):
			self.shapes.append(Lex.OTHER.name)
		else:
			self.shapes.append(Lex(int(shape)).name)

	def set_score(self, ngram_value, nn_value):
		self.ngram_scores.append(ngram_value)
		self.nn_scores.append(nn_value)

	def set_disf(self, d):
		self.disf.append(d)

	def _summarize_shape(self):
		if len(self.shapes) > 1:
			if len(set(self.shapes[:-1])) == 1:
				self.avg_shape = self.shapes[0]
			else:
				self.avg_shape = Lex.MIX.name

	def _get_surprisal_value(self, other):  # if you are calculating it for PTB, then PTB should be self, MS other
		if len(self.ngram_scores) > 1:
			self.ngram_sup = util.get_sup_diff(self.ngram_scores, other.ngram_scores)
			self.nn_sup = util.get_sup_diff(self.nn_scores, other.nn_scores)

	def _check_top_n(self, top_n):
		if len(self.tokens) == 2 and self.tokens[0] in top_n:
			self.top_n = self.tokens[0]
		else:
			self.top_n = False

	def _set_disfluencies(self):
		if len(self.disf) > 1:
			nondisf = {'C', 'O'}
			temp = [x not in nondisf for x in self.disf]
			endpoint = len(self.disf)-1
			if temp[0]:
				self.disf_prev = True
			if any(temp[1:endpoint]):
				self.disf_current = True
			if temp[endpoint]:
				self.disf_next = True

	def make_summary(self, top_n, other):
		self._summarize_shape()
		self._set_disfluencies()
		self._check_top_n(top_n)
		self._get_surprisal_value(other)

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
		self.del_edge = False
		self.types = list()
		self.ptb = Trans()
		self.ms = Trans()

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

	def summarize(self, top_n):
		self._summarize_type()
		self.ptb.make_summary(top_n, other=self.ms)
		self.ms.make_summary(top_n, other=self.ptb)

	def add_type(self, value):
		self.types.append(value)

	# does not include list or ptb and ms Trans objects
	def get_header(self):
		return list(self.__dict__.keys())[:5]

	# does not include list or ptb and ms Trans objects
	def get_values(self):
		return list(self.__dict__.values())[:5]
