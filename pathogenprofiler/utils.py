import sys
import os.path
import subprocess
from collections import defaultdict
import random
import math
import re
rand_generator = random.SystemRandom()


def infolog(x):
    sys.stderr.write('\033[94m' + str(x) + '\033[0m' + '\n')

def errlog(x,ext=False):
    sys.stderr.write('\033[91m' + str(x) + '\033[0m' + '\n')
    if ext==True:
        quit(1)

def successlog(x):
    sys.stderr.write('\033[92m' + str(x) + '\033[0m' + '\n')

def warninglog(x):
    sys.stderr.write('\033[93m' + str(x) + '\033[0m' + '\n')    

def debug(x):
    sys.stderr.write('\033[93m' + str(x) + '\033[0m' + '\n')


def reformat_mutations(x,vartype,gene,gene_info):
    aa_short2long = {
    'A': 'Ala', 'R': 'Arg', 'N': 'Asn', 'D': 'Asp', 'C': 'Cys', 'Q': 'Gln',
    'E': 'Glu', 'G': 'Gly', 'H': 'His', 'I': 'Ile', 'L': 'Leu', 'K': 'Lys',
    'M': 'Met', 'F': 'Phe', 'P': 'Pro', 'S': 'Ser', 'T': 'Thr', 'W': 'Trp',
    'Y': 'Tyr', 'V': 'Val', '*': '*', '-': '-'
    }
    # big Deletion
    # Chromosome_3073680_3074470
    if "large_deletion" in vartype:
        re_obj = re.search("([0-9]+)_([0-9]+)",x)
        if re_obj:
            start = re_obj.group(1)
            end = re_obj.group(2)
            return "Chromosome:g.%s_%sdel" % (start,end)
    # Substitution
    # 450S>450L
    if "missense" in vartype or "start_lost" in vartype or "stop_gained" in vartype:
        re_obj = re.search("([0-9]+)([A-Z\*])>([0-9]+)([A-Z\*])",x)
        if re_obj:
            codon_num = int(re_obj.group(1))
            ref = aa_short2long[re_obj.group(2)]
            alt = aa_short2long[re_obj.group(4)]
            return "p.%s%s%s" % (ref,codon_num,alt)
        # Deletion
        # 761100CAATTCATGG>C
    if "frame" in vartype:
        re_obj = re.search("([0-9]+)([A-Z][A-Z]+)>([A-Z])",x)
        if re_obj:
            chr_pos = int(re_obj.group(1))
            ref = re_obj.group(2)
            alt = re_obj.group(3)
            strand = "-" if gene[-1]=="c" else "+"
            del_len = len(ref)-len(alt)
            if strand == "+":
                gene_start = gene_info[chr_pos] + 1
                gene_end = gene_start + del_len - 1
                return "c.%s_%sdel" % (gene_start,gene_end)
            else:
                gene_start = gene_info[chr_pos+del_len]
                gene_end = gene_info[chr_pos] -1
                return "c.%s_%sdel" % (gene_start,gene_end)
        # Insertion
        # 1918692G>GTT
        re_obj = re.search("([0-9]+)([A-Z])>([A-Z][A-Z]+)",x)
        if re_obj:
            chr_pos = int(re_obj.group(1))
            ref = re_obj.group(2)
            alt = re_obj.group(3)
            strand = "-" if gene[-1]=="c" else "+"
            if strand == "+":
                gene_start = gene_info[chr_pos]
                gene_end = gene_start + 1
                return "c.%s_%sins%s" % (gene_start,gene_end,alt[1:])
            else:
                gene_start = gene_info[chr_pos] - 1
                gene_end = gene_info[chr_pos]
                return "c.%s_%sins%s" % (gene_start,gene_end,revcom(alt[1:]))
    if "non_coding" in vartype:
        re_obj = re.match("([0-9]+)([A-Z]+)>([A-Z]+)",x)
        if re_obj:
            gene_pos = int(re_obj.group(1))
            ref = re_obj.group(2)
            alt = re_obj.group(3)
            return "r.%s%s>%s" % (gene_pos,ref.lower(),alt.lower())
        re_obj = re.match("(\-[0-9]+)([A-Z]+)>([A-Z]+)",x)
        if re_obj:
            gene_pos = int(re_obj.group(1))
            ref = re_obj.group(2)
            alt = re_obj.group(3)
            strand = "-" if gene[-1]=="c" else "+"
            if strand=="+":
                return "c.%s%s>%s" % (gene_pos,ref,alt)
            else:
                return "c.%s%s>%s" % (gene_pos,revcom(ref),revcom(alt))
    if "synonymous" in vartype:
        re_obj = re.search("([\-0-9]+)([A-Z])>([A-Z])",x)
        if re_obj:
            return "c.%s" % (x)
    return x

def get_seqs_from_bam(bamfile):
    seqs = []
    for l in cmd_out("samtools view %s -H | grep ^@SQ" % bamfile):
        row = l.rstrip().split()
        seqs.append(row[1].replace("SN:",""))
    return seqs


def revcom(s):
        """Return reverse complement of a sequence"""
        def complement(s):
                        basecomplement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'N': 'N'}
                        letters = list(s)
                        letters = [basecomplement[base] for base in letters]
                        return ''.join(letters)
        return complement(s[::-1])


def stdev(arr):
    mean = sum(arr)/len(arr)
    return math.sqrt(sum([(x-mean)**2 for x in arr])/len(arr))


def add_arguments_to_self(self,args):
    for x in args:
        if x == "self":
            continue
        vars(self)[x] = args[x]
    if "kwargs" in args:
        for x in args["kwargs"]:
            vars(self)[x] = args["kwargs"][x]


def cmd_out(cmd,verbose=1):
    cmd = "set -u pipefail; " + cmd
    if verbose==2:
        sys.stderr.write("\nRunning command:\n%s\n" % cmd)
        stderr = open("/dev/stderr","w")
    elif verbose==1:
        sys.stderr.write("\nRunning command:\n%s\n" % cmd)
        stderr = open("/dev/null","w")
    else:
        stderr = open("/dev/null","w")
    try:
        res = subprocess.Popen(cmd,shell=True,stderr = stderr,stdout=subprocess.PIPE)
        for l in res.stdout:
            yield l.decode().rstrip()
    except:
        errlog("Command Failed! Please Check!")
        raise Exception
    stderr.close()

def log(msg,ext=False):
    sys.stderr.write("\n"+str(msg)+"\n")
    if ext:
        exit(1)


def load_bed(filename,columns,key1,key2=None,intasint=False):
    results = defaultdict(lambda: defaultdict(tuple))
    for l in open(filename):
        row = l.rstrip().split("\t")
        if key2:
            if max(columns+[key1,key2])>len(row):
                errlog("Can't access a column in BED file. The largest column specified is too big",True)
            if key2==2 or key2==3:
                results[row[key1-1]][int(row[key2-1])] = tuple([row[int(x)-1] for x in columns])
            else:
                results[row[key1-1]][row[key2-1]] = tuple([row[int(x)-1] for x in columns])
        else:
            if max(columns+[key1])>len(row):
                errlog("Can't access a column in BED file. The largest column specified is too big",True)
            results[row[key1-1]]= tuple([row[int(x)-1] for x in columns])
    return results


def filecheck(filename):
    """
    Check if file is there and quit if it isn't
    """
    if filename=="/dev/null":
        return filename
    elif not os.path.isfile(filename):
        errlog("Can't find %s\n" % filename)
        exit(1)
    else:
        return filename


def nofile(filename):
    """
    Return True if file does not exist
    """
    if not os.path.isfile(filename):
        return True
    else:
        return False

def nofolder(filename):
    """
    Return True if file does not exist
    """
    if not os.path.isdir(filename):
        return True
    else:
        return False

def create_seq_dict(ref):
    if nofile("%s.dict" % (ref.replace(".fasta","").replace(".fa",""))):
        run_cmd("gatk CreateSequenceDictionary -R %s" % ref)

def bowtie_index(ref):
    if nofile("%s.1.bt2"%ref):
        cmd = "bowtie2-build %s %s" % (ref,ref)
        run_cmd(cmd)

def bwa2_index(ref):
    """
    Create BWA index for a reference
    """
    if nofile("%s.bwt.2bit.64"%ref):
        cmd = "bwa-mem2 index %s" % ref
        run_cmd(cmd)

def bwa_index(ref):
    """
    Create BWA index for a reference
    """
    if nofile("%s.bwt"%ref):
        cmd = "bwa index %s" % ref
        run_cmd(cmd)

def run_cmd(cmd,verbose=1,target=None,terminate_on_error=True):
    """
    Wrapper to run a command using subprocess with 3 levels of verbosity and automatic exiting if command failed
    """
    if target and filecheck(target): return True
    cmd = "set -u pipefail; " + cmd
    if verbose>0:
        sys.stderr.write("\nRunning command:\n%s\n" % cmd)

    p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = p.communicate()

    if terminate_on_error is True and p.returncode!=0:
        raise ValueError("Command Failed:\n%s\nstderr:\n%s" % (cmd,stderr.decode()))

    if verbose>1:
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)

    return (stdout.decode(),stderr.decode())

def index_bam(bamfile,threads=1,overwrite=False):
    """
    Indexing a bam file
    """
    cmd = "samtools index -@ %s %s" % (threads,bamfile)
    bam_or_cram = "cram" if bamfile[-4:]=="cram" else "bam"
    suffix = ".bai" if bam_or_cram=="bam" else ".crai"
    if filecheck(bamfile):
        if nofile(bamfile+suffix):
            run_cmd(cmd)
        elif os.path.getmtime(bamfile+suffix)<os.path.getmtime(bamfile) or overwrite:
            run_cmd(cmd)

def index_bcf(bcffile,threads=1,overwrite=False):
    """
    Indexing a bam file
    """
    cmd = "bcftools index --threads %s -f %s" % (threads,bcffile)
    if filecheck(bcffile):
        if nofile(bcffile+".csi"):
            run_cmd(cmd)
        elif os.path.getmtime(bcffile+".csi")<os.path.getmtime(bcffile) or overwrite:
            run_cmd(cmd)

def tabix(bcffile,threads=1,overwrite=False):
    """
    Indexing a bam file
    """
    cmd = "bcftools index --threads %s -ft %s" % (threads,bcffile)
    if filecheck(bcffile):
        if nofile(bcffile+".tbi"):
            run_cmd(cmd)
        elif os.path.getmtime(bcffile+".tbi")<os.path.getmtime(bcffile) or overwrite:
            run_cmd(cmd)

def rm_files(x,verbose=True):
    """
    Remove a files in a list format
    """
    for f in x:
        if os.path.isfile(f):
            if verbose: sys.stderr.write("Removing %s\n" % f)
            os.remove(f)


# def verify_fq(filename):
#     """
#     Return True if input is a valid fastQ file
#     """
#     FQ = open(filename) if filename[-3:]!=".gz" else gzip.open(filename)
#     l1 = FQ.readline()
#     if l1[0]!="@":
#         sys.stderr.write("First character is not \"@\"\nPlease make sure this is fastq format\nExiting...")
#         exit(1)
#     else:
#         return True



# def file_len(filename):
#     """
#     Return length of a file
#     """
#     filecheck(filename)
#     for l in cmd_out("wc -l %s" % filename):
#         res = l.rstrip().split()[0]
#     return int(res)


# def download_from_ena(acc):
#     if len(acc)==9:
#         dir1 = acc[:6]
#         cmd = "wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/%s/%s/%s*" % (dir1,acc,acc)
#     elif len(acc)==10:
#         dir1 = acc[:6]
#         dir2 = "00"+acc[-1]
#         cmd = "wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/%s/%s/%s/%s*" % (dir1,dir2,acc,acc)
#     else:
#         sys.stderr.write("Check Accession: %s" % acc)
#         exit(1)
#     run_cmd(cmd)

# def which(program):
#     import os
#     def is_exe(fpath):
#         return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

#     fpath = os.path.split(program)[0]
#     if fpath:
#         if is_exe(program):
#             return program
#     else:
#         for path in os.environ["PATH"].split(os.pathsep):
#             exe_file = os.path.join(path, program)
#             if is_exe(exe_file):
#                 return exe_file

#     return None

# def programs_check(programs):
#     for p in programs:
#         if which(p)==None:
#             log("Can't find %s in path... Exiting." % p)
#             quit(1)
