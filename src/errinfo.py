#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Objects used to store and average information about errors.

TODO: calculate_surprisal method

"""


from enum import Enum


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

	# def get_overall_shape(self):
	#	if len(set(self.error_shape)) == 1:
	#		return ErrShape(self.error_shape[0])
	#	return ErrShape.MIX
		
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

	def __init__(self, index=None, transcriber=None):
		self.index = index
		self.transcriber = transcriber
		self.error_type = list()
		self.ptb = Trans()
		self.ms = Trans()
		
	#def get_overall_type(self):
	#	if "INS" in self.error_type and "DEL" in self.error_type:
	#		return ErrType.MIX
	#	elif "DEL" in self.error_type:
	#		return ErrType.DEL
	#	else:
	#		return ErrType.INS
		
	#def get_surprisal_result(self):
	#	result = dict()
	#	result['ngram'] = calculate_surprisal(self.ptb.ngram_score, self.ms.ngram_score)
	#	result['lstm'] = calculate_surprisal(self.ptb.lstm_score, self.ms.lstm_score)
	#	return result
	
	def add_type(self, value):
		self.error_type.append(value)
		
	def get_header(self):  # does not include ptb and ms objects, since these would not be printed
		return list(self.__dict__.keys())[:-2]

	def get_values(self):
		return list(self.__dict__.values())[:-2]
