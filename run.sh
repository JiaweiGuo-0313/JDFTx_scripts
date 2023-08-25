#!/bin/bash
# Created on Wed Jul 26 2023
# author: Jiawei Guo

#SBATCH --exclude=agate-0,agate-1,agate-10,agate-16,agate-19,agate-26,agate-28,agate-29,agate-40,agate-43
#SBATCH --nodes=1 --partition=high
#SBATCH --mem-per-cpu=12000
#SBATCH --nodelist=agate-15
#SBATCH --ntasks-per-node=16
#SBATCH --ntasks-per-core=4
#SBATCH --threads-per-core=1
#SBATCH --error=job.err
#SBATCH --output=job.out
#SBATCH --time=38:00:00
#SBATCH --verbose

module load jdftx/1.7.0

export SLURM_CPU_BIND="cores"
export JDFTX_MEMPOOL_SIZE=8192


run () {
# charges are measured in electrons. eg. OH- will have charge +1,  H3O+ will have charge -1
# run geometry optimiation until convergence is reached

python setup_jdftx.py NEW $1 $2 $3 $4 $5
mpirun -n 1 -c 16 jdftx -i $1.in -o $1.out -d  # overwrite

for i in {1..20}
do
job_status=$(python setup_jdftx.py RERUN $1 $2 $3 $4 $5)

if [ "$job_status" != "converged" ]
then
echo $i
mpirun -n 1 -c 16 jdftx -i $1.in -o $1.out  # append
fi
done

}


run_GC () {

PZC=$(python setup_jdftx.py GC-mu $6)
python setup_jdftx.py NEW $1 $2 $3 $4 $5

for iMu in {-10..10}
do
export mu="$(echo $PZC $iMu | awk '{printf("%.4f", $1+0.1*$2/27.2114)}')"
mpirun -n 1 -c 16 jdftx -i $1.in -o $1$mu.out
# mv $1.nbound $1$mu.nbound
done

}


collect () {

for file in $1*.out
do
mu=$(python setup_jdftx.py GC-mu ${file::-4})
G=$(python setup_jdftx.py GC-E ${file::-4})
echo $mu $G
# awk '/FillingsUpdate/ {mu=$3; N=$5} END {print mu, N}' "$file"
done

}

###############################################################################################################
###############################################################################################################

# inputs (ordering matters): end_name start_name maxIter charge solvent

# python setup_jdftx.py from_xyz 	# generate input files from .xyz 
# run Vacuum start 3 0 	                # run geometry opt in vacuum
# run CANDLE Vacuum 10 0 CH3CN          # now including solvation
# run CANDLE start 10 0 CH3CN	        # OR: directly run geometry opt including solvation (comment out the previous two lines)

# fixed-potential calculations (GC-DFT)
# run Neutral CANDLE 20 GC-Neutral CH3CN 	      # run Neutral to get Potential of Zero Charge (PZC) 
# run_GC Charged CANDLE 20 GC-Charged CH3CN Neutral   # run potential scan w.r.t PZC
# collect Charged 






