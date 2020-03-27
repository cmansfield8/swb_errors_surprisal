#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Objects used to store and average information about errors.

TODO: calculate_surprisal method

"""


from enum import Enum
import util


class ErrType(Enum):
	MIX = -1
	INS = 0
	DEL = 1

	
class ErrShape(Enum):
	MIX = -1
	FUNCTION = 0
	CONTENT = 1
	DISCOURSE = 2
	

class Trans:

	def __init__(self):
		self.tokens = list()
		self.error_shapes = list()
		self.lstm_scores = list()
		self.scores = list()

	def summarize_shape(self):
		if len(set(self.error_shapes)) == 1:
			return self.error_shapes[0]
		return ErrShape.MIX.value
		
	def set_token(self, token, shape):
		self.tokens.append(token)
		self.error_shapes.append(shape)
		
	def set_score(self, ngram_value, lstm_value):
		self.scores.append(ngram_value)
		self.lstm_scores.append(lstm_value)
		
	def get_header(self, dataset):
		keys = list(self.__dict__.keys())
		return [dataset + "_" + x for x in keys]
		
	def get_values(self):
		return list(self.__dict__.values())
	

class ErrSeq:

	def __init__(self):
		self.index = None
		self.transcriber = None
		self.avg_type = None
		self.avg_shape = None
		self.sup = None
		self.lstm_sup = None
		self.error_type = list()
		self.ptb = Trans()
		self.ms = Trans()
		
	def _summarize_type(self):
		if "INS" in self.error_type and "DEL" in self.error_type:
			self.avg_type = ErrType.MIX.value
		elif "DEL" in self.error_type:
			self.avg_type = ErrType.DEL.value
		else:
			self.avg_type = ErrType.INS.value
			
	def _summarize_shape(self):
		if self.avg_type == ErrType.MIX.value:
			self.avg_shape = ErrShape.MIX.value
		elif self.avg_type == ErrType.INS.value:
			self.avg_shape = self.ptb.summarize_shape()
		else:
			self.avg_shape = self.ms.summarize_shape()
			
	def _get_surprisal_value(self):
		# scores are inversed based on if it's an INS/SUB or DEL/SUB
		if self.avg_type == ErrType.DEL.value:
			s1, s2 = self.ms, self.ptb
		else:
			s1, s2 = self.ptb, self.ms
		self.sup = util.get_sup_diff(s1.scores, s2.scores)
		self.lstm_sup = util.get_sup_diff(s1.lstm_scores, s2.lstm_scores)
		
	def summarize(self):
		self._summarize_type()
		self._summarize_shape()
		self._get_surprisal_value()
	
	def add_type(self, value):
		self.error_type.append(value)
		
	def get_header(self):  # does not include ptb and ms objects, since these would not be printed
		return list(self.__dict__.keys())[:-2]

	def get_values(self):
		return list(self.__dict__.values())[:-2]
