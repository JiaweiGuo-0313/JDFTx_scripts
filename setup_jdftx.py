#!/usr/bin/env python
"""
Created on Wed Jul 26 2023
@author: Jiawei Guo
"""
import os, sys, time, glob, shutil, subprocess, copy
from ase.io import read
from textwrap import dedent
import re


def setup_geometry(atoms, pad, **kwargs):
    # generate geometry inputs from existing .xyz
    if atoms is not None:
        atoms.write('start.xyz', format='xyz')
        os.system(f"/home/gjw123/programs/jdftx/jdftx-git/jdftx/scripts/xyzToIonposOpt start.xyz {pad}")  # in bohr


def check_convergence(job_name, maxIter):
    lines = open(f"{job_name}.out", 'r').readlines()
    lines = reversed(lines)
    for line in lines:
        if "IonicMinimize: Converged" in line:
            return True
    return False


def get_final_mu(job_name):
    p = re.compile('[+-]?\d+.\d+')
    lines = open(f"{job_name}.out", 'r').readlines()
    lines = reversed(lines)
    for line in lines:
        if "FillingsUpdate:  mu:" in line:
            return float(p.findall(line)[0])


def write_inputs(atoms, status, job_name, start_name, pad=15, coords_type="cartesian", functional="PBE", 
        vdw='D3', maxIter=0, elec_ex_corr=None, more_outputs='', charge=0, solvent='', electrolyte_conc=0.1, *kwargs):
    # geometry & unit cell setup
    if status == 'NEW':
        setup_geometry(atoms, pad)  
        jdftx_in = dedent(f"include {start_name}.lattice\ninclude {start_name}.ionpos\n")
    elif status == 'RERUN':
        if check_convergence(job_name, maxIter):
            print("converged")
            return
        else:
            print("not converged")
            jdftx_in = dedent(f"include {job_name}.lattice\ninclude {job_name}.ionpos\n")
            jdftx_in += dedent(f"initial-state {job_name}.$VAR\n")
    else:
        return
    jdftx_in += dedent(f"coords-type {coords_type}\ncoulomb-interaction Isolated\ncoulomb-truncation-embed 0 0 0\n")
    
    # dispersion & functional setup
    functional_mapper = {'PBE': 'gga-PBE', 'PW': 'gga-PW91', 'B3LYP': 'hyb-gga-b3lyp', 'PBE0': 'hyb-PBE0', 
            'HSE06': 'hyb-HSE06', 'TPSS': 'mgga-TPSS', 'rTPSS': 'mgga-revTPSS', 'HF': 'Hartree-Fock'}
    if elec_ex_corr is None:
        func_tag = functional_mapper.get(functional)
    else:
        func_tag = elec_ex_corr
    jdftx_in += dedent(f"van-der-waals {vdw}\nelec-ex-corr {func_tag}\n")
    
    # pseudopotential setup
    if 'hyb-' in func_tag or 'Hartree-Fock' in func_tag: # NOT COMPLETE 
        jdftx_in += dedent(f"ion-species SG15/$ID_ONCV_PBE.upf\nelec-cutoff 30\n") # norm-conserving pseudopotentials
    else:
        jdftx_in += dedent(f"ion-species GBRV/$ID_pbe.uspp\nelec-cutoff 20 100\n") # ultrasoft pseudopotentials
    
    # output setup
    jdftx_in += dedent(f"dump-name {job_name}.$VAR\ndump End State Lattice {more_outputs}\n") # outputs
    
    # geometry optimization calc. setup
    jdftx_in += dedent(f"ionic-minimize nIterations {maxIter}\n") # maxIter=0: single point; >0: geometry opt
    
    # solvation params setup: stick to LinearPCM methods for now
    if solvent != '':  ### add other models 
        jdftx_in += dedent(f"fluid LinearPCM\npcm-variant CANDLE\nfluid-solvent {solvent}\n")
        jdftx_in += dedent(f"fluid-cation Na+ {electrolyte_conc}\nfluid-anion F- {electrolyte_conc}\n")
        # different ion choices behave differently only for ClassicalDFT (explicit solvation)
        # stick to Na+ and F- in the continuum electrolyte (NaF is a well-known non-adsorbing electrolyte)
        
        # CHE model vs. GC-DFT
        if type(charge) in [int, float] or charge.strip('-').isnumeric(): # explicitly define charge
            jdftx_in += dedent(f"elec-initial-charge {charge}\n")
        if 'GC' in charge: 
            jdftx_in += dedent(f"elec-smearing Fermi 0.01\n")
            if 'Charged' in charge:
                jdftx_in += dedent(f"initial-state {job_name}.$VAR\nelectronic-minimize nIterations 200\ntarget-mu ${{mu}}\n")


    with open(f"{job_name}.in", 'w') as f:
        f.write(jdftx_in)
    
    # TODO: INCLUDE VIB
   

###############################################################################################################
###############################################################################################################

status, job_name, start_name, maxIter, charge, solvent = sys.argv[1:] + ['' for i in range(7-len(sys.argv))]

if solvent == '':
    atoms = read('start.xyz', '0') 
else:
    atoms = None

if status == 'GC':
    print(get_final_mu(job_name))
else:
    write_inputs(atoms, status, job_name, start_name, maxIter=maxIter, charge=charge, solvent=solvent)






















