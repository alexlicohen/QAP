#!/usr/bin/env python
import os
import subprocess
from subprocess import Popen, PIPE
from shutil import rmtree, copy
import argparse
from glob import glob
import datetime, time
import yaml
from bids_utils import extract_bids_data


def create_dir(dir_path, sub_dir):
    import os
    dir_path = os.path.abspath(dir_path)
    dir_path = os.path.join(dir_path, sub_dir)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path

def run(command, env={}):
    process = Popen(command, stdout=PIPE, stderr=subprocess.STDOUT,
        shell=True, env=env)
    while True:
        line = process.stdout.readline()
        line = str(line)[:-1]
        print(line)
        if line == '' and process.poll() != None:
            break

parser = argparse.ArgumentParser(description='PCP-QAP Pipeline Runner')

parser.add_argument('bids_dir', help='The directory with the input dataset '
    'formatted according to the BIDS standard.')

parser.add_argument('output_dir', help='The directory where the output CSV '
    'files should be stored.')

parser.add_argument('analysis_level', help='Level of the analysis that will '
    ' be performed. Multiple participant level analyses can be run '
    ' independently (in parallel) using the same output_dir.  Group level'
    ' analysis compiles multiple participant level quality metrics into'
    'group-level csv files.',
    choices=['participant', 'group'])

parser.add_argument('--participant_label', help='The label of the participant'
    ' that should be analyzed. The label '
    'corresponds to sub-<participant_label> from the BIDS spec '
    '(so it does not include "sub-"). If this parameter is not '
    'provided all subjects should be analyzed. Multiple '
    'participants can be specified with a space separated list.', nargs="+")

parser.add_argument('--pipeline_file', help='Name for the pipeline '
    ' configuration file to use, uses a default configuration if not'
    ' specified',
    default="/qap_resources/default_pipeline.yml")

parser.add_argument('--n_cpus', help='Number of execution '
    ' resources available for the pipeline, default=1', default="1")

parser.add_argument('--mem', help='Amount of RAM available '
    ' to the pipeline in GB, default = 6', default="6")

parser.add_argument('--save_working_dir', action='store_true',
    help='Save the contents of the working directory.', default=False)

parser.add_argument('--report', action='store_true', help='Generates pdf '
    'for graphically assessing data quality.', default=False)

# get the command line arguments
args = parser.parse_args()

# validate input dir
run("bids-validator %s"%args.bids_dir)

print(args)

# get and set configuration
c = yaml.load(open(os.path.realpath(args.pipeline_file), 'r'))

# set the parameters using the command line arguments
c['output_directory']  = os.path.abspath(c['output_directory'])
c['num_sessions_at_once'] = int(args.n_cpus)
if( args.save_working_dir == True ):
    c['write_all_outputs'] = True
    c['working_directory'] = create_dir(args.output_dir, "working")
else:
    c['write_all_outputs'] = False
    c['working_directory'] = create_dir('/tmp', "working")

c['write_report'] = args.report
c['num_processors'] = int(args.n_cpus)
c['available_memory'] = int(args.mem)


print ("#### Running QAP on %s"%(args.participant_label))
print ("Number of subjects to run in parallel: %d"%(c['num_sessions_at_once']))
print ("Output directory: %s"%(c['output_directory']))
print ("Working directory: %s"%(c['working_directory']))
print ("Save working directory: %s"%(c['write_all_outputs']))


if args.analysis_level.lower() == 'participant':
    
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')

    if args.participant_label:
        for pt in args.participant_label:
            include_participants+=glob("sub-%s"%(pt))
        include_file=os.path.join(args.output_dir,"bids_run_particList_%s.txt"%(st))
        subject_list_file=os.path.join(args.output_dir,"bids_run_sublist_%s.yml"%(st))
        os.system("qap_sublist_generator.py --include %s --BIDS %s %s"%(include_file,args.bids_dir,os.path.join(args.output_dir,subject_list_file)))
    else:
        include_participants=""
        subject_list_file=os.path.join(args.output_dir,"bids_run_sublist_%s.yml"%(st))
        os.system("qap_sublist_generator.py --BIDS %s %s"%(args.bids_dir,os.path.join(args.output_dir,subject_list_file)))

    #update config file
    config_file=os.path.join(args.output_dir,"bids_run_config_%s.yml"%(st))
    with open(config_file, 'w') as f:
        yaml.dump(c, f)

    #run pipeline
    os.system("qap_measures_pipeline.py %s %s"%(subject_list_file,config_file))

else:
    print "Running group level analysis to merge participant results"
    os.system("qap_jsons_to_csv.py %s"%(c['output_directory']))
    # csv_files=glob("*.csv")
    # for i in csv_files:
    #     copy(i, c['output_directory'])
