"""Pathogen-profiler

Set of classes and functions to help create a
script which profiles Pathogen NGS data.
"""

from .profiler import bam_profiler
from .bam import bam 
from .fasta import fasta
from .fastq import fastq

__all__ = ['bam','bam_profiler','fasta','fastq']