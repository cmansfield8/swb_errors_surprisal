"""Fetches metadata from switchboard files, checks that metadata info is complete, prints
csv of metadata."""

import os
import pandas as pd
import re


class Main:

    def __init__(self, source):
        self.d = {}
        self.df = pd.DataFrame()
        labels = ["FILENAME", "TOPIC#", "DATE", "TRANSCRIBER", "DIFFICULTY", "TOPICALITY", "NATURALNESS", "ECHO_FROM_B",
                  "ECHO_FROM_A", "STATIC_ON_A", "STATIC_ON_B", "BACKGROUND_A", "BACKGROUND_B", "REMARKS"]

        for filename in os.listdir(source):
            with open(os.path.join(source, filename)) as in_file:
                lines = in_file.readlines()

                # find start of metadata lines
                i = 0
                while i < len(lines) and not lines[i].startswith("FILENAME"):
                    i += 1

                # store metadata in dictionary
                while i < len(lines) and not lines[i].startswith("=="):
                    if len(lines[i].split()) > 1:
                        key = lines[i].split(':')[0]
                        for label in labels:  # a fix for odd characters showing up in metadata labels
                            if label in key:
                                key = label
                        value = re.split(r":[\s|\t]*", lines[i])[1][:-1].strip()
                        if key == "REMARKS":
                            while i+1 < len(lines) and not lines[i+1].startswith("==") and len(lines[i+1].split()) > 1:
                                i += 1
                                value += ' ' + lines[i].strip()
                        self.d[key] = value
                    i += 1

                # check for missing metadata
                excluded_labels = list(set(labels).difference(set(self.d.keys())))

                if len(excluded_labels) > 0:
                    print('{} does not include keys: {}'.format(filename, excluded_labels))

                # merge data into dataframe
                temp = pd.DataFrame.from_records(self.d, index=[(os.path.splitext(filename)[0])])
                self.df = pd.concat([self.df, temp])
                self.df.index.rename('FILE', inplace=True)

    def get_df(self):
        return self.df

    def get_dict(self):
        return self.d

    def print_csv(self, out_file):
        self.df.to_csv(out_file)
