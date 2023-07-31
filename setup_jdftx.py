#!/usr/bin/env python
"""
Created on Wed Jul 26 2023
@author: Jiawei Guo
"""
import os, sys, time, glob, shutil, subprocess, copy
from ase.io import read
from textwrap import dedent
import re


class JDFTx_helper(object):
    

    def __init__(self, status, job_name, start_name, maxIter, charge, solvent):
        self.status = status
        self.job_name = job_name
        self.start_name =  start_name
        self.maxIter = maxIter
        self.charge = charge
        self.solvent = solvent
        self.jdftx_in = ''


    @staticmethod
    def setup_geometry(atoms, pad=15):
        # generate geometry inputs from existing .xyz
        if atoms is not None:
            atoms.write('start.xyz', format='xyz')
            os.system(f"/home/gjw123/programs/jdftx/jdftx-git/jdftx/scripts/xyzToIonposOpt start.xyz {pad}")  # in bohr


    def check_convergence(self):
        
        lines = open(f"{self.job_name}.out", 'r').readlines()
        lines = reversed(lines)
        for line in lines:
            if "IonicMinimize: Converged" in line:
                return True
        return False


    def get_final_mu(self):
        # get PZC (potential of zero charge)
        p = re.compile('[+-]?\d+.\d+')
        lines = open(f"{self.job_name}.out", 'r').readlines()
        lines = reversed(lines)
        for line in lines:
            if "FillingsUpdate:  mu:" in line:
                print(float(p.findall(line)[0]))
                return


    def setup_UC_and_geometries(self, coords_type):
        
        if self.status == 'NEW':
            self.jdftx_in = dedent(f"include {self.start_name}.lattice\ninclude {self.start_name}.ionpos\n")
        if self.status == 'RERUN':
            if self.check_convergence():
                print("converged")
                return
            else:
                print("not converged")
                self.jdftx_in = dedent(f"include {self.job_name}.lattice\ninclude {self.job_name}.ionpos\n")

        self.jdftx_in += dedent(f"initial-state {self.job_name}.$VAR\n") 
        self.jdftx_in += dedent(f"coords-type {coords_type}\n")
        self.jdftx_in += dedent(f"coulomb-interaction Isolated\ncoulomb-truncation-embed 0 0 0\n")


    def setup_basics(self, functional, vdw, elec_ex_corr, more_outputs):
    
        # setup dispersions and functionals
        functional_mapper = {'PBE': 'gga-PBE', 'PW': 'gga-PW91', 'B3LYP': 'hyb-gga-b3lyp', 'PBE0': 'hyb-PBE0',
                             'HSE06': 'hyb-HSE06', 'TPSS': 'mgga-TPSS', 'rTPSS': 'mgga-revTPSS', 'HF': 'Hartree-Fock'}
        if elec_ex_corr is None:
            func_tag = functional_mapper.get(functional)
        else:
            func_tag = elec_ex_corr
        self.jdftx_in += dedent(f"van-der-waals {vdw}\nelec-ex-corr {func_tag}\n")
        
        # pseudopotentials setup
        if 'hyb-' in func_tag or 'Hartree-Fock' in func_tag: # NOT COMPLETE
            self.jdftx_in += dedent(f"ion-species SG15/$ID_ONCV_PBE.upf\nelec-cutoff 30\n") # norm-conserving pseudopotentials
        else:
            self.jdftx_in += dedent(f"ion-species GBRV/$ID_pbe.uspp\nelec-cutoff 20 100\n") # ultrasoft pseudopotentials

        # output setup
        self.jdftx_in += dedent(f"dump-name {self.job_name}.$VAR\ndump End State Lattice {more_outputs}\n") # outputs

        # geometry optimization calc. setup
        self.jdftx_in += dedent(f"ionic-minimize nIterations {self.maxIter}\n") # maxIter=0: single point; >0: geometry opt


    def setup_solvations(self, electrolyte_conc):
        # stick to LinearPCM methods for now
        self.jdftx_in += dedent(f"fluid LinearPCM\npcm-variant CANDLE\nfluid-solvent {self.solvent}\n")
        self.jdftx_in += dedent(f"fluid-cation Na+ {electrolyte_conc}\nfluid-anion F- {electrolyte_conc}\n")
        # different ion choices behave differently only for ClassicalDFT (explicit solvation)
        # stick to Na+ and F- in the continuum electrolyte (NaF is a well-known non-adsorbing electrolyte)

        # CHE model vs. GC-DFT
        if type(self.charge) in [int, float] or self.charge.strip('-').isnumeric(): # explicitly define charge
            self.jdftx_in += dedent(f"elec-initial-charge {self.charge}\n")
        if 'GC' in self.charge:
            self.jdftx_in += dedent(f"elec-smearing Fermi 0.01\n")
            if 'Charged' in self.charge:
                self.jdftx_in += dedent(f"electronic-minimize nIterations 200\ntarget-mu ${{mu}}\n")


    def write_inputs(self, coords_type="cartesian", functional="PBE", vdw='D3', elec_ex_corr=None, more_outputs='', electrolyte_conc=0.1, *kwargs):
        
        self.setup_UC_and_geometries(coords_type)
        self.setup_basics(functional, vdw, elec_ex_corr, more_outputs)
        if solvent != '':  ### add other models
            self.setup_solvations(electrolyte_conc)
    
        with open(f"{self.job_name}.in", 'w') as f:
            f.write(self.jdftx_in)
    
        # TODO: INCLUDE VIB
   

###############################################################################################################
###############################################################################################################


status, job_name, start_name, maxIter, charge, solvent = sys.argv[1:] + ['' for i in range(7-len(sys.argv))]
helper_class = JDFTx_helper(status, job_name, start_name, maxIter, charge, solvent)

if status == 'from_xyz':
    atoms = read('start.xyz', '0') # edit this line with appropriate names
    helper_class.setup_geometry(atoms)
elif status == 'GC': 
    helper_class.get_final_mu(job_name)
else:
    helper_class.write_inputs()





















