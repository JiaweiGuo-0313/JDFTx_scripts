#!/bin/bash
import os, sys, time, glob, shutil, subprocess, copy
from ase.io import read
from textwrap import dedent
os.system('module load jdftx/1.7.0')


def setup_geometry(atoms, pad, **kwargs):
    # generate geometry inputs from existing .xyz
    atoms.write('start.xyz', format='xyz')
    os.system(f"/home/gjw123/programs/jdftx/jdftx-git/jdftx/scripts/xyzToIonposOpt start.xyz {pad}")  # in bohr


def check_convergence(job_name, maxIter):
    lines = open(f"{job_name}.out", 'r').readlines()
    lines = reversed(lines)
    for line in lines:
        if "IonicMinimize: Converged" in line:
            return True
    return False
    

def write_inputs(atoms, status, job_name, pad=15, coords_type="cartesian", functional="PBE",
        vdw='D3', maxIter=0, elec_ex_corr=None, **kwargs):
    # geometry & unit cell setup
    if status == 'NEW':
        setup_geometry(atoms, pad)
        jdftx_in = dedent(f"include start.lattice\ninclude start.ionpos\n")
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
    jdftx_in += dedent(f"dump-name {job_name}.$VAR\ndump End State Lattice\n") # OUTPUT

    # calculation setup
    jdftx_in += dedent(f"ionic-minimize nIterations {maxIter}\n") # maxIter=0: single point; >0: geometry opt

    with open(f"{job_name}.in", 'w') as f:
        f.write(jdftx_in)
    # TODO: INCLUDE SOL, VIB


###############################################################################################################
###############################################################################################################

status, job_name, maxIter = sys.argv[1:]
atoms = read('start.xyz', '0')
write_inputs(atoms, status=status, job_name=job_name, maxIter=int(maxIter))








