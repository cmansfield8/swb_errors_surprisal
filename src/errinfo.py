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
		self.shapes = list()
		self.nn_scores = list()
		self.ngram_scores = list()

	def summarize_shape(self):
		if len(set(self.shapes[:-1])) == 1:
			return self.shapes[0]
		return Lex.MIX.name
		
	def set_token(self, token, shape, split=False):
		if not split:
			self.tokens.append(token)
		self.shapes.append(Lex(int(shape)).name)
		
	def set_score(self, ngram_value, nn_value):
		self.ngram_scores.append(ngram_value)
		self.nn_scores.append(nn_value)
		
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
		self.avg_type = None
		self.avg_shape = None
		self.sup = None
		self.nn_sup = None
		self.error_type = list()
		self.del_edge = False
		self.ptb = Trans()
		self.ms = Trans()
		
	def _summarize_type(self):
		if 'SUB_MS' in self.error_type:
			self.avg_type = Err.SUB.name
		elif Err.DEL.name in self.error_type:
			self.avg_type = Err.DEL.name
		elif Err.INS.name in self.error_type:
			self.avg_type = Err.INS.name
			
	def _summarize_shape(self):
		avg_ptb = self.ptb.summarize_shape()
		avg_ms = self.ms.summarize_shape()
		if self.avg_type == Err.INS.name or avg_ptb == avg_ms:
			self.avg_shape = avg_ptb
		elif self.avg_type == Err.DEL.name:
			self.avg_shape = avg_ms
		else:
			self.avg_shape = Lex.MIX.name

	def _get_suprisal_value(self):
		s1, s2 = self.ptb, self.ms
		self.sup = util.get_sup_diff(s1.ngram_scores, s2.ngram_scores)
		self.nn_sup = util.get_sup_diff(s1.nn_scores, s2.nn_scores)

	def make_summary(self):
		self._summarize_type()
		self._summarize_shape()
		self._get_suprisal_value()
	
	def add_type(self, value):
		self.error_type.append(value)

	# does not include ptb and ms Trans objects
	def get_header(self):
		return list(self.__dict__.keys())[:-2]

	# does not include ptb and ms Trans objects
	def get_values(self):
		return list(self.__dict__.values())[:-2]
