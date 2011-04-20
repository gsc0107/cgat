################################################################################
#
#   MRC FGU Computational Genomics Group
#
#   $Id$
#
#   Copyright (C) 2009 Tildon Grant Belgard
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#################################################################################
"""
====================
ReadQc pipeline
====================

:Author: David Sims
:Release: $Id$
:Date: |today|
:Tags: Python

The readqc pipeline imports unmapped reads from one or more
fastq and performs basic quality control steps:

   1. per position quality
   2. per read quality
   3. duplicates

For further details see http://www.bioinformatics.bbsrc.ac.uk/projects/fastqc/

Usage
=====

See :ref:`PipelineSettingUp` and :ref:`PipelineRunning` on general information how to use CGAT pipelines.

Configuration
-------------

Input
-----

Reads are imported by placing files or linking to files in the :term:`working directory`.

The default file format assumes the following convention:

   <sample>-<condition>-<replicate>.<suffix>

``sample`` and ``condition`` make up an :term:`experiment`, while ``replicate`` denotes
the :term:`replicate` within an :term:`experiment`. The ``suffix`` determines the file type.
The following suffixes/file types are possible:

sra
   Short-Read Archive format. Reads will be extracted using the :file:`fastq-dump` tool.

fastq.gz
   Single-end reads in fastq format.

fastq.1.gz, fastq2.2.gz
   Paired-end reads in fastq format. The two fastq files must be sorted by read-pair.

.. note::

   Quality scores need to be of the same scale for all input files. Thus it might be
   difficult to mix different formats.



Requirements
------------

On top of the default CGAT setup, the pipeline requires the following software to be in the 
path:

+--------------------+-------------------+------------------------------------------------+
|*Program*           |*Version*          |*Purpose*                                       |
+--------------------+-------------------+------------------------------------------------+
|fastqc              |>=0.9.0            |read quality control                            |
+--------------------+-------------------+------------------------------------------------+
|sra-tools           |                   |extracting reads from .sra files                |
+--------------------+-------------------+------------------------------------------------+
|picard              |>=1.38             |bam/sam files. The .jar files need to be in your|
|                    |                   | CLASSPATH environment variable.                |
+--------------------+-------------------+------------------------------------------------+

Pipeline output
===============

The major output is a set of HTML pages and plots reporting on the quality of the sequence archive

Example
=======

Example data is available at http://www.cgat.org/~andreas/sample_data/pipeline_readqc.tgz.
To run the example, simply unpack and untar::

   wget http://www.cgat.org/~andreas/sample_data/pipeline_readqc.tgz
   tar -xvzf pipeline_readqc.tgz
   cd pipeline_readqc
   python <srcdir>/pipeline_readqc.py make full


Code
====

"""

# load modules
from ruffus import *
from rpy2.robjects import r as R

import Experiment as E
import logging as L
import Database
import sys, os, re, shutil, itertools, math, glob, time, gzip, collections, random
import numpy, sqlite3
import GTF, IOTools, IndexedFasta
import Tophat
import rpy2.robjects as ro
import PipelineGeneset
import PipelineMapping
import Stats
import PipelineTracks
import Pipeline as P

USECLUSTER = True

###################################################
###################################################
###################################################
## Pipeline configuration
###################################################

# load options from the config file
import Pipeline as P
P.getParameters( 
    ["%s.ini" % __file__[:-len(".py")],
     "../pipeline.ini",
     "pipeline.ini" ] )
PARAMS = P.PARAMS

#########################################################################
#########################################################################
#########################################################################
@follows(mkdir(PARAMS["exportdir"]), mkdir(os.path.join(PARAMS["exportdir"], "fastqc")) )
@transform( ("*.fastq.1.gz", 
              "*.fastq.gz",
              "*.sra"),
              regex( r"(\S+).(fastq.1.gz|fastq.gz|sra)"),
              r"\1.fastqc")
def runFastqc(infiles, outfile):
        '''convert sra files to fastq and check mapping qualities are in solexa format. 
           Perform quality control checks on reads from .fastq files.'''
        to_cluster = USECLUSTER
        m = PipelineMapping.fastqc()
        statement = m.build((infiles,), outfile) 
        P.run()

#########################################################################
#########################################################################
#########################################################################
@follows(mkdir("filtered_fastq"))
@transform( ("*.fastq.1.gz", 
              "*.fastq.gz",
              "*.sra"),
              regex( r"(\S+).(fastq.1.gz|fastq.gz|sra)"),
              r"filtered_fastq/\1_filt.\2")
def filterFastq(infiles, outfile):
        '''Filter FASTQ files to remove duplicates, low quality reads and artifacts using the FASTX Toolkit.'''
        to_cluster = USECLUSTER
        m = PipelineMapping.fastqFilter()
        statement = m.build((infiles,), outfile) 
        P.run()

#########################################################################
#########################################################################
#########################################################################
@merge( filterFastq, suffix(".txt"), "fastq_filter_stats.load" )
def loadFilterStats( infiles, outfile ):
    '''import fastq filter statistics.'''

    scriptsdir = PARAMS["general_scriptsdir"]
    header = "track,feature,feature_length,cov_mean,cov_median,cov_sd,cov_q1,cov_q3,cov_2_5,cov_97_5,cov_min,cov_max"
    filenames = " ".join(infiles)
    tablename = P.toTable( outfile )
    E.info( "loading coverage stats" )
    statement = '''cat %(filenames)s | sed -e /Track/D
            | python %(scriptsdir)s/csv2db.py %(csv2db_options)s
              --allow-empty
              --header=%(header)s
              --index=track
              --index=feature
              --table=%(tablename)s 
            > %(outfile)s
    '''
            
    P.run()
#########################################################################
#########################################################################
#########################################################################
@follows( runFastqc,
          filterFastq )
def full(): pass

@follows( mkdir( "report" ) )
def build_report():
    '''build report from scratch.'''

    E.info( "starting documentation build process from scratch" )
    P.run_report( clean = True )

@follows( mkdir( "report" ) )
def update_report():
    '''update report.'''

    E.info( "updating documentation" )
    P.run_report( clean = False )

if __name__== "__main__":
    sys.exit( P.main(sys.argv) )

