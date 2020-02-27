#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
General useful scripts for error analysis.
"""


import logging
import yaml
import pandas as pd


def get_config(config_file):
    with open(config_file, 'r') as stream:
        return yaml.safe_load(stream)


def get_logger(debug):
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
        
    logger = logging.getLogger()
    logger.setLevel(level)
    
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger


def read_metadata(metadata_file):
    df = pd.read_csv(metadata_file, header=0)
    df.index = df['FILE']
    d = df.to_dict()
    result = d['TRANSCRIBER']
    result = {int(f): t for f, t in result.items()}
    return result
