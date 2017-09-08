#! /usr/bin/env python

import pdb
import time
import sys
import os
import subprocess
import psutil
import shutil

from itertools import product

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def run_benchmark(command, unique_id):

    analysis_dirname = get_analysis_dir(command, unique_id)
    os.chdir(analysis_dirname)

    write_command_notes(command, unique_id)
    process = run_command(command)

    timeout = 50000
    time_taken, monitor_path = monitor_system(process, timeout)
    if time_taken > timeout:
        handle_timeout(process, monitor_path)

    os.chdir("../")

def write_command_notes(command, unique_id):
    with open("notes.txt", "w") as notes_file:
        notes_file.write(command + "\n")
        notes_file.write(str(unique_id) + "\n")

def get_analysis_dir(command, unique_id):
    command_list = command.split(" ")
    dirname = "%s_%d" % (command_list[0], unique_id,)
    os.mkdir(dirname)
    return dirname

def handle_timeout(process,monitor_path):
    try:
        process.terminate()
    except OSError:
        pass

    with open(monitor_path,"a") as monitor_file:
        monitor_file.write("TIMEOUT_FAIL\n")

def run_command(command):
    output_file = open("./output.txt", "w")

    proc = subprocess.Popen(command,
                            shell = True,
                            stdin=output_file, 
                            stdout=output_file, 
                            stderr=output_file)

    return proc

def monitor_system(process, timeout):
    monitor_path = "monitor.csv"
    start_time = time.time()
    sleep_time = 5
    write_multiplier = 6

    with open(monitor_path, "w") as monitor_file:
        monitor_file.write(\
            "CPU-PERCENT,CPU-PERCENT-FULL,FREE-MEM,AVAILABLE-MEM,DISK-USEAGE,TIME\n")
        i = 0
        while process.poll() is None and time_since(start_time) < timeout:
            
            if i % write_multiplier == 0:
                write_stats_to_file(monitor_file, start_time)
            
            if i % 36 == 0:
                monitor_file.flush()
            
            time.sleep(sleep_time)
            i += 1

        time.sleep(sleep_time*write_multiplier)
                                        # +sleep_time to record the final time 
                                        # including time slept to try and 
                                        # capture the system "at rest"
        write_stats_to_file(monitor_file, 
                            start_time+(sleep_time*write_multiplier))
        monitor_file.flush()

    return time_since(start_time), monitor_path

def time_since(since_time):
    return time.time() - since_time

def write_stats_to_file(monitor_file, start_time):
    cpu_percent = psutil.cpu_percent()
    cpu_percent_full = sum(psutil.cpu_percent(percpu=True))
    
    mem_stats = psutil.virtual_memory()
    free_mem = int(mem_stats.free)
    available_mem = int(mem_stats.available)

    dirsize = get_size()

    monitor_file.write("%d,%d,%d,%d,%d,%d\n" % (cpu_percent,
                                             cpu_percent_full,
                                             free_mem,
                                             available_mem,
                                             dirsize,
                                             time_since(start_time)))

def get_parent_dir():
    dirname = "benchmark-%d" % (time.time())
    os.mkdir(dirname)
    return dirname

def benchmark_commands(commands, repeat = 1):
    dirname = get_parent_dir()
    os.chdir(dirname)

    iterations = 0
    turns = 0

    while turns < repeat:
        line = commands[iterations % len(commands)]   

        print "\t%d:: %s" % (iterations, line[:50],)
        run_benchmark(line.strip(), iterations)

        iterations += 1

        if iterations % len(commands) == 0 and iterations > 0:
            turns += 1

    print "\n%s" % (dirname,)

def get_commands(in_file):
    commands = []
    for line in in_file:
        commands.append(line)
    return commands

if __name__ == "__main__":
    commands = []
    repeat = 1
    if len(sys.argv) == 1:
        commands = get_commands(sys.stdin)
    elif len(sys.argv) >= 2 and len(sys.argv) < 4:
        if len(sys.argv) == 3:
            repeat = int(sys.argv[2])
        with open(sys.argv[1], "r") as in_file:
            commands = get_commands(in_file)
    else:
        print "Useage:"
        print "\tcat /path/to/file/of_commands.txt > benchmarker.py"
        print "Or:"
        print "\tbenchmarker.py /path/to/file/of_commands.txt <num of repeats (int)>"

    if len(commands) > 0:
        benchmark_commands(commands, repeat)

