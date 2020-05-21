#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Simple class to generate the top N specified number of common words
given the alignment file.
"""

import sys
from collections import Counter
import pandas as pd

sys.path.append("..")
from data import read_tsv
import pickle


class Main:

    def __init__(self, alignments_file, output_file, top=100):
        print("Reading alignments", flush=True, end='\n')
        df = read_tsv(alignments_file)

        print("Counting sentences", flush=True, end='\n')
        sentences = df["sentence_dtok"].tolist()
        counts = Counter()
        for sent in sentences:
            for word in sent:
                if word != "//" and word != "--":
                    counts[word] += 1

        results = [x for x, _ in counts.most_common(top)]
        pickle.dump(set(results), open(out, 'wb'))
        print("Complete!")


if __name__ == "__main__":
    align = "/mnt//d//projects//swb_errors_surprisal//exp2//data//swbd_cont.tsv"
    out = "top-n.P"
    Main(align, out)
