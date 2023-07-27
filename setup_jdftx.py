#!/bin/bash
import os, sys, time, glob, shutil, subprocess, copy
from ase.io import read
from textwrap import dedent
os.system('module load jdftx/1.7.0')


def setup_geometry(atoms, pad, **kwargs):
    atoms.write('start.xyz', format='xyz')
    os.system(f"xyzToIonposOpt start.xyz {pad}")  # in bohr
    time.sleep(20) 


def write_inputs(atoms, job_name, pad=15, coords_type="cartesian", functional="PBE", 
        vdw='D3', maxIter=0, elec_ex_corr=None, **kwargs):
    setup_geometry(atoms, pad)   

    functional_mapper = {'PBE': 'gga-PBE', 'PW': 'gga-PW91', 'B3LYP': 'hyb-gga-b3lyp',
                         'PBE0': 'hyb-PBE0', 'HSE06': 'hyb-HSE06', 
                         'TPSS': 'mgga-TPSS', 'rTPSS': 'mgga-revTPSS',
                         'HF': 'Hartree-Fock'}
    if elec_ex_corr is None:
        func_tag = functional_mapper.get(functional)
    else:
        func_tag = elec_ex_corr
    
    jdftx_in = dedent(f"include start.lattice\ninclude start.ionpos\ncoords-type {coords_type}\n")
    jdftx_in += dedent(f"coulomb-interaction Isolated\ncoulomb-truncation-embed 0 0 0\n")
    jdftx_in += dedent(f"van-der-waals {vdw}\n")
    jdftx_in += dedent(f"elec-ex-corr {func_tag}\n") 
    
    if 'hyb-' in func_tag or 'Hartree-Fock' in func_tag: # NOT COMPLETE
        jdftx_in += dedent(f"ion-species SG15/$ID_ONCV_PBE.upf\nelec-cutoff 30\n") # norm-conserving pseudopotentials
    else:
        jdftx_in += dedent(f"ion-species GBRV/$ID_pbe.uspp\nelec-cutoff 20 100\n") # ultrasoft pseudopotentials
    
    jdftx_in += dedent(f"dump-name Vacuum.$VAR\n")
    jdftx_in += dedent(f"dump End State\n")    
    jdftx_in += dedent(f"ionic-minimize nIterations {maxIter}\n") # maxIter=0: SINGLE POINT
    
    with open(f"{job_name}.in", 'w') as f:
        f.write(jdftx_in)
    # TODO: INCLUDE SOL, VIB
    return
   

def check_convergence(job_name, maxIter):
    lines = open(f"{job_name}.out", 'r').readlines()
    lines = reversed(lines)
    for line in lines:
        if "IonicMinimize: Converged" in line:
            print("converged")
            return

    print("not converged")
    in_lines = open(f"{job_name}.in", 'r').readlines()
    write_line = True
    for line in in_lines:
        if 'initial-state' in line:
            write_line = False
            break
    if write_line is True:
        with open(f"{job_name}.in", 'a') as f:
            f.write(dedent(f"initial-state {job_name}.$VAR\n"))
        # only write initial-state one time for all reruns


###################################################################################################
###################################################################################################

status, job_name, maxIter = sys.argv[1:]
if status == 'NEW':
    atoms = read('start.xyz', '0')
    write_inputs(atoms, job_name=job_name, maxIter=int(maxIter))
if status == 'RERUN':
    check_convergence(job_name, int(maxIter))








