"""
Author: coman8@uw.edu

Preprocessing the PTB and MS alignments before it is sent on its merry way downstream.

This file expects the alignment which does not have weird duplicate quotation marks.
Run this first:
sed -r "/'\"+([a-z]+)\"+'/ s//'\1'/g" $INPUT > $OUTPUT

cont        Match stylistic differences in ptb and ms.  It updates the ptb tokens
            AND the combined tokens, leaving behind a CONT marker so you know things
            were updated there. This includes fixing the annotations to ignore
            differences between WANT TO and GOING TO.
detokenize  'you_know' and CONTRACTIONS are joined.  WANT TO and GOING to are never
            joined.
"""

import argparse
from collections import defaultdict
from data import read_tsv
import util


def update_ids(sent, tok_ids):
    YOU_KNOW = ('you', 'know')
    REDUCED = [('want', 'to'), ('going', 'to')]
    result = list()
    i = 1
    while i <= len(sent):
        current = (sent[i - 1], sent[i]) if i < len(sent) else None
        if current and current[0] == '---':
            result.append('None')
        elif current == YOU_KNOW:
            result.append(tok_ids[i - 1] + '_a')
            result.append(tok_ids[i] + '_b')
            i += 1  # skip ahead since appending at i
        elif current in REDUCED and \
                tok_ids[i - 1].endswith('_a') and tok_ids[i].endswith('_b'):
            result.append(tok_ids[i - 1] + '0')
            result.append(tok_ids[i] + '0')
            i += 1  # skip ahead since appending at i
        else:
            result.append(tok_ids[i - 1])
        i += 1
    return result


def update_names(row, sent_col, tok_ids_col):
    sent = row[sent_col]
    tok_ids = row[tok_ids_col]
    words = set(sent)
    if 'you' in words and 'know' in words or \
            'want' in words and 'to' in words or \
            'going' in words and 'to' in words or \
            '---' in words:
        return update_ids(sent, tok_ids)
    return tok_ids


def update_cont(row):
    if 'CONT_MS' in set(row['comb_ann']):
        ix = defaultdict(int)
        ix['ptb'], ix['ms'] = 0, 0
        temp = defaultdict(list)

        for i in range(len(row['comb_ann'])):
            label = row['comb_ann'][i]
            # the ptb tokens stay as is if it's not a CONT
            if util.is_ptb(label) and label != 'CONT_TREE':
                temp['sent'].append(row['sentence'][ix['ptb']])
                temp['names'].append(row['names'][ix['ptb']])
            # an MS cont is added to the ptb tokens (cont_ms uses a CONT annotation)
            if label == 'CONT_MS':
                temp['sent'].append(row['ms_sentence'][ix['ms']])
                temp['names'].append(row['ms_names'][ix['ms']])
                temp['comb'].append(row['comb_sentence'][i])
                temp['ann'].append('CONT')
            # for all normal labels, keep annotation the same (cont_tree has no annotation)
            if not label.startswith('CONT'):
                temp['comb'].append(row['comb_sentence'][i])
                temp['ann'].append(row['comb_ann'][i])

            # move indices forward
            if util.is_ptb(label):
                ix['ptb'] += 1
            if util.is_ms(label):
                ix['ms'] += 1
        row['sentence'] = temp['sent']
        row['names'] = temp['names']
        row['comb_ann'] = temp['ann']
        row['comb_sentence'] = temp['comb']
    return row


def update_reductions(row):
    pattern1 = ['going', 'to', 'going', 'to']
    pattern2 = ['want', 'to', 'want', 'to']
    target = ['SUB_MS', 'SUB_MS', 'SUB_TREE', 'INS']
    temp = defaultdict(list)
    i = 0
    while i < len(row['comb_ann']):
        if i + 4 < len(row['comb_ann']) and row['comb_ann'][i:i+4] == target \
                and row['comb_sentence'][i:i+4] == pattern1 or row['comb_sentence'][i:i+4] == pattern2:
            temp['ann'].extend(['CONT', 'CONT'])
            temp['comb'].extend([row['comb_sentence'][i], row['comb_sentence'][i+1]])
            i += 3
        else:
            temp['ann'].append(row['comb_ann'][i])
            temp['comb'].append(row['comb_sentence'][i])
        i += 1
    row['comb_ann'] = temp['ann']
    row['comb_sentence'] = temp['comb']
    return row


def detokenize(row, sent_col, tok_ids_col):
    if any([(x.endswith('_a') or x == 'None') for x in row[tok_ids_col]]):
        temp = list()
        i = 0
        while i < len(row[tok_ids_col]):
            label = row[tok_ids_col][i]
            if label.endswith('_a'):
                # join 'you' 'know' tokens with an underscore
                if row[sent_col][i] == 'you' and row[sent_col][i + 1] == 'know':
                    temp.append(row[sent_col][i] + '_' + row[sent_col][i + 1])
                # join contractions
                else:
                    temp.append(row[sent_col][i] + row[sent_col][i + 1])
                i += 1
            elif label != 'None':
                temp.append(row[sent_col][i])
            i += 1
        return temp
    return row[sent_col]


def preprocess(args):
    df = read_tsv(args.file)

    print('Updating IDs')
    token_pairs = [('sentence', 'names'), ('ms_sentence', 'ms_names')]
    for sent_col, tok_ids_col in token_pairs:
        df[tok_ids_col] = df.apply(lambda x: update_names(x, sent_col, tok_ids_col),
                                   axis=1)

    if args.cont:
        print('Updating style differences')
        df = df.apply(lambda x: update_cont(x), axis=1)
        df = df.apply(lambda x: update_reductions(x), axis=1)

    if args.detokenize:
        print('Detokenizing values')
        for sent_col, tok_ids_col in token_pairs:
            df[sent_col + '_dtok'] = df.apply(lambda x: detokenize(x, sent_col, tok_ids_col), axis=1)

    df.to_csv(args.output, sep='\t', index=None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="original alignments file")
    parser.add_argument("output", help="output file")
    parser.add_argument("-c", "--cont",
                        help="fix style difference between ptb and ms to match ms",
                        action='store_true')
    parser.add_argument("-d", "--detokenize",
                        help="Combine forms such as contractions and remove special chars.",
                        action='store_true')
    args = parser.parse_args()
    preprocess(args)
